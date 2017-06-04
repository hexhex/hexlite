# encoding: utf8
# This module provides program rewriting for finding compatible sets of a HEX program.

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

import pprint
import logging

# the . module is called hexlite but we cannot import it, so we use the common trick in hexlite/__init__.py
# see https://stackoverflow.com/questions/3078927/python-how-to-access-variable-declared-in-parent-module
from . import common as hexlite
from . import ast
from .ast import shallowparser as shp
from . import aux
Aux = aux.Aux

import dlvhex

class ProgramRewriter:
  def __init__(self, pcontext, shallowprogram, plugins, args):
    assert(isinstance(pcontext, hexlite.ProgramContext))
    self.pcontext = pcontext
    self.shallowprog = shallowprogram
    self.plugins = plugins
    self.args = args
    self.srprog, self.facts = self.__annotateWithStatementRewriters()
    self.rewritten = []

  def rewrite(self):
    '''
    returns rewritten_program, facts
    '''
    # rewriters append to self.rewritten
    for stm in self.srprog:
      stm.rewrite()
    if not self.pcontext.wroteMaxint and self.args.maxint is not None:
      maxintConst = shp.alist(['#const', Aux.MAXINT, '=', self.args.maxint], right='.')
      logging.info("adding maxint rule (from commandline) "+shp.shallowprint(maxintConst))
      self.addRewrittenRule(maxintConst)
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
        logging.debug('ASR stm='+dbgstm)
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
        elif sig == (None, ':~', '.'):
          # weak constraint without weights (with weights would be caught below)
          defaultweight = shp.alist([['1'], ['1']], left='[', right=']', sep=':')
          extendedWeakConstraint = [stm, defaultweight]
          if __debug__:
            logging.debug('ASR extended weak constraint {} into {}'.format(
              dbgstm, pprint.pformat(extendedWeakConstraint)))
          ret.append(StatementRewriterWeakCstr(self, extendedWeakConstraint))
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


class EAtomHandlerBase:
  def __init__(self, pcontext, holder):
    assert(isinstance(pcontext, hexlite.ProgramContext))
    assert(isinstance(holder, dlvhex.ExternalAtomHolder))
    self.pcontext = pcontext
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
  def __init__(self, pcontext, holder):
    EAtomHandlerBase.__init__(self, pcontext, holder)
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
    remainingEatoms = ast.deepCollect(statement, lambda x: isinstance(x, str) and x.startswith('&'))
    #assert(logging.debug('PIEAH remainingEatoms='+repr(remainingEatoms)) or True)
    if len(remainingEatoms) == 0:
      return [statement]
    else:
      return []


class PregroundableOutputEAtomHandler(EAtomHandlerBase):
  def __init__(self, pcontext, holder):
    EAtomHandlerBase.__init__(self, pcontext, holder)
  def transformEAtomInStatement(self, eatom, statement, safevars, safeconditions):
    '''
    * creates a rule for instantiating the input tuple from the statement body
      - input tuple is instantiated in an auxiliary predicate
      - body of this rule contains all elements in statement that use only variables in safevars
      - this is also done for empty input tuple! (because guessing the atom is not necessary if the body is false)
    * transforms eatom in statement into auxiliary atom with all inputs and outputs
    * creates a rule for guessing truth of the auxiliary eatom based on the auxiliary input tuple
    '''
    if __debug__:
      logging.debug('NOEAH eatom {} with safevars {} and safeconditions {}'.format(
        pprint.pformat(eatom), repr(safevars), pprint.pformat(safeconditions)))
      logging.debug('NOEAH in statement '+pprint.pformat(statement))
    out = []

    # raise an exception if outputs are non-safe variables (this case will for sure not work)
    if not eatom['outputvars'].issubset(safevars):
      raise Exception("cannot use PregroundableOutputEAtomHandler for eatom {} with output vars {} and safe vars {} in statement {}".format(pprint.pformat(eatom), repr(eatom['outputvars']), repr(safevars), shp.shallowprint(statement)))

    # auxiliary atom for relevance of external atom
    args = eatom['inputs']+eatom['outputs']
    arity = len(args)
    # one auxiliary per arity (to rule out problems with multi-arity-predicates)
    relAuxPred = aux.predEAtomRelevance(arity, eatom['name'])
    relAuxAtom = [ relAuxPred, shp.alist(args, left='(', right=')', sep=',') ]

    # auxiliary atoms for value of external atom
    valueAuxPred = aux.predEAtomTruth(arity, eatom['name'])
    valueAuxAtom = [ valueAuxPred, shp.alist(args, left='(', right=')', sep=',') ]
    self.pcontext.addSignature(eatom['name'], relAuxPred, valueAuxPred, arity)

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
    replacement = eatom['prefix'] + valueAuxAtom
    # find position of eatom in body list
    posInStatement = statement[1].index(eatom['shallow'])
    logging.info('NOEAH replacing eatom '+shp.shallowprint(eatom['shallow'])+' by '+shp.shallowprint(replacement))
    statement[1][posInStatement] = replacement

    # find out if rule is completely rewritten XXX maybe the caller should decide this?
    remainingEatoms = ast.deepCollect(statement, lambda x: isinstance(x, str) and x.startswith('&'))
    assert(logging.debug('NOEAH remainingEatoms='+repr(remainingEatoms)) or True)
    if len(remainingEatoms) == 0:
      out.append(statement)

    return out

def classifyEAtomsInstallRewritingHandlers(pcontext):
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
      holder.executionHandler = PureInstantiationEAtomHandler(pcontext, holder)
    #elif holder.outnum == 0:
    else:
      # let's try
      holder.executionHandler = PregroundableOutputEAtomHandler(pcontext, holder)
    #else:
    #  raise Exception("cannot handle external atom '{}' from plugin '{}' because of input signature {} and nonempty ({}) output signature (please use dlvhex2)".format(
    #    name, holder.module.__name__, repr(dlvhex.humanReadableSpec(holder.inspec)), holder.outnum))


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
          elem[:] = [term, '=', '0', '..', Aux.MAXINT]
          if __debug__:
            logging.debug("rewrote {} to {}".format(pprint.pformat(orig), pprint.pformat(elem)))
    ast.dfVisit(self.statement, rewriteIfApplicable)

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
      self.statement[0][0:1] = ['#const', Aux.MAXINT]
      self.pr.addRewrittenRule(self.statement)
      self.pr.pcontext.wroteMaxint = True
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
    safetyGivingAtoms = ast.deepCollectAtDepth(body, lambda d: d == 1,
      lambda x:
        (x[0] != 'not') and # NAF
        not (isinstance(x[0],str) and x[0][0] == '&') # external atoms
      )
    logging.debug('SRRC safetyGivingAtoms='+pprint.pformat(safetyGivingAtoms))
    safeVars = ast.findVariables(safetyGivingAtoms)
    return set(safeVars)

  def findSafeConditions(self, body, safeVars):
    '''
    find all body elements that are not external atoms
    and that are safe assuming safeVars are safe

    currently:
    * finds all positive body literals
    * finds all negated body literals that contain only variables from safeVars
    * XXX implicitly finds rewritten external atoms(?)
    * XXX see findBasicSafeVariables for potentially problematic cases
    '''
    #logging.debug('SRRC findSafeConditions for safeVars {} and body {}'.format(repr(safeVars), pprint.pformat(body)))
    def isSafe(elem):
      #logging.debug('SRRC isSafe='+pprint.pformat(elem))
      isEatom = any([isinstance(subelem,str) and subelem[0] == '&' for subelem in elem])
      if isEatom:
        # for sure do not return untransformed external atoms
        return False
      if elem[0] != 'not':
        # positive literal
        return True
      else:
        # negative literal
        usedVariables = set(ast.findVariables(elem))
        if usedVariables.issubset(safeVars):
          return True
      return False
    safeRewrittenLiterals = ast.deepCollectAtDepth(body, lambda d: d == 1, isSafe)
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
      if __debug__:
        logging.debug('splitPrefixEatom({})'.format(pprint.pformat(x)))
      if isinstance(x,shp.alist):
        # maybe expansion (lit : lit) or disjunction (lit ; lit)
        # TODO how about external atoms in expansions/disjunctions/aggregates?
        return None
      else:
        # literal
        assert(isinstance(x,list))
        checkIdx = 0
        # skip over not's
        while len(x) > checkIdx and x[checkIdx] == 'not':
          checkIdx += 1
        if len(x) > checkIdx and isinstance(x[checkIdx], str) and x[checkIdx][0].startswith('&'):
          return x[:checkIdx], x[checkIdx:]
        else:
          # TODO how about external atoms in aggregates?
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
      eatom['inputvars'] = set(ast.findVariables(inplist))
      if len(outplist) == 0:
        eatom['outputs'] = []
      else:
        eatom['outputs'] = list(outplist[0])
      eatom['outputvars'] = set(ast.findVariables(outplist))
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
