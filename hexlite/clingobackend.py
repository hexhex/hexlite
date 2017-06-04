# encoding: utf8
# This module handles evaluation of external atoms via plugins for the Clingo backend.

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

import logging
import collections
import pprint
import dlvhex

from . import common as hexlite
flatten=hexlite.flatten

# assume that the main program has handled possible import problems
import clingo

class ClaspContext:
  '''
  context within the propagator
  '''
  def __init__(self):
    self.propcontrol = None
  def __call__(self, control):
    '''
    initialize context with control object
    '''
    assert(self.propcontrol == None)
    assert(control != None)
    self.propcontrol = control
    return self
  def __enter__(self):
    pass
  def __exit__(self, type, value, traceback):
    self.propcontrol = None

class SymLit:
  '''
  Holds the symbol of a symbolic atom of Clingo plus its solver literal.

  x <- init.symbolic_atoms.by_signature
  sym <- x.symbol
  lit <- init.solver_literal(x.literal)
  '''
  def __init__(self, sym, lit):
    self.sym = sym
    self.lit = lit

class ClingoID:
  # the ID class as passed to plugins, from view of Clingo backend
  def __init__(self, ccontext, symlit):
    assert(isinstance(ccontext, ClaspContext))
    self.ccontext = ccontext
    self.symlit = symlit
    self.__value = str(symlit.sym)

  def value(self):
    return self.__value

  def intValue(self):
    if self.symlit.sym.type == clingo.SymbolType.Number:
      return self.symlit.sym.number
    else:
      raise Exception('intValue called on ID {} which is not a number!'.format(self.__value))

  def isTrue(self):
    if not self.symlit.lit:
      raise Exception("cannot call isTrue on term that is not an atom")
    return self.__assignment().is_true(self.symlit.lit)

  def isFalse(self):
    if not self.symlit.lit:
      raise Exception("cannot call isFalse on term that is not an atom")
    return self.__assignment().is_false(self.symlit.lit)

  def isAssigned(self):
    if not self.symlit.lit:
      raise Exception("cannot call isAssigned on term that is not an atom")
    return self.__assignment().value(self.symlit.lit) != None

  def tuple(self):
    tup = tuple([ ClingoID(self.ccontext, SymLit(sym, None)) for sym in
                  [clingo.Function(self.symlit.sym.name)]+self.symlit.sym.arguments])
    return tup

  def __assignment(self):
    return self.ccontext.propcontrol.assignment

  def __str__(self):
    return self.__value

  def __repr__(self):
    return "ClingoID({})".format(str(self))

  def __getattr__(self, name):
    raise Exception("not (yet) implemented: ClingoID.{}".format(name))

class EAtomEvaluator:
  '''
  Clingo-backend-specific evaluation of external atoms implemented in Python
  using the same API as in the dlvhex solver (but fully realized in Python).

  This closely interacts with the dlvhex package.
  '''
  def __init__(self, claspcontext):
    assert(isinstance(claspcontext, ClaspContext))
    self.ccontext = claspcontext

  def clingo2hex(self, term):
    assert(isinstance(term, clingo.Symbol))
    #logging.debug("convertClingoToHex got {} with type {}".format(repr(term), term.type))
    return ClingoID(self.ccontext, SymLit(term, None))
    #if term.type is clingo.SymbolType.Number:
    #  ret = term.number
    #elif term.type in [clingo.SymbolType.String, clingo.SymbolType.Function]:
    #  ret = str(term)
    #else:
    #  raise Exception("cannot convert clingo term {} of type {} to external atom term!".format(
    #    repr(term), str(term.type)))
    #return ret

  def hex2clingo(self, term):
    if isinstance(term, ClingoID):
      return term.symlit.sym
    elif isinstance(term, str):
      if term[0] == '"':
        ret = clingo.String(term[1:-1])
      else:
        ret = clingo.parse_term(term)
    elif isinstance(term, int):
      ret = clingo.Number(term)
    else:
      raise Exception("cannot convert external atom term {} to clingo term!".format(repr(term)))
    return ret


  def evaluate(self, holder, inputtuple, predicateinputatoms):
    '''
    Convert input tuple (from clingo to dlvhex) and call external atom semantics function.
    Convert output tuple (from dlvhex to clingo).

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
          arg = self.clingo2hex(inputtuple[spec_idx])
          plugin_arguments.append(arg)
        elif inp == dlvhex.TUPLE:
          if (spec_idx + 1) != len(holder.inspec):
            raise Exception("got TUPLE type which is not in final argument position")
          # give all remaining arguments as one tuple
          args = [ self.clingo2hex(x) for x in inputtuple[spec_idx:] ]
          plugin_arguments.append(tuple(args))
        else:
          raise Exception("unknown input type "+repr(inp))

      # call external atom in plugin
      logging.debug('calling plugin eatom with arguments '+repr(plugin_arguments))
      holder.func(*plugin_arguments)
      
      # interpret output
      # list of tuple of terms (maybe empty tuple)
      out = [ tuple([ self.hex2clingo(val) for val in _tuple ]) for _tuple in dlvhex.currentOutput ]
    finally:
      dlvhex.cleanupExternalAtomCall()
    return out

class GringoContext:
  class ExternalAtomCall:
    def __init__(self, eaeval, holder):
      self.eaeval = eaeval
      self.holder = holder
    def __call__(self, *arguments):
      logging.debug('GC.EAC(%s) called with %s',self.holder.name, repr(arguments))
      out = self.eaeval.evaluate(self.holder, arguments, None)
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
        if any([ len(x) != outarity for x in out ]):
          wrongarity = [ x for x in out if len(x) != outarity ]
          out = [ x for x in out if len(x) == outarity ]
          logging.warning("ignored tuples {} with wrong arity from atom {}".format(repr(wrongarity), self.holder.name))
        out = [ x[0] for x in out ]
      # in other cases we can directly use what externalAtomCallHelper returned
      logging.debug('GC.EAC(%s) call returned output %s', self.holder.name, repr(out))
      return out
  def __init__(self, eaeval):
    assert(isinstance(eaeval, EAtomEvaluator))
    self.eaeval = eaeval
  def __getattr__(self, attr):
    #logging.debug('GC.%s called',attr)
    return self.ExternalAtomCall(self.eaeval, dlvhex.eatoms[attr])


class ClingoPropagator:

  class EAtomVerification:
    """
    stores everything required to evaluate truth of one ground external atom in propagation:
    * relevance atom (do we need to evaluate it?)
    * replacement atom (was it guessed true or false? which arguments does it have?)
    * the full list of atoms relevant as predicate inputs (required to evaluate the external atom semantic function)
    """
    def __init__(self, relevance, replacement):
      # symlit for ground eatom relevance
      self.relevance = relevance
      # symlit for ground eatom replacement
      self.replacement = replacement
      # key = argument position, value = list of ClingoID
      self.predinputs = collections.defaultdict(list)
      # list of all elements in self.predinputs (cache)
      self.allinputs = None

  class Nogood:
    def __init__(self):
      self.literals = set()

    def add(self, lit):
      if -lit in self.literals:
        return False
      self.literals.add(lit)
      return True


  class StopPropagation(Exception):
    pass

  def __init__(self, pcontext, ccontext, eaeval):
    # key = eatom
    # value = list of EAtomVerification
    self.eatomVerifications = collections.defaultdict(list)
    # mapping from solver literals to lists of strings
    self.debugMapping = collections.defaultdict(list)
    # program context
    self.pcontext = pcontext
    # clasp context
    self.ccontext = ccontext
    # helper for external atom evaluation
    self.eaeval = eaeval
  def init(self, init):
    # register mapping for solver/grounder atoms!
    # no need for watches as long as we use only check()
    for eatomname, signatures in self.pcontext.eatoms.items():
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

          verification = self.EAtomVerification(relevance, replacement)

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
                  predinputid = ClingoID(self.ccontext, SymLit(ax.symbol, init.solver_literal(ax.literal)))
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

    # TODO (near future) implement this current type of check in on_model where we can comfortably add all nogoods immediately
    # TODO (far future) create one propagator for each external atom (or even for each external atom literal)
    #                   which watches predicate inputs, relevance, and replacement, and incrementally finds when it should compute
    #                   [then we need to find out which grounded input tuple belongs to which atom, so we might need
    #                    nonground-eatom-literal-unique input tuple auxiliaries (which might hurt efficiency)]
  def check(self, control):
    '''
    * get valueAuxTrue and valueAuxFalse truth values
    * get predicate input truth values/extension
    * for each true/false external atom call the plugin and add corresponding nogood
    '''
    # called on total assignments (even without watches)
    logging.info('CPcheck')
    with self.ccontext(control):
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

  def verifyTruthOfAtom(self, eatomname, control, veri):
    targetValue = control.assignment.is_true(veri.replacement.lit)
    if __debug__:
      idebug = pprint.pformat([ x.value() for x in veri.allinputs if x.isTrue() ])
      logging.debug('CPvTOA checking if {} = {} with interpretation {}'.format(
        str(targetValue), veri.replacement.sym, idebug))
    holder = dlvhex.eatoms[eatomname]
    # in replacement atom everything that is not output is relevant input
    replargs = veri.replacement.sym.arguments
    inputtuple = tuple(replargs[0:len(replargs)-holder.outnum])
    outputtuple = tuple(replargs[len(replargs)-holder.outnum:len(replargs)])
    logging.debug('CPvTOA inputtuple {} outputtuple {}'.format(repr(inputtuple), repr(outputtuple)))
    out = self.eaeval.evaluate(holder, inputtuple, veri.allinputs)
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
    nogood = self.Nogood()
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
