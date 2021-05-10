# encoding: utf8
# This module handles evaluation of external atoms via plugins for the Clingo backend.

# HEXLite Python-based solver for a fragment of HEX
# Copyright (C) 2017-2019  Peter Schueller <schueller.p@gmail.com>
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

import sys
import logging
import collections
import itertools
import pprint
import traceback
import json

import dlvhex

from . import common as hexlite
from . import auxiliary as aux
from .ast import shallowparser as shp
from . import explicitflpcheck as flp
from . import modelcallback

from .clingogroundprogramprinter import GroundProgramPrinter

# assume that the main program has handled possible import problems
import clingo


class ClaspContext:
  '''
  context within the propagator
  * clasp context with PropagateControl object
  * ClingoPropagator object that contains, e.g., propagation init symbol information
  '''
  def __init__(self):
    self.propcontrol = None
    self.propagator = None
    
  def __call__(self, control, propagator):
    '''
    initialize context with control object
    '''
    assert(self.propcontrol == None)
    assert(control != None)
    assert(isinstance(control, clingo.PropagateControl))
    self.propcontrol = control
    assert(isinstance(propagator, ClingoPropagator))
    self.propagator = propagator
    return self
  def __enter__(self):
    pass
  def __exit__(self, type, value, traceback):
    self.propcontrol = None
    self.propagator = None

class SymLit:
  '''
  Holds the symbol of a symbolic atom of Clingo plus its solver literal.

  x <- init.symbolic_atoms.by_signature
  sym <- x.symbol
  lit <- init.solver_literal(x.literal)

  if lit is None, then
  * sym is a term and not an atom and there is no solver literal
  * sym is used as a non-predicate-input to an external atom (TODO ensure this is always true)
  * TODO document other cases
  '''
  def __init__(self, sym, lit):
    self.sym = sym
    #if lit is None:
    #  logging.warning("SYMLIT {} with empty LIT from {}".format(sym, '\n'.join(traceback.format_stack())))
    self.lit = lit

  def __hash__(self):
    return hash(self.sym)

  def __str__(self):
    return "{}/{}".format(self.sym, self.lit)


class ClingoID(dlvhex.ID):
  # the ID class as passed to plugins, from view of Clingo backend
  def __init__(self, ccontext, symlit):
    assert(isinstance(ccontext, ClaspContext))
    self.ccontext = ccontext
    self.symlit = symlit
    self.__value = str(symlit.sym)

  def negate(self):
    if self.symlit.sym.type != clingo.SymbolType.Function:
      raise Exception("cannot negate non-function symbols!")
    return ClingoID(self.ccontext, SymLit(
      clingo.Function(self.symlit.sym.name, self.symlit.sym.arguments, self.symlit.sym.negative),
      -self.symlit.lit))

  def value(self):
    return self.__value

  def intValue(self):
    if self.symlit.sym.type == clingo.SymbolType.Number:
      return self.symlit.sym.number
    else:
      raise Exception('intValue called on ID {} which is not a number!'.format(self.__value))

  def isPositive(self):
    return self.symlit.sym.positive

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

  def isInteger(self):
    return self.symlit.sym.type == clingo.SymbolType.Number

  def tuple(self):
    tup = tuple([ ClingoID(self.ccontext, SymLit(sym, None)) for sym in
                  [clingo.Function(self.symlit.sym.name)]+self.symlit.sym.arguments])
    return tup

  def extension(self):
    '''
    returns a sequence of tuples of true atoms with predicate using this ClingoID
    fails if this ClingoID does not hold a constant
    '''
    if self.symlit.sym.type != clingo.SymbolType.Function or self.symlit.sym.arguments != []:
      raise Exception("cannot call extension() on term that is not a constant. was called on {}".format(self.__value))
    # extract all true atoms with matching predicate name
    ret_atoms = [
      x for x in dlvhex.getTrueInputAtoms()
      if x.symlit.sym.type == clingo.SymbolType.Function and x.symlit.sym.name == self.__value ]
    # convert into tuples of ClingoIDs without literal (they are terms, not atoms)
    ret = frozenset([
      tuple([ClingoID(self.ccontext, SymLit(term, None)) for term in x.symlit.sym.arguments])
      for x in ret_atoms ])
    #logging.warning("extension of {} returned {}".format(self.__value, repr(ret)))
    return ret

  def __assignment(self):
    return self.ccontext.propcontrol.assignment

  def __str__(self):
    return self.__value

  def __repr__(self):
    return "ClingoID({})/{}".format(str(self), self.symlit.lit)

  def __hash__(self):
    return hash(self.symlit)

  def __eq__(self, other):
    if isinstance(other, str):
      return self.value() == other
    elif isinstance(other, int) and self.symlit.sym.type == clingo.SymbolType.Number:
      return self.intValue() == other
    elif isinstance(other, ClingoID):
      return self.symlit.sym == other.symlit.sym
    else:
      return self.value() == other

  def __getattr__(self, name):
    raise Exception("not (yet) implemented: ClingoID.{}".format(name))

class EAtomEvaluator(dlvhex.Backend):
  '''
  Clingo-backend-specific evaluation of external atoms implemented in Python
  using the same API as in the dlvhex solver (but fully realized in Python).

  This closely interacts with the dlvhex package.

  This is one object that evaluates all external atoms in the context of a clasp context.
  '''
  def __init__(self, config, claspcontext, stats):
    assert(isinstance(claspcontext, ClaspContext))
    self.config = config
    self.ccontext = claspcontext
    self.stats = stats

    # set of all replacement atom symbols so that we can detect them in nogoods
    # this is initialized by ClingoPropagator.init
    self.replacementAtoms = set()

    # key = replacement symbol
    # value = single EAtomVerification in ClingoPropagator.eatomVerifications.values()
    # this is initialized by ClingoPropagator.init
    self.eatomVerificationsByReplacement = {}

    # list of nogoods that still need to be added
    # (in an external atom call, dlvhex.learn() collects nogoods here and adds them later)
    self.nogoodsToAdd = set()

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
        try:
          ret = clingo.parse_term(term)
        except:
          logging.warning("cannot parse external atom term {} with clingo! (creating a string out of it)".format(repr(term)))
          ret = clingo.String(str(term))
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
    * return result (known true tuples, unknown tuples)
    '''
    with self.stats.context('eatom'+holder.name):
      # prepare input tuple
      input_arguments = []
      if __debug__ and len(inputtuple) < len(holder.inspec):
        # this should be detected already in rewriting in transformEAtomInStatement()
        raise Exception("external atom {} got fewer inputs ({}) in input tuple ({}) than declared in interface ({})".format(
          holder.name, len(inputtuple), inputtuple, dlvhex.humanReadableSpec(holder.inspec)))
      for spec_idx, inp in enumerate(holder.inspec):
        if inp in [dlvhex.PREDICATE, dlvhex.CONSTANT]:
          arg = self.clingo2hex(inputtuple[spec_idx])
          input_arguments.append(arg)
        elif inp == dlvhex.TUPLE:
          if (spec_idx + 1) != len(holder.inspec):
            raise Exception("got TUPLE type which is not in final argument position")
          # give all remaining arguments as one tuple
          args = [ self.clingo2hex(x) for x in inputtuple[spec_idx:] ]
          input_arguments.append(tuple(args))
        else:
          raise Exception("unknown input type "+repr(inp))

      # call external atom in plugin
      dlvhex.startExternalAtomCall(input_arguments, predicateinputatoms, self, holder)
      outKnownTrue, outUnknown = set(), set()
      try:
        logging.debug('calling plugin eatom with arguments '+repr(input_arguments))
        holder.func(*input_arguments)
        
        # sanity check
        inconsistent = set.intersection(dlvhex.currentEvaluation().outputKnownTrue, dlvhex.currentEvaluation().outputUnknown)
        if len(inconsistent) > 0:
          raise Exception('external atom {} with arguments {} provided the following tuples both as true and unknown: {} partial interpretation is {}'.format(holder.name, repr(input_arguments), repr(inconsistent), repr(predicateinputatoms)))

        # interpret output that is known to be true
        outKnownTrue = [ tuple([ self.hex2clingo(val) for val in _tuple ])
                         for _tuple in dlvhex.currentEvaluation().outputKnownTrue ]

        # interpret output that is unknown whether it is false or true (in partial evaluation)
        outUnknown = [ tuple([ self.hex2clingo(val) for val in _tuple ])
                       for _tuple in dlvhex.currentEvaluation().outputUnknown ]
      finally:
        dlvhex.cleanupExternalAtomCall()
      return outKnownTrue, outUnknown
  
  # implementation of Backend method
  def storeAtom(self, tpl):
    '''
    this can only be called from an external atom code of a user
    it is called after
      dlvhex.startExternalAtomCall(predicateinputatoms, self)
    has been called and the only atoms we can store here are from predicateinputatoms
    (because we do not invent new variables and we cannot access variables that are not about our predicate inputs)

    so we only need to check if tpl is in predicateinputatoms and return the corresponding ClingoID
    '''
    match_name = tpl[0].symlit.sym.name
    match_arguments = [t.symlit.sym for t in tpl[1:]]
    #print("match_name = {} match_arguments = {}".format(repr(match_name), repr(match_arguments)))
    for x in dlvhex.currentEvaluation().input:
      #logging.info("storeAtom comparing {} with {}: xsxn {} xssa {}".format(repr(tpl), repr(x), repr(x.symlit.sym.name), repr(x.symlit.sym.arguments)))
      if x.symlit.sym.name == match_name and x.symlit.sym.arguments == match_arguments:
        #logging.info("storeAtom found {}".format(repr(x)))
        return x
    raise dlvhex.StoreAtomException("storeAtom() called with tuple {} that cannot be stored because it is not part of the predicate input or not existing in the ground rewriting (we have no liberal safety)".format(repr(tpl)))

  # implementation of Backend method
  def storeOutputAtom(self, args, sign):
    '''
    this can only be called from an external atom code of a user
    it is called after
      dlvhex.startExternalAtomCall(predicateinputatoms, self, holder)
    has been called and the only atoms we can store here are external atom replacement atoms that exist in the theory

    so we only need to assemble the correct tuple and check if it exists in clingo and return the corresponding ClingoID (only literal matters)
    '''
    #logging.debug("got dlvhex.currentEvaluation().holder.name {}".format(dlvhex.currentEvaluation().holder.name))
    #logging.debug("got self.ccontext.propagator.eatomVerifications[dlvhex.currentEvaluation().holder.name] {}".format(repr([ x.replacement.sym for x in self.ccontext.propagator.eatomVerifications[dlvhex.currentEvaluation().holder.name]])))

    eatomname = dlvhex.currentEvaluation().holder.name
    inputtuple = dlvhex.currentEvaluation().inputTuple
    match_args = [t.symlit.sym for t in itertools.chain(inputtuple, args)]
    #print("looking up {}".format(repr(match_args)))
    # find those verification objects that contain the tuple to be stored
    # XXX maybe first use self.ccontext.propagator.currentVerification as a possible shortcut
    # (works if the external atom creates nogood for the output tuple of the verification where it was called)
    for x in self.ccontext.propagator.eatomVerifications[eatomname]:
      #logging.info("storeOutputAtom {} comparing {} with {}".format(sign, repr(args), repr(x.replacement.sym.arguments)))
      if x.replacement.sym.arguments == match_args:
        #logging.info("storeOutputAtom found replacement {}".format(x.replacement))
        return ClingoID(self.ccontext, x.replacement)
    #  if x.symlit.sym.name == match_name and x.symlit.sym.arguments == match_arguments:
    raise dlvhex.StoreAtomException("did not find literal to return in storeOutputAtom for &{}[{}]({})".format(eatomname, inputtuple, repr(args)))

  def getInstantiatedOutputAtoms(self):
    '''
    as storeOutputAtom, but returns all output atoms that have been instantiated for the currently called external atom
    '''
    eatomname = dlvhex.currentEvaluation().holder.name
    return [  ClingoID(self.ccontext, x.replacement)
              for x in self.ccontext.propagator.eatomVerifications[eatomname] ]

  def storeConstant(self, s: str):
    if len(s) == 0 or (s[0] == '"' and s[1] == '"'):
      # TODO this is only for backwards compatibility, should be removed in V2
      logging.warning("storeConstant() was used on string '%s', use storeString in the future", s)
      if len(s) == 0:
        return ClingoID(self.ccontext, SymLit(clingo.String(''), None))
      else:
        return ClingoID(self.ccontext, SymLit(clingo.String(s), None))
    return ClingoID(self.ccontext, SymLit(clingo.Function(s), None))

  def storeString(self, s: str):
    if len(s) > 0 and s[0] == '"' and s[1] == '"':
      s = s[1:-1]
    return ClingoID(self.ccontext, SymLit(clingo.String(s), None))

  def storeInteger(self, i: int):
    return ClingoID(self.ccontext, SymLit(clingo.Number(i), None))

  def storeParseable(self, p: str):
    return ClingoID(self.ccontext, SymLit(clingo.parse_term(p), None))

  # implementation of Backend method
  def learn(self, ng):
    '''
    learn a nogood from an external atom call
    this method is directly called from the external atom code
    it does not actually add nogoods to the solver but collects them
    '''
    if not self.config.enable_eatom_specified_nogoods:
      logging.info("ignored eatom-specified nogood %s due to configuration", ng)
      return

    with self.stats.context('spec-learn'):
      logging.info("learning eatom-specified nogood %s", ng)
      assert(all([isinstance(clingoid, ClingoID) for clingoid in ng]))

      # convert and validate
      nogood = self.ccontext.propagator.Nogood()
      replacementAtomSymLit = None
      replacementAtomPositiveSym = None
      for clingoid in ng:
        if clingoid.isPositive():
          positive = clingoid
        else:
          positive = clingoid.negate()
        if positive.symlit.sym in self.replacementAtoms:
          replacementAtomSymLit = clingoid.symlit
          replacementAtomPositiveSymLit = positive.symlit
        if not nogood.add(clingoid.symlit.lit):
          logging.info("cannot build nogood (opposite literals)!")
          return

      if replacementAtomSymLit is None:
        # we intend nogoods to only specify truth of replacement atoms = truth of external atom evaluations
        logging.warning("learn() obtained nogood %s which does not contain replacement atoms (storeOutputAtom) - this might be a mistake - ignoring", ng)
        return
      else:
        logging.debug("identified replacementAtomSymLit %s with positive %s", replacementAtomSymLit, replacementAtomPositiveSymLit)

      # analyze the nogood and check if it exists in learned nogoods
      # if yes, just return and do not learn it
      # if no, add it and schedule to add it in the solver
      veri = self.eatomVerificationsByReplacement[replacementAtomPositiveSymLit.sym]

      # extend nogood with relevance atom
      # (only if external atom is relevant, the nogood can make the replacement true/false)
      # otherwise we get unfounded "must be true" external atom replacements, see testcase relevance_learning.hex
      if not nogood.add(veri.relevance.lit):
        logging.info("cannot add nogood (opposing relevance literal)!")
        return
      logging.info("learn() added relevance atom %s to nogood which became %s", veri.relevance, nogood)

      # find out of this external atom is positive/negative in the nogood (see __init__ / self.nogoods)
      if replacementAtomSymLit == replacementAtomPositiveSymLit:
        # positive -> indicates that the external atom must be false if all other literals match
        idx = 0
      else:
        # negative -> indicates that the external atom must be true if all other literals match
        idx = 1

      # remove replacement literal (it is encoded in the index)
      inogood = frozenset([ x for x in nogood.literals if x != replacementAtomSymLit.lit ])
      # find out if this nogood is already known
      if inogood in veri.nogoods[idx]:
        logging.info("learn() skips adding known nogood")
        return

      # add to known nogoods
      veri.nogoods[idx].add(inogood)
      logging.debug("learn() records [%d] nogood part %s - nogood is %s+[%s]", idx, inogood, ng, veri.relevance)

      # record as nogood to be added
      self.ccontext.propagator.recordNogood(nogood, defer=True)

class CachedEAtomEvaluator(EAtomEvaluator):
  counter = 0

  def __init__(self, config, claspcontext, stats):
    EAtomEvaluator.__init__(self, config, claspcontext, stats)
    # cache = defaultdict:
    # key = eatom name
    # value = defaultdict
    #   key = inputtuple
    #   value = dict:
    #     key = (predicateinputatoms-true, predicateinputatoms-false)
    #           [because in partial interpretations there are also unknown atoms]
    #     value = output
    self.cache = collections.defaultdict(lambda: collections.defaultdict(dict))

  def evaluateNoncached(self, holder, inputtuple, predicateinputatoms):
    return EAtomEvaluator.evaluate(self, holder, inputtuple, predicateinputatoms)

  def evaluateCached(self, holder, inputtuple, predicateinputatoms):
    # this is handled by defaultdict
    storage = self.cache[holder.name][inputtuple]
    positiveinputatoms = frozenset(x for x in predicateinputatoms if x.isTrue())
    negativeinputatoms = frozenset(x for x in predicateinputatoms if x.isFalse())
    key = (positiveinputatoms, negativeinputatoms)
    if key not in storage:
      storage[key] = EAtomEvaluator.evaluate(
        self, holder, inputtuple, predicateinputatoms)
    if __debug__:
      self.counter += 1
      if self.counter % 1000 == 1000:
        logging.info("cache was hit %d times", self.counter)
    return storage[key]

  def evaluate(self, holder, inputtuple, predicateinputatoms):
    # we cache for total and partial evaluations,
    # because our architecture would evaluate multiple times for multiple output tuples
    # of the same nonground external atom on the same (partial) interpretation
    # -> the cache avoids recomputations in this case
    return self.evaluateCached(holder, inputtuple, predicateinputatoms)

class GringoContext:
  class ExternalAtomCall:
    def __init__(self, eaeval, holder):
      self.eaeval = eaeval
      self.holder = holder
      self.ERR = "GringoContext.ExternalAtomCall returning at least one non-Symbol: repr=%s"
    def __call__(self, *arguments):
      logging.debug('GC.EAC(%s) called with %s',self.holder.name, repr(arguments))
      outKnownTrue, outUnknown = self.eaeval.evaluate(self.holder, arguments, [])
      assert(len(outUnknown) == 0) # no partial evaluation for eatoms in grounding
      outarity = self.holder.outnum
      gringoOut = None
      # interpret special cases for gringo @eatom rewritings:
      if outarity == 0:
        # no output arguments: 1 or 0
        if len(outKnownTrue) == 0:
          gringoOut = clingo.Number(0)
        else:
          gringoOut = clingo.Number(1)
        if not isinstance(gringoOut, clingo.Symbol):
          logging.error(self.ERR, repr(gringoOut))
      elif outarity == 1:
        # list of terms, not list of tuples (I could not convince Gringo to process single-element-tuples)
        if any([ len(x) != outarity for x in outKnownTrue ]):
          wrongarity = [ x for x in outKnownTrue if len(x) != outarity ]
          outKnownTrue = [ x for x in outKnownTrue if len(x) == outarity ]
          logging.warning("ignored tuples {} with wrong arity from atom {}".format(repr(wrongarity), self.holder.name))
        gringoOut = [ x[0] for x in outKnownTrue ]
        if not all([isinstance(x, clingo.Symbol) for x in gringoOut]):
          logging.error(self.ERR, repr(gringoOut))
      else:
        # list of tuples of terms
        gringoOut = [clingo.Tuple_(args) for args in outKnownTrue]
        if not all([isinstance(x, clingo.Symbol) for x in gringoOut]):
          logging.error(self.ERR, repr(gringoOut))
      # in other cases we can directly use what externalAtomCallHelper returned
      logging.debug('GC.EAC(%s) call returned output %s', self.holder.name, repr(gringoOut))
      return gringoOut
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
    * whether we should verify this on partial assignments (or only on total ones)
    """
    def __init__(self, relevance, replacement, verify_on_partial=False):
      # symlit for ground eatom relevance
      self.relevance = relevance
      # symlit for ground eatom replacement
      self.replacement = replacement
      # key = argument position, value = list of ClingoID
      self.predinputs = collections.defaultdict(list)
      # list of all elements in self.predinputs (cache)
      self.allinputs = []
      # whether this should be verified on partial assignments
      self.verify_on_partial = verify_on_partial
      # nogoods that are relevant for this verification:
      # (nogoods for falsity, nogoods for truth)
      # nogoods for falsity contain positive replacement literal
      # nogoods for truth contain negative replacement literal
      # these nogoods are stored _without_ the replacement literal
      # (it is implicit from the set in which the nogood is stored)
      self.nogoods = (set(), set())

  class Nogood:
    def __init__(self):
      self.literals = set()

    def add(self, lit):
      if -lit in self.literals:
        return False
      self.literals.add(lit)
      return True

    def __contains__(self, lit):
      return lit in self.literals

    def subsumes(self, other):
      # this nogood (self) subsumes another one (other) if it is more strict
      # i.e., other is no longer necessary
      # this is the case if self is a subset of other
      assert(isinstance(other, Nogood))
      return self.literals.issubset(other.literals)

  class StopPropagation(Exception):
    pass

  def __init__(self, config, name, pcontext, ccontext, eaeval, partial_evaluation_eatoms):
    self.name = 'ClingoProp('+name+'):'
    # configuration object
    self.config = config
    # key = eatom
    # value = list of EAtomVerification
    self.eatomVerifications = collections.defaultdict(list)
    # mapping from solver literals to lists of strings
    self.dbgSolv2Syms = collections.defaultdict(list)
    # mapping from symbol to solver literal
    self.dbgSym2Solv = {}
    # program context - to get external atoms and signatures to initialize EAtomVerification instances
    self.pcontext = pcontext
    # clasp context - to store the propagator for external atom verification
    self.ccontext = ccontext
    # helper for external atom evaluation - to perform external atom evaluation
    self.eaeval = eaeval
    # list of names of external atoms that should do checks on partial assignments
    self.partial_evaluation_eatoms = partial_evaluation_eatoms
    # list of nogoods to add
    self.nogoodsToAdd = []
    # verification that is currently verified using an external atom call
    # this is used to handle learned nogoods
    self.currentVerification = None

  def init(self, init):
    name = self.name+'init:'
    # register mapping for solver/grounder atoms!
    # no need for watches as long as we use only check()
    require_partial_evaluation = False
    for eatomname, signatures in self.pcontext.eatoms.items():
      logging.info("%s eatom %s has signatures %s", name, eatomname, signatures)
      found_this_eatomname = False
      verify_on_partial = eatomname in self.partial_evaluation_eatoms
      for siginfo in signatures:
        logging.debug('%s init processing eatom %s signature relpred %s reppred %s arity %d', name, eatomname, siginfo.relevancePred, siginfo.replacementPred, siginfo.arity)
        for xrep in init.symbolic_atoms.by_signature(siginfo.replacementPred, siginfo.arity):
          found_this_eatomname = True
          logging.debug('%s   replacement atom %s', name, xrep.symbol)
          replacement = SymLit(xrep.symbol, init.solver_literal(xrep.literal))
          xrel = init.symbolic_atoms[clingo.Function(name=siginfo.relevancePred, arguments = xrep.symbol.arguments)]
          logging.debug('%s   relevance atom %s', name, xrel.symbol)
          relevance = SymLit(xrel.symbol, init.solver_literal(xrel.literal))

          verification = self.EAtomVerification(relevance, replacement, verify_on_partial)

          # get symbols given to predicate inputs and register their literals
          for argpos, argtype in enumerate(dlvhex.eatoms[eatomname].inspec):
            if argtype == dlvhex.PREDICATE:
              argval = str(xrep.symbol.arguments[argpos])
              logging.debug('%s   argument %d is %s', name, argpos, argval)
              relevantSig = [ (aarity, apol) for (aname, aarity, apol) in init.symbolic_atoms.signatures if aname == argval ]
              logging.debug('%s   relevantSig %s', name, repr(relevantSig))
              for aarity, apol in relevantSig:
                for ax in init.symbolic_atoms.by_signature(argval, aarity):
                  slit = init.solver_literal(ax.literal)
                  logging.debug('%s       atom %s (neg:%s) / slit %d', name, str(ax.symbol), ax.symbol.negative, slit)
                  predinputid = ClingoID(self.ccontext, SymLit(ax.symbol, slit))
                  verification.predinputs[argpos].append(predinputid)

          verification.allinputs = frozenset(hexlite.flatten([idlist for idlist in verification.predinputs.values()]))
          self.eatomVerifications[eatomname].append(verification)
          self.eaeval.eatomVerificationsByReplacement[replacement.sym] = verification
          self.eaeval.replacementAtoms.add(replacement.sym)
      if found_this_eatomname:
        # this eatom is used at least once in the search
        if eatomname in self.partial_evaluation_eatoms:
          logging.info('%s will perform checks on partial assignments due to external atom %s', name, eatomname)
          require_partial_evaluation = True

    if require_partial_evaluation:
      init.check_mode = clingo.PropagatorCheckMode.Fixpoint
    else:
      # this is the default anyways
      init.check_mode = clingo.PropagatorCheckMode.Total

    # for debugging: get full symbol table
    if __debug__:
      for x in init.symbolic_atoms:
        slit = init.solver_literal(x.literal)
        logging.debug("PropInit symbol:{} lit:{} isfact:{} slit:{}".format(x.symbol, x.literal, x.is_fact, slit))
        prefix = 'F'
        if not x.is_fact:
          prefix = str(x.literal)
        self.dbgSolv2Syms[slit].append(prefix+'/'+str(x.symbol))
        self.dbgSym2Solv[x.symbol] = slit

    # WONTFIX (near future) implement this current type of check in on_model where we can comfortably add all nogoods immediately
    # DONE (near future) use partial checks and stay in check()
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
    name = self.name+'check:'
    logging.info('%s entering with assignment.is_total=%d', self.name, control.assignment.is_total)
    #for t in traceback.format_stack():
    #  logging.info(self.name+'   '+t)
    if __debug__:
      true = []
      false = []
      unassigned = []
      for slit, syms in self.dbgSolv2Syms.items():
        info = "{}={{{}}}".format(slit, ','.join(syms))
        if control.assignment.is_true(slit):
          true.append(info)
        elif control.assignment.is_false(slit):
          false.append(info)
        else:
          assert(control.assignment.value(slit) == None)
          unassigned.append(info)
      if len(true) > 0: logging.debug(name+" assignment has true slits "+' '.join(true))
      if len(false) > 0: logging.debug(name+" assignment has false slits "+' '.join(false))
      if len(unassigned) > 0: logging.debug(name+" assignment has unassigned slits "+' '.join(unassigned))
      logging.debug(name+"assignment is "+' '.join([ str(x[0]) for x in self.dbgSym2Solv.items() if control.assignment.is_true(x[1]) ]))
    partial_evaluation = not control.assignment.is_total
    with self.ccontext(control, self):
      try:
        # do this within ccontext and within the try/catch that logs StopPropagation
        self.addPendingNogoodsOrThrow()
        for eatomname, veriList in self.eatomVerifications.items():
          for veri in veriList:
            if partial_evaluation and not veri.verify_on_partial:
              # just skip this verification here
              continue
            if control.assignment.is_true(veri.relevance.lit):
              logging.info(name+' relevance of {} is true'.format(veri.replacement.sym))
              if self.config.consider_skipping_evaluation_if_nogood_determines_truth:
                if self.nogoodConfirmsTruthOfAtom(control, veri):
                  logging.info(name+' no need to verify atom {} (existing nogood)'.format(veri.replacement.sym))
                else:
                  # verify truth because nogood did not determine it
                  self.verifyTruthOfAtom(eatomname, control, veri)
                  # add new pending nogoods (this is a potential output of above verification) if required
                  self.addPendingNogoodsOrThrow()
              else:
                # always verify truth
                self.verifyTruthOfAtom(eatomname, control, veri)
                # add new pending nogoods (this is a potential output of above verification) if required
                self.addPendingNogoodsOrThrow()
            else:
              logging.debug(name+' no need to verify atom {} (relevance)'.format(veri.replacement.sym))
      except ClingoPropagator.StopPropagation:
        # this is part of the intended behavior
        logging.debug(name+' aborted propagation')
        #logging.debug('aborted from '+traceback.format_exc())
    logging.info(self.name+' leaving check() propagator')
  
  def nogoodConfirmsTruthOfAtom(self, control, veri):
    logging.debug("checking if %s is confirmed by previously learned nogoods", veri.replacement)
    target = 1 if control.assignment.is_true(veri.replacement.lit) else 0
    ngset = veri.nogoods[target]
    logging.debug("  previously recorded atom-specified nogoods for target %d without replacement: %s", target, ngset)
    for nogood in ngset:
      check = [ control.assignment.is_true(l) for l in nogood ]
      logging.debug("  checking nogood %s: check=%s", nogood, check)
      if all(check):
          # this nogood fires!
          logging.debug("previously learned nogood %s decides truth %s of atom!", nogood, target)
          return True
    return False

  def verifyTruthOfAtom(self, eatomname, control, veri):
    name = self.name+'vTOA:'
    targetValue = control.assignment.is_true(veri.replacement.lit)
    if __debug__:
      idebug = repr([ x.value() for x in veri.allinputs if x.isTrue() ])
      logging.info(name+' checking if {} = {} with interpretation {} ({})'.format(
        str(targetValue), veri.replacement.sym, idebug,
        {True:'total', False:'partial'}[control.assignment.is_total]))
    holder = dlvhex.eatoms[eatomname]
    # in replacement atom everything that is not output is relevant input
    replargs = veri.replacement.sym.arguments
    inputtuple = tuple(replargs[0:len(replargs)-holder.outnum])
    outputtuple = tuple(replargs[len(replargs)-holder.outnum:len(replargs)])
    logging.info(name+' inputtuple {} outputtuple {}'.format(repr(inputtuple), repr(outputtuple)))
    self.currentVerification = veri
    try:
      outKnownTrue, outUnknown = self.eaeval.evaluate(holder, inputtuple, veri.allinputs)
    finally:
      self.currentVerification = None
    logging.debug(name+" outputtuple {} outTrue {} outUnknown {} targetValue of {} = {}".format(repr(outputtuple), repr(outKnownTrue), repr(outUnknown), str(veri.replacement.sym), targetValue))

    if outputtuple in outUnknown:
      # cannot verify
      logging.info("%s external atom gave tuple %s as unknown -> cannot verify", name, outputtuple)
      return

    # TODO handle all outputs in outputtuple, not only the one that is relevant to the next line
    realValue = outputtuple in outKnownTrue

    if realValue == targetValue:
      logging.info("%s verified %s = &%s[%s](%s)", name, targetValue, eatomname, inputtuple, outputtuple)
      return
    else:
      # this just means the guess was wrong, this "failure to verify" is not an error!
      logging.info("%s failed %s = &%s[%s](%s)", name, targetValue, eatomname, inputtuple, outputtuple)

    # add clause that ensures this value is always chosen correctly in the future
    # clause contains veri.relevance.lit, veri.replacement.lit and negation of all atoms in

    if not holder.props.doInputOutputLearning:
      # this breaks the search if the external atom does not provide at least one nogood that declares this answer set invalid!
      logging.info("%s not performing input/output learning due to configuration", name)
      return

    # build naive input/output nogood
    # this invalidates the current answer set candidate
    
    nogood = self.Nogood()
    hr_nogood = []
    # solution is eliminated if all inputs are as they were above ...
    for atom in veri.allinputs:
      value = control.assignment.value(atom.symlit.lit)
      if value == True:
        hr_nogood.append( (atom.symlit.sym,True) )
        if not nogood.add(atom.symlit.lit):
          logging.warning(name+" cannot build nogood (opposite literals)!")
          return
      elif value == False:
        hr_nogood.append( (atom.symlit.sym,False) )
        if not nogood.add(-atom.symlit.lit):
          logging.warning(name+" cannot build nogood (opposite literals)!")
          return
      # None case does not contribute to nogood

    # ... if the atom was relevant ...
    if not nogood.add(veri.relevance.lit):
      logging.warning("cannot add relevance to  i/o nogood (opposing literal)!")
      return

    # important: check this _before_ adding replacement literal
    if self._inputOutputNogoodSubsumedByLearnedNogood(veri.nogoods, realValue, nogood):
      logging.info(self.name+"CPvTOA omitting nogood (subsumed)!")
      return

    checklit = None
    if realValue == True:
      # ... and if computation gave true but eatom replacement is false
      checklit = -veri.replacement.lit
      hr_nogood.append( (veri.replacement.sym,False) )
    else:
      # ... and if computation gave false but eatom replacement is true
      checklit = veri.replacement.lit
      hr_nogood.append( (veri.replacement.sym,True) )

    if not nogood.add(checklit):
      logging.warning(self.name+"CPvTOA cannot build nogood (opposite literals)!")
      return

    if logging.getLogger().isEnabledFor(logging.INFO):
      hr_nogood_str = repr([ {True:'',False:'-'}[sign]+str(x) for x, sign in hr_nogood ])
      logging.info("%s CPcheck adding input/output nogood %s", name, hr_nogood_str)
    # defer=False to make sure that we abort investigating this answer set candidate as soon as possible
    # and do not waste computing external atoms on a candidate that is for sure not an answer set
    # lock=False to permit the solver to delete the nogood later (these nogoods only serve to invalidate the current result)
    self.recordNogood(nogood, defer=False, lock=False)

  def _inputOutputNogoodSubsumedByLearnedNogood(self, veri_nogoods, realValue, nogood):
    # veri_nogoods -> see EAtomVerification.__init__ comments
    if realValue == True:
      vngds = veri_nogoods[1]
    else:
      vngds = veri_nogoods[0]

    # vngds does not contain replacement literal
    # nogood _also_ does not contain a replacement literal at this point
    # (where this method is called)

    for vng in vngds:
      # vng is a frozenset of integers (solver literals)
      # nogood is a Nogood -> nogood.literals is a set of integers (solver literals)
      if vng.issubset(nogood.literals):
        logging.info("learned nogood %s subsumes nogood %s", list(vng), nogood)
        return True

    return False

  def recordNogood(self, nogood, defer=False, lock=True):
    nogood = list(nogood.literals)
    if __debug__:
      name = self.name+'recordNogood:'
      logging.debug(name+" adding {}".format(repr(nogood)))
      for slit in nogood:
        a = abs(slit)
        logging.debug(name+"  {} ({}) is {}".format(a, self.ccontext.propcontrol.assignment.value(a), repr(self.dbgSolv2Syms[a])))
    if defer:
      # do not add nogood here, but record in list so that propagator can later add them
      self.nogoodsToAdd.append(nogood)
    else:
      # add (potentially raises StopPropagation)
      self.addNogood(nogood, lock)

  def addPendingNogoodsOrThrow(self):
    '''
    add nogoods to the solver that were recorded in an external atom call and propagate
    if nogood requires end of propagation, throw StopPropagation
    '''
    logging.debug("addPendingNogoodsOrThrow has %d nogoods to add", len(self.nogoodsToAdd))
    while len(self.nogoodsToAdd) > 0:
      # get next nogood from queue
      ng = self.nogoodsToAdd.pop(0)
      self.addNogood(ng)

  def addNogood(self, nogood, lock=True):
    # low-level add of nogood and abort of propagation if required
    may_continue = self.ccontext.propcontrol.add_nogood(nogood, tag=False, lock=lock)
    if may_continue:
      may_continue = self.ccontext.propcontrol.propagate()
    if __debug__:
      name = self.name+'addNogood:'
      logging.debug(name+" {}, may_continue={}".format(repr(nogood), repr(may_continue)))
    if may_continue == False:
      raise ClingoPropagator.StopPropagation()


class ClingoModel(dlvhex.Model):
  '''
  This class wraps a clingo model and provides the shown atoms to dlvhex for display.
  This is not used to perform external evaluations (those must be done also on non-shown atoms).
  '''
  def __init__(self, ccontext, mdl):
    def idmaker(x):
      if x in mdl.context.symbolic_atoms:
        # real variables in the solver
        return ClingoID(ccontext, SymLit(x, mdl.context.symbolic_atoms[x].literal))
      else:
        # symbols from #show statements
        return ClingoID(ccontext, SymLit(x, None))
    idlist = [ idmaker(x) for x in mdl.symbols(shown=True) ]
    dlvhex.Model.__init__(self,
      atoms=frozenset(idlist),
      cost=mdl.cost,
      is_optimal=True if mdl.optimality_proven or len(mdl.cost) == 0 else False)

def execute(pcontext, rewritten, facts, plugins, config, model_callbacks):
  propagatorFactory = None
  flpchecker = None
  cmdlineargs = None
  with pcontext.stats.context('preparation'):
    # prepare contexts that are for this program but not yet specific for a clasp solver process
    # (multiple clasp solvers are used for finding compatible sets and for checking FLP property)

    # preparing clasp context which does not hold concrete clasp information yet
    # (such information is added during propagation)
    ccontext = ClaspContext()

    # preparing evaluator for external atoms which needs to know the clasp context
    if config.enable_generic_eatom_cache:
      eaeval = CachedEAtomEvaluator(config, ccontext, pcontext.stats)
    else:
      eaeval = EAtomEvaluator(config, ccontext, pcontext.stats)

    # find names of external atoms that advertises to do checks on a partial assignment
    partial_evaluation_eatoms = [ eatomname for eatomname, info in dlvhex.eatoms.items() if info.props.provides_partial ]
    # XXX we could filter here to reduce this set or we could decide to do no partial evaluation at all or we could do this differently for FLP checker and Compatible Set finder
    should_do_partial_evaluation_on = partial_evaluation_eatoms

    propagatorFactory = lambda name: ClingoPropagator(config, name, pcontext, ccontext, eaeval, should_do_partial_evaluation_on)

    if config.flpcheck == 'explicit':
      flp_checker_factory = flp.ExplicitFLPChecker
    else:
      assert(config.flpcheck == 'none')
      flp_checker_factory = flp.DummyFLPChecker
    flpchecker = flp_checker_factory(config, propagatorFactory)

    # TODO get settings from commandline
    cmdlineargs = []
    if config.number != 1:
      cmdlineargs.append(str(config.number))
    # just in case we need optimization
    cmdlineargs.append('--opt-mode=optN')
    for a in hexlite.flatten(config.backend_additional_args):
      cmdlineargs.append(a)

  cc = None
  with pcontext.stats.context('grounding'):
    logging.info('sending nonground program to clingo control '+repr(cmdlineargs))
    cc = clingo.Control(cmdlineargs)
    sendprog = '\n'.join([ shp.shallowprint(x) for x in rewritten ])
    try:
      logging.debug('sending program ===\n'+sendprog+'\n===')
      cc.add('base', (), sendprog)
    except:
      raise Exception("error sending program ===\n"+sendprog+"\n=== to clingo:\n"+traceback.format_exc())

    # preparing context for instantiation
    # (this class is specific to the gringo API)
    logging.info('grounding with gringo context')
    ccc = GringoContext(eaeval)
    flpchecker.attach(cc)

    if config.dump_grounding:
      cc.register_observer(GroundProgramPrinter(), False)

    cc.ground([('base',())], ccc)

  with pcontext.stats.context('search'):
    logging.info('preparing for search')

    # name of this propagator CSF = compatible set finder
    checkprop = propagatorFactory('CSF')
    cc.register_propagator(checkprop)

    logging.info('starting search')
    ret = None
    with cc.solve(yield_=True, async_=False) as handle:
      for model in handle:
        flpmodel = False
        with pcontext.stats.context("flpcheck"):
          flpmodel = flpchecker.checkModel(model)
        if not flpmodel:
          logging.debug('discarding model because flpchecker returned False')
          # according to clingo documentation "discards current model"
          handle.resume()
        else:
          try:
            clingo_model = ClingoModel(ccontext, model)
            suffix = 'opt' if clingo_model.is_optimal else 'nonopt'
            # first display stats (if the callback ends the search we still want to have the stats of that answer set!)
            pcontext.stats.display('answerset'+suffix)
            # then call the callbacks
            for cb in model_callbacks:
              cb(clingo_model)
          except modelcallback.StopModelEnumerationException:
            handle.cancel()
            ret = 'SAT'
            logging.info("end of enumeration with StopModelEnumerationException")
      if not ret:
        res = handle.get()
        if res.unsatisfiable:
          ret = 'UNSAT'
        if res.interrupted or res.unknown:
          raise InterruptedError("clingo solve interrupted or unknown")

  if config.stats:
    sys.stderr.write(json.dumps({'event':'stats', 'name':'clingo', 'c': cc.statistics })+'\n')

  logging.info('execute() terminated with result '+repr(ret))
  return ret

