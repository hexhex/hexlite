#!/usr/bin/python2
# needs clingo to be built with correct python version, this software supports python2 and python3

# HEXLite Python-based solver for a fragment of HEX
# Copyright (C) 2017  Peter Schueller <schueller.p@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys, logging
# initially log everything
logging.basicConfig(level=logging.NOTSET, format="%(filename)10s:%(lineno)4d:%(message)s", stream=sys.stderr)

# load rest after configuring logging
import os, argparse, traceback, pprint, collections
import shallowhexparser as shp
import dlvhex

# clingo python API
import clingo

AUXPREFIX = 'aux_'
AUX_MAXINT = AUXPREFIX+'maxint'

class Plugin:
  def __init__(self, mname, pmodule):
    self.mname = mname
    self.pmodule = pmodule

def flatten(listoflists):
  return [x for y in listoflists for x in y]

def loadPlugin(mname):
  # returns plugin info
  logging.info('loading plugin '+repr(mname))
  pmodule = __import__(mname, globals(), locals(), [], 0)
  logging.info('configuring dlvhex module for registering module '+repr(mname))
  # tell dlvhex module which other module is registering its atoms
  dlvhex.startRegistration(pmodule)
  logging.info('calling register() for '+repr(mname))
  pmodule.register()
  logging.info('list of known atoms is now {}'.format(', '.join(dlvhex.eatoms.keys())))
  return Plugin(mname, pmodule)

def loadProgram(hexfiles):
  ret = []
  for f in hexfiles:
    with open(f, 'r') as inf:
      prog = shp.parse(inf.read())
      logging.debug('from file '+repr(f)+' parsed program\n'+pprint.pformat(prog, indent=2, width=250))
      ret += prog
  return ret

def rewriteProgram(program, plugins):
  '''
  go over all rules of program
  for each rule find external atoms and handle them with EAtomHandler
  (this can change the rule and create new rules)
  '''
  pr = ProgramRewriter(program, plugins)
  return pr.rewrite()

class ProgramRewriter:
  def __init__(self, shallowprogram, plugins):
    self.shallowprog = shallowprogram
    self.plugins = plugins
    self.srprog, self.facts = self.__annotateWithStatementRewriters()
    self.rewritten = []

  def rewrite(self):
    '''
    returns rewritten_program, facts
    '''
    # rewriters append to self.rewritten
    for stm in self.srprog:
      stm.rewrite()
    return self.rewritten, self.facts

  def addRewrittenRule(self, stm):
    'called by child statement rewriters to register rules'
    # XXX handle duplicate rules here
    logging.info("adding rewritten rule "+shp.shallowprint(stm))
    self.rewritten.append(stm)

  def __annotateWithStatementRewriters(self):
    '''
    collect statements from shallowprog
    * mostly one item is one statement
    * exceptions might apply
    * facts are returned separately
    '''
    ret = []
    facts = []
    for stm in self.shallowprog:
      if __debug__:
        dbgstm = pprint.pformat(stm, width=1000)
      #logging.debug('ASR '+dbgstm)
      if isinstance(stm, shp.alist):
        sig = (stm.left, stm.sep, stm.right)
        #logging.debug('ASR alist {}'.format(repr(sig)))
        if sig == (None, None, '.'):
          if len(stm) == 1 and isinstance(stm[0], list) and isinstance(stm[0][0], str) and stm[0][0].startswith('#'):
            # hash-instruction
            logging.debug('ASR hash %s', dbgstm)
            ret.append(StatementRewriterHash(self, stm))
            continue
          else:
            # fact (maybe disjunctive)
            logging.debug('ASR fact/passthrough %s', dbgstm)
            ret.append(StatementRewriterHead(self, stm))
            facts.append(stm)
            continue
        elif sig == (None, ':-', '.'):
          # rule/constraint
          logging.debug('ASR rule/rulecstr %s', dbgstm)
          ret.append(StatementRewriterRuleCstr(self, stm))
          continue
      elif isinstance(stm, list) and len(stm) == 2:
        # weak constraint
        assert(isinstance(stm[0], shp.alist) and stm[0].sep == ':~')
        ret.append(StatementRewriterWeakCstr(self, stm))
        continue
      # unclassified
      logging.warning('ASR unclassified/passthrough '+dbgstm)
      ret.append(StatementRewriterPassthrough(self, stm))
    return ret, facts

class StatementRewriterBase:
  def __init__(self, pr, statement):
    '''
    pr is the program rewriter
    statement is the shallow parse of the statement
    '''
    self.pr = pr
    self.statement = statement

  def rewrite(self):
    '''
    appends to self.pr.rewritten
    '''
    raise Exception('should be implemented in child class')

  def rewriteInt(self):
    '''
    rewrite #int directives wherever they are in the tree (uses aux_maxint)
    '''
    def rewriteIfApplicable(elem):
      if isinstance(elem, list) and len(elem) > 0 and elem[0] == '#int':
        if len(elem) != 2 or not isinstance(elem[1], shp.alist):
          logging.warning("do not know how to rewrite integer in {}".format(pprint.pformat(elem)))
        else:
          # rewrite
          # #int(Term) becomes Term = 0..aux_maxint
          if __debug__:
            orig = list(elem)
          term = elem[1][0]
          elem[:] = [term, '=', '0', '..', AUXPREFIX+'maxint']
          if __debug__:
            logging.debug("rewrote {} to {}".format(pprint.pformat(orig), pprint.pformat(elem)))
    dfVisit(self.statement, rewriteIfApplicable)

class StatementRewriterPassthrough(StatementRewriterBase):
  '''
  just outputs the statement as it comes in
  (used for things we do not know how to handle otherwise)
  '''
  def __init__(self, pr, statement):
    StatementRewriterBase.__init__(self, pr, statement)

  def rewrite(self):
    #self.rewriteInt()
    self.pr.addRewrittenRule(self.statement)

class StatementRewriterHash(StatementRewriterBase):
  '''
  for everything starting with # and ending with .
  '''
  def __init__(self, pr, statement):
    StatementRewriterBase.__init__(self, pr, statement)

  def rewrite(self):
    #self.rewriteInt()
    base = self.statement[0]
    logging.debug('SRH base '+pprint.pformat(base))
    if base[0] == '#maxint':
      # replace the first part with a const declaration (this way there can be a formula to the right of '=')
      self.statement[0][0:1] = ['#const', AUX_MAXINT]
      self.pr.addRewrittenRule(self.statement)
    else:
      logging.warning('SRH skipping rewriting of '+pprint.pformat(base))

class StatementRewriterHead(StatementRewriterBase):
  '''
  rewriting heads (of rules or facts)
  (used for facts, derived for rules)
  '''
  def __init__(self, pr, statement):
    StatementRewriterBase.__init__(self, pr, statement)
  def rewrite(self):
    logging.debug('SRH stm='+pprint.pformat(self.statement))
    #self.rewriteInt()
    assert(isinstance(self.statement, shp.alist))
    assert(len(self.statement) == 1) # we have no body (otherwise use StatementRewriterRuleCstr)
    self.statement[0] = self.rewriteDisjunctiveHead(self.statement[0])
    self.pr.addRewrittenRule(self.statement)
  def rewriteDisjunctiveHead(self, head):
    logging.debug('SRH head='+pprint.pformat(head))
    # if head is a normal list that contains more than 2 elements and some 'v' items on top level,
    # transform it into an alist with separator '|' instead of 'v'
    ret = head
    if isinstance(head, list) and not isinstance(head, shp.alist) and len(head) > 2:
      # collect parts between top-level 'v'
      parts = []
      current = []
      for elem in head:
        if elem == 'v':
          if len(current) != 0:
            parts.append(current)
            current = []
          else:
            current.append(elem)
        else:
          current.append(elem)
      parts.append(current)
      if len(parts) > 1:
        ret = shp.alist(parts, sep='|')
    logging.debug('SRH ret='+pprint.pformat(ret))
    return ret

class StatementRewriterRuleCstr(StatementRewriterHead):
  '''
  rewriting rules with nonempty body and constraints
  '''
  def __init__(self, pr, statement):
    StatementRewriterHead.__init__(self, pr, statement)

  def rewrite(self):
    if __debug__:
      logging.debug('SRRC stm='+pprint.pformat(self.statement, width=1000))
    self.rewriteInt()
    self.statement[0] = self.rewriteDisjunctiveHead(self.statement[0])
    body = self.statement[1]
    safeVars = self.findBasicSafeVariables(body)
    pendingEatoms = self.extractExternalAtoms(body)
    if len(pendingEatoms) == 0:
      self.pr.addRewrittenRule(self.statement)
    else:
      while len(pendingEatoms) > 0:
        #logging.debug('SRRC pendingEatoms='+pprint.pformat(pendingEatoms))
        logging.debug('SRRC safeVars='+pprint.pformat(safeVars))
        safeEatm, makesSafe = self.pickSafeExternalAtom(pendingEatoms, safeVars)
        logging.debug('SRRC safeEatm='+pprint.pformat(safeEatm))
        pendingEatoms.remove(safeEatm)
        handler = self.getExecutionHandler(safeEatm)
        safeConditions = self.findSafeConditions(self.statement[1], safeVars)
        resultRules = handler.transformEAtomInStatement(safeEatm, self.statement, safeVars, safeConditions)
        for r in resultRules:
          self.pr.addRewrittenRule(r)
        safeVars |= makesSafe

  def getExecutionHandler(self, eatom):
    eatomname = eatom['name']
    if eatomname not in dlvhex.eatoms:
      raise Exception('could not find handler for external atom {}'.format(shp.shallowprint(eatom['shallow'])))
    return dlvhex.eatoms[eatomname].executionHandler

  def pickSafeExternalAtom(self, pendingEatoms, safeVars):
    '''
    find some external atom A that is safe given safe variables in safeVars
     * return A, variables made safe by A
    '''
    for eatom in pendingEatoms:
      if eatom['inputvars'].issubset(safeVars):
        return eatom, eatom['outputvars']
    raise Exception("could not find safe external atom:\n"+
      "remaining atoms to resolve: "+shp.shallowprint(pendingEatoms)+"\n"+
      "safe variables in rule: "+repr(safeVars)+"\n"+
      "rule: "+shp.shallowprint(self.statement))

  def findBasicSafeVariables(self, body):
    '''
    find all variables safe due to non-hex body literals

    currently:
    * finds all variables in arguments of positive body literals
    * XXX there are some other cases that make variables safe (e.g., assignments)
    '''
    logging.debug('SRRC findBasicSafeVariables for body '+pprint.pformat(body))
    safetyGivingAtoms = deepCollectAtDepth(body, lambda d: d == 1,
      lambda x:
        (x[0] != 'not') and # NAF
        not (isinstance(x[0],str) and x[0][0] == '&') # external atoms
      )
    logging.debug('SRRC safetyGivingAtoms='+pprint.pformat(safetyGivingAtoms))
    safeVars = findVariables(safetyGivingAtoms)
    return set(safeVars)

  def findSafeConditions(self, body, safeVars):
    '''
    find all body elements that are safe assuming safeVars are safe

    currently:
    * finds all positive body literals
    * finds all negated body literals that contain only variables from safeVars
    * XXX implicitly finds rewritten external atoms(?)
    * XXX see findBasicSafeVariables for potentially problematic cases
    '''
    #logging.debug('SRRC findSafeConditions for safeVars {} and body {}'.format(repr(safeVars), pprint.pformat(body)))
    def isSafe(elem):
      #logging.debug('SRRC isSafe='+pprint.pformat(elem))
      isEatom = isinstance(elem[0],str) and elem[0][0] == '&'
      if isEatom:
        # for sure do not return untransformed external atoms
        return False
      if elem[0] != 'not':
        # positive literal
        return True
      else:
        # negative literal
        usedVariables = set(findVariables(elem))
        if usedVariables.issubset(safeVars):
          return True
      return False
    safeRewrittenLiterals = deepCollectAtDepth(body, lambda d: d == 1, isSafe)
    #logging.debug('SRRC safeRewrittenLiterals='+pprint.pformat(safeRewrittenLiterals))
    return safeRewrittenLiterals

  def extractExternalAtoms(self, body):
    '''
    return a list of dicts containing external atoms plus supporting information:
    * key shallow: shallow parse of the original eatom
    * key prefix: things before the eatom (NAF)
    * key eatom: the eatom on its own
    * key inputs: shallow parse of input list of the eatom
    * key inputvars: variables in the input of the eatom
    * key outputs: shallow parse of output list of the eatom
    * key outputvars: variables in the output of the eatom
    '''
    #logging.debug('body='+pprint.pformat(body))
    def splitPrefixEatom(x):
      assert(isinstance(x,list) and not isinstance(x,shp.alist))
      checkIdx = 0
      # skip over not's
      while len(x) > checkIdx and x[checkIdx] == 'not':
        checkIdx += 1
      if len(x) > checkIdx and isinstance(x[checkIdx], str) and x[checkIdx][0].startswith('&'):
        return x[:checkIdx], x[checkIdx:]
      else:
        return None
    eatoms = [ splitPrefixEatom(x) for x in body ]
    #logging.debug('eatoms1='+pprint.pformat(eatoms))
    eatoms = [ {'shallow': p_e[0] + p_e[1], 'prefix': p_e[0], 'eatom': p_e[1], 'name': p_e[1][0][1:] }
               for p_e in eatoms if p_e is not None ]
    #logging.debug('eatoms2='+pprint.pformat(eatoms))
    def enrich(eatom):
      #assert(logging.debug('enrich eatom='+pprint.pformat(eatom)) or True)
      inplist = [ x for x in eatom['eatom'] if isinstance(x,shp.alist) and x.left == '[' ]
      assert(len(inplist) <= 1)
      #assert(logging.debug('enrich inplist ='+pprint.pformat(inplist)) or True)
      outplist = [ x for x in eatom['eatom'] if isinstance(x,shp.alist) and x.left == '(' ]
      assert(len(outplist) <= 1)
      #assert(logging.debug('enrich outplist='+pprint.pformat(outplist)) or True)
      if len(inplist) == 0:
        eatom['inputs'] = []
      else:
        eatom['inputs'] = list(inplist[0])
      eatom['inputvars'] = set(findVariables(inplist))
      if len(outplist) == 0:
        eatom['outputs'] = []
      else:
        eatom['outputs'] = list(outplist[0])
      eatom['outputvars'] = set(findVariables(outplist))
      return eatom
    return [ enrich(x) for x in eatoms ]

class StatementRewriterWeakCstr(StatementRewriterRuleCstr):
  '''
  rewriting weak constraints
  '''
  def __init__(self, pr, statement):
    assert(isinstance(statement, list) and len(statement) == 2)
    StatementRewriterRuleCstr.__init__(self, pr, statement[0])
    self.weak = statement[1]

  def rewrite(self):
    logging.debug('SRWC stm='+pprint.pformat(self.statement))
    logging.debug('SRWC weak='+pprint.pformat(self.weak))
    assert(self.statement[0] == None)
    body = self.statement[1]
    safeVars = self.findBasicSafeVariables(body)
    pendingEatoms = self.extractExternalAtoms(body)
    if len(pendingEatoms) == 0:
      self.pr.addRewrittenRule(self.decorateWeak(self.statement, safeVars))
    else:
      while len(pendingEatoms) > 0:
        #logging.debug('SRRC pendingEatoms='+pprint.pformat(pendingEatoms))
        #logging.debug('SRRC safeVars='+pprint.pformat(safeVars))
        safeEatm, makesSafe = self.pickSafeExternalAtom(pendingEatoms, safeVars)
        pendingEatoms.remove(safeEatm)
        #logging.debug('SRRC safeEatm='+pprint.pformat(safeEatm))
        eatomname = safeEatm['eatom'][0][1:]
        if eatomname not in dlvhex.eatoms:
          raise Exception('could not find handler for external atom {}'.format(
            shp.shallowprint(safeEatm['shallow'])))
        handler = dlvhex.eatoms[eatomname].executionHandler
        resultRules = handler.transformEAtomInStatement(safeEatm, self.statement, safeVars)
        for r in resultRules:
          self.pr.addRewrittenRule(self.decorateWeak(r, safeVars))
        safeVars |= makesSafe

  def decorateWeak(self, stmt, safeVars):
    logging.debug('SRWC decorateWeak='+pprint.pformat(self.weak))
    assert(isinstance(self.weak, shp.alist))
    assert(self.weak.left == '[' and self.weak.right == ']')
    if self.weak.sep == ':':
      # old weak constraint syntax
      cost = self.weak[0]
      level = self.weak[1]
      leveltuple = shp.alist([level]+list(safeVars), sep=',')
      weakpart = shp.alist([cost, leveltuple], left='[', right=']', sep='@')
    else:
      # new syntax, just pass it directly
      weakpart = self.weak
    return [stmt, weakpart]

def findVariables(structure):
  # XXX maybe we want a "findFreeVariables" and not search for variables within aggregate bodies ...
  return deepCollect(structure,
    lambda x: isinstance(x, str) and x[0].isupper())

def dfVisit(structure, visitor):
  'depth-first traversal of structure, calls visitor on everything'
  if isinstance(structure, list):
    for elem in structure:
      dfVisit(elem, visitor)
  visitor(structure)

def deepCollect(liststructure, condition):
  'recursively traverses liststructure and retrieves items where condition is true'
  out = []
  def recursiveCollect(structure):
    if condition(structure):
      out.append(structure)
    if isinstance(structure, list):
      for elem in structure:
        recursiveCollect(elem)
  recursiveCollect(liststructure)
  return out

def deepCollectAtDepth(liststructure, depthfilter, condition):
  'recursively traverses liststructure and retrieves items where condition is true at depth in depthfilter'
  out = []
  def recursiveCollectAtDepth(structure, depth):
    if depthfilter(depth) and condition(structure):
      out.append(structure)
    if isinstance(structure, list):
      for elem in structure:
        recursiveCollectAtDepth(elem, depth+1)
  recursiveCollectAtDepth(liststructure, 0)
  return out

def convertClingoToHex(term):
  assert(isinstance(term, clingo.Symbol))
  if term.type is clingo.SymbolType.Number:
    ret = term.number
  elif term.type in [clingo.SymbolType.String, clingo.SymbolType.Function]:
    ret = str(term)
  else:
    raise Exception("cannot convert clingo term {} of type {} to external atom term!".format(
      repr(term), str(term.type)))
  return ret

def convertHexToClingo(term):
  if isinstance(term, str):
    if term[0] == '"':
      ret = clingo.String(term[1:-1])
    else:
      ret = clingo.parse_term(term)
  elif isinstance(term, int):
    ret = clingo.Number(term)
  else:
    raise Exception("cannot convert external atom term {} to clingo term!".format(repr(term)))
  return ret

def externalAtomCallHelper(holder, inputtuple, predicateinputatoms):
  '''
  * converts input tuple for execution
  * prepares dlvhex.py for execution
  * executes
  * converts output tuples
  * cleans up
  * return result
  '''
  out = None
  dlvhex.startExternalAtomCall(predicateinputatoms)
  try:
    # prepare input tuple
    plugin_arguments = []
    for spec_idx, inp in enumerate(holder.inspec):
      if inp in [dlvhex.PREDICATE, dlvhex.CONSTANT]:
        arg = convertClingoToHex(inputtuple[spec_idx])
        plugin_arguments.append(arg)
      elif inp == dlvhex.TUPLE:
        if (spec_idx + 1) != len(holder.inspec):
          raise Exception("got TUPLE type which is not in final argument position")
        # give all remaining arguments as one tuple
        args = [ convertClingoToHex(x) for x in inputtuple[spec_idx:] ]
        plugin_arguments.append(tuple(args))
      else:
        raise Exception("unknown input type "+repr(inp))

    # call external atom in plugin
    logging.debug('calling plugin eatom with arguments '+repr(plugin_arguments))
    holder.func(*plugin_arguments)
    
    # interpret output
    # list of tuple of terms (maybe empty tuple)
    out = [ tuple([ convertHexToClingo(val) for val in _tuple ]) for _tuple in dlvhex.currentOutput ]
  finally:
    dlvhex.cleanupExternalAtomCall()
  return out

class GringoContext:
  class ExternalAtomCall:
    def __init__(self, holder):
      self.holder = holder
    def __call__(self, *arguments):
      logging.debug('GC.EAC(%s) called with %s',self.holder.name, repr(arguments))
      out = externalAtomCallHelper(self.holder, arguments, None)
      outarity = self.holder.outnum
      # interpret special cases for gringo @eatom rewritings:
      if outarity == 0:
        # no output arguments: 1 or 0
        if len(out) == 0:
          out = 0
        else:
          out = 1
      elif outarity == 1:
        # list of terms, not list of tuples (I could not convince Gringo to process single-element-tuples)
        out = [ x[0] for x in out ]
      # in other cases we can directly use what externalAtomCallHelper returned
      logging.debug('GC.EAC(%s) call returned output %s', self.holder.name, repr(out))
      return out
  def __init__(self):
    pass
  def __getattr__(self, attr):
    #logging.debug('GC.%s called',attr)
    return self.ExternalAtomCall(dlvhex.eatoms[attr])

class Generic:
  def __init__(self, name):
    self.name = name
  def __call__(self, *arguments):
    logging.debug("GPGeneric {} {}".format(self.name, repr(arguments)))

class GroundProgramObserver:
  def rule(self, choice, head, body):
    logging.debug("GPRule ch={} hd={} b={}".format(repr(choice), repr(head), repr(body)))
  def output_atom(self, symbol, atom):
    logging.debug("GPAtom symb={} atm={}".format(repr(symbol), repr(atom)))
  def output_term(self, symbol, condition):
    logging.debug("GPAtom symb={} cond={}".format(repr(symbol), repr(condition)))
  def __getattr__(self, name):
    #logging.debug("GP getattr {}".format(name))
    return Generic(name)

class SymLit:
  def __init__(self, sym, lit):
    self.sym = sym
    self.lit = lit

class ClingoID:
  # the ID class as passed to plugins, from view of Clingo backend
  def __init__(self, symlit):
    self.symlit = symlit
    self.value = str(symlit.sym)

  def value(self):
    return self.value

  def intValue(self):
    if self.symlit.sym.type == clingo.SymbolType.Number:
      return self.symlit.sym.number
    else:
      raise Exception('intValue called on ID {} which is not a number!'.format(self.value))

  def isTrue(self):
    global clingoPropControl
    return clingoPropControl.assignment.is_true(self.symlit.lit)

  def isFalse(self):
    global clingoPropControl
    return clingoPropControl.assignment.is_false(self.symlit.lit)

  def isAssigned(self):
    global clingoPropControl
    return clingoPropControl.assignment.value(self.symlit.lit) != None

  def __getattr__(self, name):
    raise Exception("not (yet) implemented: ClingoID.{}".format(name))


class EAtomVerification:
  def __init__(self, relevance, replacement):
    # symlit for ground eatom relevance
    self.relevance = relevance
    # symlit for ground eatom replacement
    self.replacement = replacement
    # key = argument position, value = list of ClingoID
    self.predinputs = collections.defaultdict(list)
    # list of all elements in self.predinputs (cache)
    self.allinputs = None

clingoPropControl = None

class Nogood:
  def __init__(self):
    self.literals = set()
  def add(self, lit):
    if -lit in self.literals:
      return False
    self.literals.add(lit)
    return True

class ClingoPropagator:
  class StopPropagation:
    pass
  def __init__(self):
    # key = eatom
    # value = list of EAtomVerification
    self.eatomVerifications = collections.defaultdict(list)
    # mapping from solver literals to lists of strings
    self.debugMapping = collections.defaultdict(list)
  def init(self, init):
    # register mapping for solver/grounder atoms!
    # no need for watches as long as we use only check()
    for eatomname, signatures in rewritingState.eatoms.items():
      logging.info('CPinit processing eatom '+eatomname)
      for siginfo in signatures:
        logging.debug('CPinit processing eatom {} relpred {} reppred arity {}'.format(
          eatomname, siginfo.relevancePred, siginfo.replacementPred, siginfo.arity))
        for xrep in init.symbolic_atoms.by_signature(siginfo.replacementPred, siginfo.arity):
          logging.debug('CPinit   replacement atom {}'.format(str(xrep.symbol)))
          replacement = SymLit(xrep.symbol, init.solver_literal(xrep.literal))
          xrel = init.symbolic_atoms[clingo.Function(name=siginfo.relevancePred, arguments = xrep.symbol.arguments)]
          logging.debug('CPinit   relevance atom {}'.format(str(xrel.symbol)))
          relevance = SymLit(xrel.symbol, init.solver_literal(xrel.literal))

          verification = EAtomVerification(relevance, replacement)

          # get symbols given to predicate inputs and register their literals
          for argpos, argtype in enumerate(dlvhex.eatoms[eatomname].inspec):
            if argtype == dlvhex.PREDICATE:
              argval = str(xrep.symbol.arguments[argpos])
              logging.debug('CPinit     argument {} is {}'.format(argpos, str(argval)))
              relevantSig = [ (aarity, apol) for (aname, aarity, apol) in init.symbolic_atoms.signatures if aname == argval ]
              logging.debug('CPinit       relevantSig {}'.format(repr(relevantSig)))
              for aarity, apol in relevantSig:
                for ax in init.symbolic_atoms.by_signature(argval, aarity):
                  logging.debug('CPinit         atom {}'.format(str(ax.symbol)))
                  predinputid = ClingoID(SymLit(ax.symbol, init.solver_literal(ax.literal)))
                  verification.predinputs[argpos].append(predinputid)

          verification.allinputs = flatten([idlist for idlist in verification.predinputs.values()])
          self.eatomVerifications[eatomname].append(verification)

    # for debugging: get full symbol table
    for aname, aarity, apol in init.symbolic_atoms.signatures:
      for x in init.symbolic_atoms.by_signature(aname, aarity):
        slit = init.solver_literal(x.literal)
        if apol == True:
          self.debugMapping[slit].append(str(x.symbol))
        else:
          self.debugMapping[slit].append('-'+str(x.symbol))

    # TODO (future) create one propagator for each external atom (or even for each external atom literal, but then we need to find out which grounded input tuple belongs to which atom, so we might need nonground-eatom-literal-unique input tuple auxiliaries (which might hurt efficiency))
    # TODO (future) set watches for propagation on partial assignments
    
  # TODO (future) implement propagation on partial assignments
  def check(self, control):
    '''
    * get valueAuxTrue and valueAuxFalse truth values
    * get predicate input truth values/extension
    * for each true/false external atom call the plugin and add corresponding nogood
    '''
    # called on total assignments (even without watches)
    logging.info('CPcheck')
    global clingoPropControl
    clingoPropControl = control
    try:
      for eatomname, veriList in self.eatomVerifications.items():
        for veri in veriList:
          if control.assignment.is_true(veri.relevance.lit):
            self.verifyTruthOfAtom(eatomname, control, veri)
          else:
            logging.debug('CP no need to verify atom {}'.format(veri.replacement.sym))
    except ClingoPropagator.StopPropagation:
      # this is part of the intended behavior
      logging.debug('CPcheck aborted propagation')
      #logging.debug('aborted from '+traceback.format_exc())
    finally:
      # reset
      clingoPropControl = None

  def verifyTruthOfAtom(self, eatomname, control, veri):
    targetValue = control.assignment.is_true(veri.replacement.lit)
    if __debug__:
      idebug = pprint.pformat([ x.value for x in veri.allinputs if x.isTrue() ])
      logging.debug('CPvTOA checking if {} = {} with interpretation {}'.format(
        str(targetValue), veri.replacement.sym, idebug))
    holder = dlvhex.eatoms[eatomname]
    # in replacement atom everything that is not output is relevant input
    replargs = veri.replacement.sym.arguments
    inputtuple = tuple(replargs[0:len(replargs)-holder.outnum])
    outputtuple = tuple(replargs[len(replargs)-holder.outnum:len(replargs)])
    logging.debug('CPvTOA inputtuple {} outputtuple {}'.format(repr(inputtuple), repr(outputtuple)))
    out = externalAtomCallHelper(holder, inputtuple, veri.allinputs)
    logging.debug("CPvTOA output {}".format(pprint.pformat(out)))
    realValue = outputtuple in out
    if realValue == targetValue:
      logging.debug("CPvTOA positively verified!")
      # TODO somehow adding the (redundant) nogood aborts the propagation
      # this was the case with bb7ab74
      # benjamin said there is a bug, now i try the WIP branch 83038e
      return
    else:
      logging.debug("CPvTOA verification failed!")
    # add clause that ensures this value is always chosen correctly in the future
    # clause contains veri.relevance.lit, veri.replacement.lit and negation of all atoms in 

    # build nogood: solution is eliminated if ...

    # ... eatom is relevant ...
    nogood = Nogood()
    nogood.add(veri.relevance.lit)

    # ... and all inputs are as they were above ...
    for atom in veri.allinputs:
      value = control.assignment.value(atom.symlit.lit)
      if value == True:
        if not nogood.add(atom.symlit.lit):
          logging.debug("CPvTOA cannot build nogood (opposite literals)!")
          return
      elif value == False:
        if not nogood.add(-atom.symlit.lit):
          logging.debug("CPvTOA cannot build nogood (opposite literals)!")
          return
      # None case does not contribute to nogood

    checklit = None
    if realValue == True:
      # ... and computation gave true but eatom replacement is false
      checklit = -veri.replacement.lit
    else:
      # ... and computation gave false but eatom replacement is true
      checklit = veri.replacement.lit

    if not nogood.add(checklit):
      logging.debug("CPvTOA cannot build nogood (opposite literals)!")
      return

    nogood = list(nogood.literals)
    if __debug__:
      logging.debug("CPcheck adding nogood {}".format(repr(nogood)))
      for slit in nogood:
        a = abs(slit)
        logging.debug("CPcheck  {} ({}) is {}".format(a, control.assignment.value(a), repr(self.debugMapping[a])))
    may_continue = control.add_nogood(nogood)
    logging.debug("CPcheck add_nogood returned {}".format(repr(may_continue)))
    if may_continue == False:
      raise ClingoPropagator.StopPropagation()

class ModelReceiver:
  def __init__(self, facts, args):
    self.facts = set(self._normalizeFacts(facts))
    self.args = args

  def __call__(self, mdl):
    costs = mdl.cost
    if len(costs) > 0 and not mdl.optimality_proven:
      logging.info('not showing suboptimal model (like dlvhex2)!')
      return
    syms = mdl.symbols(atoms=True,terms=True)
    strsyms = [ str(s) for s in syms ]
    if self.args.nofacts:
      strsyms = [ s for s in strsyms if s not in self.facts ]
    if not self.args.auxfacts:
      strsyms = [ s for s in strsyms if not s.startswith(AUXPREFIX) ]
    if len(costs) > 0:
      # first entry = highest priority level
      # last entry = lowest priority level (1)
      logging.debug('on_model got cost'+repr(costs))
      pairs = [ '[{}:{}]'.format(p[1], p[0]+1) for p in enumerate(reversed(costs)) if p[1] != 0 ]
      costs=' <{}>'.format(','.join(pairs))
    else:
      costs = ''
    sys.stdout.write('{'+','.join(strsyms)+'}'+costs+'\n')

  def _normalizeFacts(self, facts):
    def normalize(x):
      if isinstance(x, shp.alist):
        if x.right == '.':
          assert(x.left == None and x.sep == None and len(x) == 1)
          ret = normalize(x[0])
        else:
          ret = x.sleft()+x.ssep().join([normalize(y) for y in x])+x.sright()
      elif isinstance(x, list):
        ret = ''.join([normalize(y) for y in x])
      else:
        ret = str(x)
      logging.debug('normalize({}) returns {}'.format(repr(x), repr(ret)))
      return ret
    return [normalize(f) for f in facts]

def execute(rewritten, facts, plugins, args):
  # XXX get settings from commandline
  cmdlineargs = []
  if args.number != 1:
    cmdlineargs.append(str(args.number))
  # just in case we need optimization
  cmdlineargs.append('--opt-mode=optN')
  cmdlineargs.append('--opt-strategy=usc,9')

  logging.info('sending nonground program to clingo control')
  cc = clingo.Control(cmdlineargs)
  sendprog = shp.shallowprint(rewritten)
  try:
    logging.debug('sending program ===\n'+sendprog+'\n===')
    cc.add('base', (), sendprog)
  except:
    raise Exception("error sending program ===\n"+sendprog+"\n=== to clingo:\n"+traceback.format_exc())
  #cc.register_observer(GroundProgramObserver(), False)

  logging.info('grounding with gringo context')
  ccc = GringoContext()
  cc.ground([('base',())], ccc)

  logging.info('preparing for search')
  checkprop = ClingoPropagator()
  cc.register_propagator(checkprop)
  mr = ModelReceiver(facts, args)

  logging.info('starting search')
  cc.solve(on_model=mr)

  # TODO return code for unsat/sat/opt?
  return 0

class RewritingState:
  class SignatureInfo:
    def __init__(self, relevancePred, replacementPred, arity):
      self.relevancePred = relevancePred
      self.replacementPred = replacementPred
      self.arity = arity

  def __init__(self):
    # key = eatomname, value = list of SignatureInfo
    self.eatoms = collections.defaultdict(list)
  def addSignature(self, eatomname, relevancePred, replacementPred, arity):
    self.eatoms[eatomname].append(
      self.SignatureInfo(relevancePred, replacementPred, arity))

rewritingState = RewritingState()

class EAtomHandlerBase:
  def __init__(self, holder):
    assert(isinstance(holder, dlvhex.ExternalAtomHolder))
    self.holder = holder
  def transformEAtomInStatement(self, eatom, statement, safevars, safeconditions):
    '''
    transforms eatom in self.holder in statement
    * potentially modifies statement
    * returns set of rules necessary for rewriting
      (returns statement only if last eatom in statement was rewritten)
    '''
    raise Exception("TODO: implement in child class")

class PureInstantiationEAtomHandler(EAtomHandlerBase):
  def __init__(self, holder):
    EAtomHandlerBase.__init__(self, holder)
  def transformEAtomInStatement(self, eatom, statement, safevars, safeconditions):
    '''
    transforms eatom in statement into gringo external
    with all inputs as inputs and all outputs as equivalent tuple:
      &foo[bar,baz](bam,ban)
    becomes
      @foo(bar,baz) = (bam,ban)

    * modifies statement in place
    * does not use safeconditions, safevars
    '''
    #assert(logging.debug('PIEAH '+pprint.pformat(eatom)) or True)
    replacement = eatom['prefix'] + [['@'+self.holder.name, shp.alist(eatom['inputs'], '(', ')', ',')]]
    if len(eatom['outputs']) == 0:
      # add equality with 1
      replacement.append('=')
      replacement.append(1)
    elif len(eatom['outputs']) == 1:
      # for 1 output: no tuple (it will not work correctly)
      replacement.append('=')
      replacement.append(eatom['outputs'][0])
    else:
      # for >1 outputs: use tuple
      replacement.append('=')
      replacement.append(shp.alist(eatom['outputs'], '(', ')', ','))
    # find position of eatom in body list
    posInStatement = statement[1].index(eatom['shallow'])
    logging.info('PIEAH replacing eatom '+shp.shallowprint(eatom['shallow'])+' by '+shp.shallowprint(replacement))
    statement[1][posInStatement] = replacement
    remainingEatoms = deepCollect(statement, lambda x: isinstance(x, str) and x.startswith('&'))
    #assert(logging.debug('PIEAH remainingEatoms='+repr(remainingEatoms)) or True)
    if len(remainingEatoms) == 0:
      return [statement]
    else:
      return []

class PregroundableOutputEAtomHandler(EAtomHandlerBase):
  def __init__(self, holder):
    EAtomHandlerBase.__init__(self, holder)
  def transformEAtomInStatement(self, eatom, statement, safevars, safeconditions):
    '''
    * creates a rule for instantiating the input tuple from the statement body
      - input tuple is instantiated in an auxiliary predicate
      - body of this rule contains all elements in statement that use only variables in safevars
      - this is also done for empty input tuple! (because guessing the atom is not necessary if the body is false)
    * transforms eatom in statement into auxiliary atom with all inputs and outputs
    * creates a rule for guessing truth of the auxiliary eatom based on the auxiliary input tuple
    '''
    assert(logging.debug('NOEAH eatom {} in statement {} with safevars {} and safeconditions {}'.format(
      pprint.pformat(eatom), pprint.pformat(statement), repr(safevars), pprint.pformat(safeconditions))) or True)
    out = []

    # raise an exception if outputs are non-safe variables (this case will for sure not work)
    if not eatom['outputvars'].issubset(safevars):
      raise Exception("cannot use PregroundableOutputEAtomHandler for eatom {} with output vars {} and safe vars {} in statement {}".format(pprint.pformat(eatom), repr(eatom['outputvars']), repr(safevars), shp.shallowprint(statement)))

    # auxiliary atom for relevance of external atom
    args = eatom['inputs']+eatom['outputs']
    arity = len(args)
    # one auxiliary per arity (to rule out problems with multi-arity-predicates)
    relAuxPred = '{}r{}_{}'.format(AUXPREFIX, arity, eatom['name'])
    relAuxAtom = [ relAuxPred, shp.alist(args, left='(', right=')', sep=',') ]

    # auxiliary atoms for value of external atom
    valueAuxPred = '{}t{}_{}'.format(AUXPREFIX, arity, eatom['name'])
    valueAuxAtom = [ valueAuxPred, shp.alist(args, left='(', right=')', sep=',') ]
    rewritingState.addSignature(eatom['name'], relAuxPred, valueAuxPred, arity)

    # create input instantiation rule for eatom value based on safeconditions
    # (this also determines if the atom needs to be guessed)
    if len(safeconditions) == 0:
      # fact (for keeping it uniform)
      relevanceRule = shp.alist([ relAuxAtom ], right='.')
    else:
      # rule
      relevanceRule = shp.alist([ relAuxAtom, shp.alist(safeconditions, sep=',') ], sep=':-', right='.')
    logging.debug('NOEAH relevanceRule={}'.format(shp.shallowprint(relevanceRule)))
    out.append(relevanceRule)

    # create guessing rule for eatom value based on safeconditions
    valueGuessHead = [ shp.alist([ valueAuxAtom ], left='{', right='}', sep=';') ]
    valueGuessRule = shp.alist([ valueGuessHead, shp.alist([relAuxAtom], sep=',') ], sep=':-', right='.')
    logging.debug('NOEAH valueGuessRule={}'.format(shp.shallowprint(valueGuessRule)))
    out.append(valueGuessRule)

    # replace eatom in statement
    replacement = valueAuxAtom
    # find position of eatom in body list
    posInStatement = statement[1].index(eatom['shallow'])
    logging.info('NOEAH replacing eatom '+shp.shallowprint(eatom['shallow'])+' by '+shp.shallowprint(replacement))
    statement[1][posInStatement] = replacement

    # find out if rule is completely rewritten XXX maybe the caller should decide this?
    remainingEatoms = deepCollect(statement, lambda x: isinstance(x, str) and x.startswith('&'))
    assert(logging.debug('NOEAH remainingEatoms='+repr(remainingEatoms)) or True)
    if len(remainingEatoms) == 0:
      out.append(statement)

    return out

def classifyExternalAtoms():
  '''
  For now we can only handle the following:
  * PregroundableOutputEAtomHandler:
    external atom has no output and arbitrary input
    -> we create an input instantiation (relevance) rule as in dlvhex2
    -> we transform this atom into a regular atom and add a guessing rule as in dlvhex2
    -> we use a propagator to evaluate during solving as in dlvhex2
    external atom has only output variables that are safe (without using the external atom)
    -> we create an input instantiation (relevance) rule as in dlvhex2
    -> we transform this atom into a regular atom and add a guessing rule as in dlvhex2
    -> we use a propagator to evaluate during solving as in dlvhex2
  * PureInstantiationEAtomHandler:
    external atom has only constant/tuple input(s)
    -> we transform this atom into a gringo external
    -> we do not (need to) consider it during solving
  '''
  for name, holder in dlvhex.eatoms.items():
    # uses PureInstantiationEAtomHandler if possible (even if output is 0)
    # (external atom functions cannot change during evaluation,
    # hence it is safe to evaluate these atoms in grounding)
    inspec_types = set(holder.inspec)
    if dlvhex.PREDICATE not in inspec_types:
      holder.executionHandler = PureInstantiationEAtomHandler(holder)
    #elif holder.outnum == 0:
    else:
      # let's try
      holder.executionHandler = PregroundableOutputEAtomHandler(holder)
    #else:
    #  raise Exception("cannot handle external atom '{}' from plugin '{}' because of input signature {} and nonempty ({}) output signature (please use dlvhex2)".format(
    #    name, holder.module.__name__, repr(dlvhex.humanReadableSpec(holder.inspec)), holder.outnum))

def interpretArguments(argv):
  parser = argparse.ArgumentParser(
    description='HEX-Lite - Answer Set Solver for fragment of the HEX formalism')
  parser.add_argument('hexfiles', nargs='+', metavar='HEXFILE', action='append', default=[],
    help='Filename(s) of HEX source code.')
  parser.add_argument('--pluginpath', nargs='*', metavar='PATH', action='append', default=[],
    help='Paths to search for python modules.')
  parser.add_argument('--plugin', nargs='*', metavar='MODULE', action='append', default=[],
    help='Names of python modules to load as external atoms.')
  parser.add_argument('--liberalsafety', action='store_true', default=False,
    help='Whether liberal safety is requested (ignore).')
  parser.add_argument('-n', '--number', metavar='N', action='store', default=0,
    help='Number of models to enumerate.')
  parser.add_argument('--nofacts', action='store_true', default=False,
    help='Whether to output given facts in answer set.')
  parser.add_argument('--auxfacts', action='store_true', default=False,
    help='Whether to output auxiliary facts in answer set.')
  #parser.add_argument('--solver', nargs='?', metavar='BACKEND', action='store', default=[],
  #  help='Names of solver backend to use (supported: clingo).')
  parser.add_argument('--verbose', action='store_true', default=False, help='Activate verbose mode.')
  parser.add_argument('--debug', action='store_true', default=False, help='Activate debugging mode.')
  args = parser.parse_args(argv)
  setupLogging(args)
  logging.debug('args='+repr(args))
  return args

def setupLogging(args):
  level = logging.WARNING
  if args.verbose:
    level=logging.INFO
  if args.debug:
    level=logging.DEBUG
  # call only once
  logging.getLogger().setLevel(level)
  
def main():
  try:
    args = interpretArguments(sys.argv[1:])
    setPaths(flatten(args.pluginpath))
    plugins = loadPlugins(flatten(args.plugin))
    program = loadProgram(flatten(args.hexfiles))
    rewritten, facts = rewriteProgram(program, plugins)
    code = execute(rewritten, facts, plugins, args)
    return code
  except:
    logging.error('Exception: '+traceback.format_exc())
    return -1

def loadPlugins(plugins):
  ret = []
  for p in plugins:
    pi = loadPlugin(p)
    logging.debug('for plugin '+p+' got plugin info '+repr(pi))
    ret.append(pi)
  classifyExternalAtoms()
  return ret

def setPaths(paths):
  for p in paths:
    sys.path.append(p)
  logging.info('sys.path='+repr(sys.path))

if __name__ == '__main__':
  main()
