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
import os, argparse, traceback, pprint
import shallowhexparser as shp
import dlvhex

# clingo python API
import clingo

AUXPREFIX = 'aux_'

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
  logging.info('list of known atoms is now {}'.format(', '.join(dlvhex.atoms.keys())))
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
      dbgstm = pprint.pformat(stm, width=1000)
      #logging.debug('ASR '+dbgstm)
      if isinstance(stm, shp.alist):
        sig = (stm.left, stm.sep, stm.right)
        #logging.debug('ASR alist {}'.format(repr(sig)))
        if sig == (None, None, '.'):
          # fact
          #logging.info('ASR fact/passthrough '+dbgstm)
          ret.append(StatementRewriterPassthrough(self, stm))
          facts.append(stm)
        elif sig == (None, ':-', '.'):
          # rule/constraint
          #logging.info('ASR rule/rulecstr '+dbgstm)
          ret.append(StatementRewriterRuleCstr(self, stm))
        else:
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

class StatementRewriterPassthrough(StatementRewriterBase):
  'just outputs the statement as it comes in'
  def __init__(self, pr, statement):
    StatementRewriterBase.__init__(self, pr, statement)

  def rewrite(self):
    self.pr.addRewrittenRule(self.statement)

class StatementRewriterHash(StatementRewriterBase):
  def __init__(self, pr, statement):
    StatementRewriterBase.__init__(self, pr, statement)

  def rewrite(self):
    logging.error('TODO')

class StatementRewriterRuleCstr(StatementRewriterBase):
  def __init__(self, pr, statement):
    StatementRewriterBase.__init__(self, pr, statement)

  def rewrite(self):
    #logging.debug('SRRC stm='+pprint.pformat(self.statement, width=1000))
    head, body = self.statement
    safeVars = self.findBasicSafeVariables(body)
    pendingEatoms = self.extractExternalAtoms(body)
    if len(pendingEatoms) == 0:
      self.pr.addRewrittenRule(self.statement)
    else:
      while len(pendingEatoms) > 0:
        #logging.debug('SRRC pendingEatoms='+pprint.pformat(pendingEatoms))
        #logging.debug('SRRC safeVars='+pprint.pformat(safeVars))
        safeEatm, makesSafe = self.pickSafeExternalAtom(pendingEatoms, safeVars)
        pendingEatoms.remove(safeEatm)
        #logging.debug('SRRC safeEatm='+pprint.pformat(safeEatm))
        eatomname = safeEatm['eatom'][0][1:]
        handler = dlvhex.atoms[eatomname].executionHandler
        resultRules = handler.transformEAtomInStatement(safeEatm, self.statement, safeVars)
        for r in resultRules:
          self.pr.addRewrittenRule(r)
        safeVars |= makesSafe

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
    safetyGivingAtoms = deepCollectAtDepth(body, lambda d: d == 1,
      lambda x:
        x[0] != 'not' and # NAF
        not (isinstance(x[0],str) and x[0][0] == '&') # external atoms
      )
    #logging.debug('RWR safetyGivingAtoms='+pprint.pformat(safetyGivingAtoms))
    safeVars = findVariables(safetyGivingAtoms)
    return set(safeVars)

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
    eatoms = []
    if isinstance(body, shp.alist):
      # > 1 body atom
      eatoms += [ splitPrefixEatom(x) for x in body ]
    else:
      # 1 body atom
      eatom = splitPrefixEatom(body)
      if eatom:
        eatoms.append(eatom)
    #logging.debug('eatoms1='+pprint.pformat(eatoms))
    eatoms = [ {'shallow': p_e[0] + p_e[1], 'prefix': p_e[0], 'eatom': p_e[1] }
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
      eatom['inputs'] = list(inplist[0])
      eatom['inputvars'] = set(findVariables(inplist))
      eatom['outputs'] = list(outplist[0])
      eatom['outputvars'] = set(findVariables(outplist))
      return eatom
    return [ enrich(x) for x in eatoms ]

def findVariables(structure):
  return deepCollect(structure,
    lambda x: isinstance(x, str) and x[0].isupper())

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

class GringoContext:
  class ExternalAtomCall:
    def __init__(self, holder):
      self.holder = holder
    def __call__(self, *arguments):
      logging.debug('GC.EAC(%s) called with %s',self.holder.name, repr(arguments))
      dlvhex.startExternalAtomCall()
      # prepare arguments
      plugin_arguments = []
      for spec_idx, inp in enumerate(self.holder.inspec):
        if inp in [dlvhex.PREDICATE, dlvhex.CONSTANT]:
          arg = convertClingoToHex(arguments[spec_idx])
          plugin_arguments.append(arg)
        elif inp == dlvhex.TUPLE:
          if (spec_idx + 1) != len(self.holder.inspec):
            raise Exception("got TUPLE type which is not in final argument position")
          # give all remaining arguments as one tuple
          args = [ convertClingoToHex(x) for x in arguments[spec_idx:] ]
          plugin_arguments.append(tuple(args))
        else:
          raise Exception("unknown input type "+repr(inp))
      # call external atom in plugin
      #logging.debug('calling plugin with arguments '+repr(plugin_arguments))
      self.holder.func(*plugin_arguments)
      if self.holder.outnum == 1:
        # list of terms
        out = [ convertHexToClingo(_tuple[0]) for _tuple in dlvhex.currentOutput ]
      else:
        # list of tuple of terms
        assert(self.holder.outnum != 0) # TODO will it work for 0 terms?
        out = [ tuple([ convertHexToClingo(val) for val in _tuple ]) for _tuple in dlvhex.currentOutput ]
      logging.debug('GC.EAC(%s) call returned output %s', self.holder.name, repr(out))
      dlvhex.cleanupExternalAtomCall()
      return out
      
  def __init__(self):
    pass
  def __getattr__(self, attr):
    #logging.debug('GC.%s called',attr)
    return self.ExternalAtomCall(dlvhex.atoms[attr])

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


class ModelReceiver:
  def __init__(self, facts, nofacts=False):
    self.facts = set(self._normalizeFacts(facts))
    self.nofacts = nofacts

  def __call__(self, mdl):
    syms = mdl.symbols(atoms=True,terms=True)
    strsyms = [ str(s) for s in syms ]
    if self.nofacts:
      strsyms = [ s for s in strsyms if s not in self.facts ]
    strsyms = [ s for s in strsyms if not s.startswith(AUXPREFIX) ]
    sys.stdout.write('{'+','.join(strsyms)+'}\n')

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
  #cmdlineargs = ['--opt-mode=usc,9']
  # XXX get settings from commandline
  cmdlineargs = []

  logging.info('sending nonground program to clingo control')
  cc = clingo.Control(cmdlineargs)
  cc.add('base', (), shp.shallowprint(rewritten))
  #cc.register_observer(GroundProgramObserver(), False)

  logging.info('grounding with gringo context')
  ccc = GringoContext()
  cc.ground([('base',())], ccc)

  logging.warning('TODO prepare/register propagator')
  mr = ModelReceiver(facts, args.nofacts)
  cc.solve(on_model=mr)
  # TODO return code for unsat/sat/opt
  return 0

class EAtomHandlerBase:
  def __init__(self, holder):
    assert(isinstance(holder, dlvhex.ExternalAtomHolder))
    self.holder = holder
  def transformEAtomInStatement(self, eatom, statement, safevars):
    '''
    transforms eatom in self.holder in statement
    * potentially modifies statement
    * returns set of rules necessary for rewriting
      (returns statement only if last eatom in statement was rewritten)
    '''
    logging.error("TODO implement in child class")
    return []

class NoOutputEAtomHandler(EAtomHandlerBase):
  def __init__(self, holder):
    EAtomHandlerBase.__init__(self, holder)
  def transformEAtomInStatement(self, eatom, statement, safevars):
    '''
    * creates a rule for instantiating the input tuple from the statement body
      - input tuple is instantiated in an auxiliary predicate
      - body of this rule contains all elements in statement that use only variables in safevars
      - this is also done for empty input tuple! (because guessing the atom is not necessary if the body is false)
    * transforms eatom in statement into auxiliary atom with all inputs and outputs
    * creates a rule for guessing truth of the auxiliary eatom based on the auxiliary input tuple
    '''
    logging.error("TODO implement")
    return []

class PureInstantiationEAtomHandler(EAtomHandlerBase):
  def __init__(self, holder):
    EAtomHandlerBase.__init__(self, holder)
  def transformEAtomInStatement(self, eatom, statement, safevars):
    '''
    transforms eatom in statement into gringo external
    with all inputs as inputs and all outputs as equivalent tuple:
      &foo[bar,baz](bam,ban)
    becomes
      @foo(bar,baz) = (bam,ban)
    '''
    #assert(logging.debug('PIEAH '+pprint.pformat(eatom)) or True)
    replacement = eatom['prefix'] + [['@'+self.holder.name, shp.alist(eatom['inputs'], '(', ')', ',')]]
    if len(eatom['outputs']) == 1:
      # for 1 output: no tuple (it will not work correctly)
      replacement.append('=')
      replacement.append(eatom['outputs'][0])
    else:
      # for 0 and >1 outputs: use tuple
      assert(len(eatom['outputs']) != 0) # TODO will it work correctly for 0?
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

def classifyExternalAtoms():
  '''
  For now we can only handle the following:
  * NoOutputEAtomHandler:
    external atom has no output and arbitrary input
    -> we transform this atom into an input/guessing rule as in dlvhex2
    -> we use a propagator to evaluate during solving
  * PureInstantiationEAtomHandler:
    external atom has only constant/tuple input(s)
    -> we transform this atom into a gringo external
    -> we do not (need to) consider it during solving
  '''
  for name, holder in dlvhex.atoms.items():
    # uses PureInstantiationEAtomHandler if possible (even if output is 0)
    # (external atom functions cannot change during evaluation,
    # hence it is safe to evaluate these atoms in grounding)
    inspec_types = set(holder.inspec)
    if dlvhex.PREDICATE not in inspec_types:
      holder.executionHandler = PureInstantiationEAtomHandler(holder)
    elif holder.outnum == 0:
      holder.executionHandler = NoOutputEAtomHandler(holder)
    else:
      raise Exception("cannot handle external atom '{}' from plugin '{}' because of input signature {} and nonempty ({}) output signature (please use dlvhex2)".format(
        name, holder.module.__name__, repr(dlvhex.humanReadableSpec(holder.inspec)), holder.outnum))

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
  parser.add_argument('--nofacts', action='store_true', default=False,
    help='Whether to output given facts in answer set.')
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
