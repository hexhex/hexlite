# encoding: utf8
# This module provides functionality for finding out if a compatible set is or is not an answer set.
#
# We effectively make use of Proposition 2 from the following paper:
# Eiter, T., Fink, M., Krennwallner, T., Redl, C., & Schüller, P. (2014).
# Efficient HEX-Program Evaluation Based on Unfounded Sets.
# Journal of Artificial Intelligence Research, 49, 269–321.

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

# assume that the main program has handled possible import problems
import clingo

from .aux import Aux

# head begin/separator/end sign for key=choice=True (choice rule) or False (disjunction)
HBEG = { True: '{', False: '' }
HSEP = { True: ' ; ', False: ' | ' }
HEND = { True: '}', False: '' }

class GroundProgramObserver:
  class WarnMissing:
    def __init__(self, name):
      self.name = name
    def __call__(self, *arguments):
      logging.debug("GPOWarning {} {}".format(self.name, repr(arguments)))

  def __init__(self):
    # a program is a set of rules, we assume gringo/clasp are clever enough to eliminate duplicates
    self.atom2int = {}
    self.int2atom = {}
    # eatom truth replacement atoms (cache)
    self.replatoms = set()
    # facts
    self.facts = set()
    # received rules (will be erased at end_step! use only eareplrules and rules!)
    self.preliminaryrules = []
    # rules for eatom replacement guessing
    self.eareplrules = []
    # all other rules
    self.rules = []
    # TODO: weight rules
    self.maxAtom = 1
    self.waitingForStuff = True
    logging.debug("GP.__init__")

  def init_program(self, incr):
    logging.debug("GPInit")
    pass
  def begin_step(self):
    logging.debug("GPBeginStep")
    self.waitingForStuff = True
  def end_step(self):
    logging.debug("GPEndStep")
    # here we got rules and atoms so only here we can separate rules from eareplrules
    self.extractEAtomReplacementGuesses()
    self.waitingForStuff = False
    self.printall()
  def __getattr__(self, name):
    logging.debug("GPWARN"+name)
    return self.WarnMissing(name)
  def rule(self, choice, head, body):
    logging.debug("GPRule ch=%s hd=%s b=%s", repr(choice), repr(head), repr(body))
    if choice == False and len(head) == 1 and len(body) == 0:
      # ignore rules for facts,
      # because we get facts separately in output_atom, and
      # because they are eliminated from bodies anyways
      pass
    else:
      self.preliminaryrules.append( (choice, head, body) )
  def weight_rule(self, choice, head, lower_bound, body):
    logging.debug("GPWeightRule ch=%s hd=%s lb=%s, b=%s", repr(choice), repr(head), repr(lower_bound), repr(body))
    raise Exception("weight_rule [aggregates] not yet implemented in FLP checker")
  def output_atom(self, symbol, atom):
    logging.debug("GPAtom symb=%s atm=%s", repr(symbol), repr(atom))
    if atom == 0L:
      self.facts.add(symbol)
      assert(not symbol.name.startswith(Aux.EAREPL))
    else:
      self.atom2int[symbol] = atom
      self.int2atom[atom] = symbol
      self.maxAtom = max(self.maxAtom, atom)
      if symbol.name.startswith(Aux.EAREPL):
        self.replatoms.add(atom)

  def extractEAtomReplacementGuesses(self):
    for choice, head, body in self.preliminaryrules:
      if choice and len(head) == 2 and head[0] in self.replatoms:
        assert(head[1] in self.replatoms)
        self.eareplrules.append( (choice, head, body) )
      else:
        assert(len(head) != 2 or (head[0] not in self.replatoms and head[1] not in self.replatoms))
        self.rules.append( (choice, head, body) )
    # after that we should not use this anymore
    # XXX solve this in a more elegant way, without ever storing in self
    del(self.preliminaryrules)

  def formatAtom(self, atom):
    # XXX if atom is x we segfault (we cannot catch an exception here!)
    if atom > 0L:
      return str(self.int2atom[atom])
    else:
      return 'not '+str(self.int2atom[-atom])

  def formatBody(self, body):
    return ','.join([self.formatAtom(x) for x in body])

  def formatRule(self, rule):
    choice, head, body = rule
    headstr = HBEG[choice] + HSEP[choice].join([self.formatAtom(x) for x in head]) + HEND[choice]
    if len(body) == 0:
      return headstr+'.'
    else:
      bodystr = self.formatBody(body)
      return headstr+':-'+bodystr+'.'

  # TODO formatWeightRule

  def printall(self):
    if __debug__:
      logging.debug("facts:")
      logging.debug('  '+', '.join([ str(f) for f in self.facts]))
      logging.debug("eareplrules:")
      for r in self.eareplrules:
        logging.debug('  '+self.formatRule(r))
      logging.debug("rules:")
      for r in self.rules:
        logging.debug('  '+self.formatRule(r))
      # TODO weight rules

  def finished(self):
    # true if at least one program was fully received
    return not self.waitingForStuff

class RuleActivityProgram:
  '''
  This program is a transformed version of the ground program Pi with HEX replacement atoms.

  It contains:
  (I) a guess for each atom in Pi (non-fact rules are stored in self.po.eareplrules and self.po.rules)
  (II) for each non-fact rule in Pi a rule with a unique head <Aux.RHPRED>(ruleidx) and the body of the original rule.

  The purpose of this program is to find out which rule bodies are satisfied (i.e., which rules are in the FLP reduct) in a given answer set.

  This is determined using solver assumptions which fully determine the guesses (I).
  '''
  def __init__(self, programObserver):
    self.po = programObserver
    self.cc = clingo.Control()
    prog = self._build()
    with self.cc.builder() as b:
      for rule in prog:
        logging.debug('RAP rule: '+repr(rule))
        # TODO ask Benjamin/benchmark if it is faster to parse one by one or all in one string
        clingo.parse_program(rule, lambda ast: b.add(ast))
    self.cc.ground([("base", [])])

  def _assumptionFromModel(self, mdl):
    syms = mdl.symbols(atoms=True, terms=True)
    return [ (atm, mdl.contains(atm)) for atm in self.po.atom2int ]

  def _build(self):
    def headActivityRule(idx, chb):
      choice, head, body = chb
      # we only use the body!
      if len(body) == 0:
        return '{}({}).'.format(Aux.RHPRED, idx)
      else:
        sbody = self.po.formatBody(body)
        return '{}({}) :- {}.'.format(Aux.RHPRED, idx, sbody)
    def atomGuessRule(atom):
      return  '{'+str(atom)+'}.'
      
    assert(self.po.finished())

    # (I) guess for each atom
    raguesses = [ atomGuessRule(atom) for atom in self.po.atom2int.keys() ]
    # (II) rules with special auxiliary heads
    rarules = [ headActivityRule(idx, chb) for idx, chb in enumerate(self.po.eareplrules + self.po.rules) ]
    # we are interested in which rule is active
    rashow = ['#show {}/1.'.format(Aux.RHPRED)]
    return rarules + raguesses + rashow

  def getActiveRulesForModel(self, mdl):
    class OnModel:
      def __init__(self):
        self.activeRules = None
      def __call__(self, activeRulesMdl):
        #logging.debug('activeRulesMdl = '+str(activeRulesMdl)) 
        shownTrueAtoms = activeRulesMdl.symbols(shown=True)
        self.activeRules = [ atm.arguments[0].number for atm in shownTrueAtoms ]
        assert(all([isinstance(r, (int, long)) for r in self.activeRules]))

    assumptions = self._assumptionFromModel(mdl)
    #logging.debug("solving with assumption"+repr(assumptions))
    modelcb = OnModel()
    res = self.cc.solve(on_model=modelcb, assumptions=assumptions)
    assert(res.satisfiable)
    assert(modelcb.activeRules is not None)
    return modelcb.activeRules

class CheckOptimizedProgram:
  '''
  This program is a transformed version of the ground program Pi with HEX replacement atoms.

  It contains:
  (I) a guess for <Aux.RHPRED>(ruleidx) for each non-fact rule in Pi (will be determined by an assumption)
      (non-fact rules are stored in self.eareplrules and self.po.rules)
  (II) a constraint :- <Aux.RHPRED>(ruleidx), {not <HEADATOMS>}, <POSBODYATOMS>. for each rule in Pi
      (except guessing rules for external atom replacements)
      [this seems to be merely an optimization].
  (III) for each atom in Pi (stored in self.po.int2atom/atom2int) a guess.
  (IV) for each atom A in Pi a guess for <Aux.CATOMTRUE>_A (will be determined by an assumption)
  (V) for each atom A in Pi that is not an external atom replacement, the rules
      % A cannot become true if it was not true in the compatible set
      :- A, not <Aux.CATOMTRUE>_A.
      % A is guessed to be true if it was true in the compatible set
      {A} :- <Aux.CATOMTRUE>_A.
      % model is smaller than compatible set if an atom is not true that is true in the compatible set
      smaller :- not A, <Aux.CATOMTRUE>_A.
  (VI) the rule
      :- not smaller
  (VII) all facts from the original ground program (stored in self.po.facts)

  The purpose of this program is to check if the FLP reduct has a model that is smaller than the original compatible set.

  This is determined using solver assumptions which fully determine the guesses (I) to determine the reduct and the guess (IV) to determine the compatible set.

  For this program we also need to check if external atom semantics are correctly captured by the guesses,
  so we include the propagator from the main solver in the search.
  (Input/output cache can be reused so we use the same instance as in the main search.)
  '''
  def __init__(self, programObserver, propagatorFactory):
    self.po = programObserver
    # name of this propagator = FLP checker
    self.eatomPropagator = propagatorFactory('FLP')
    # build program
    self.cc = clingo.Control()
    prog = self._build()
    with self.cc.builder() as b:
      for rule in prog:
        logging.debug('COP rule: '+repr(rule))
        # TODO ask Benjamin/benchmark if it is faster to parse one by one or all in one string
        clingo.parse_program(rule, lambda ast: b.add(ast))
    self.cc.ground([("base", [])])
    # register propagator for upcoming solve calls
    self.cc.register_propagator(self.eatomPropagator)

  def _build(self):
    def headActivityRule(idx, chb, int2atom):
      choice, head, body = chb
      # we only use the body!
      if len(body) == 0:
        return '{}({}).'.format(Aux.RHPRED, idx)
      else:
        sbody = self.po.formatBody(body)
        return '{}({}) :- {}.'.format(Aux.RHPRED, idx, sbody)
    def rhGuessRule(ruleidx):
      return  '{'+Aux.RHPRED+'('+str(ruleidx)+')}.'
    def ruleToReductConstraint(ruleidx, rule):
      activator = '{}({})'.format(Aux.RHPRED, ruleidx)
      choice, head, body = rule
      bodies = [activator]
      bodies += [ self.po.formatAtom(-h) for h in head ]
      bodies += [ self.po.formatAtom(b) for b in body ]
      return ':-'+','.join(bodies)+'.'

    def atomGuessRule(atom):
      return  '{'+str(atom)+'}.'
      
    assert(self.po.finished())

    # (I) guess which rules are marked as active (will be determined with assumption)
    rhguess = [ rhGuessRule(idx) for idx in range(0, len(self.po.rules)) ]
    # (II) check model of reduct (not for choice rules, because they are always satisfied)
    reductconstr = [
      ruleToReductConstraint(idx, rule)
      for idx, rule in enumerate(self.po.rules)
      if rule[0] != True ]
    # (III) guess each atom in Pi
    atomguess = [ atomGuessRule(atom) for atom in self.po.atom2int ]
    # this is A(Pi) in the paper
    nonreplatoms = [ str(atom) for idx, atom in self.po.int2atom.items() if idx not in self.po.replatoms ]
    # (IV) guess <Aux.CATOMTRUE>_A for each atom except eareplacements (will be determined by an assumption)
    csatomguess = [ atomGuessRule(Aux.CATOMTRUE+"_"+at) for at in nonreplatoms ]
    # (V) ensure model is equal or smaller except eareplacements
    # A cannot become true if it was not true in the compatible set
    ensure = [ ':-'+at+',not '+Aux.CATOMTRUE+"_"+at+"." for at in nonreplatoms ]
    # A is guessed to be true if it was true in the compatible set
    ensure += [ '{'+at+'}:-'+Aux.CATOMTRUE+"_"+at+"." for at in nonreplatoms ]
    # model is smaller than compatible set if an atom is not true that is true in the compatible set
    ensure +=[ 'smaller:-not '+at+','+Aux.CATOMTRUE+'_'+at+"." for at in nonreplatoms ]
    nsmaller = [':- not smaller.']
    # (VI) facts (external atom semantics depends also on these facts)
    facts = [ str(f)+'.' for f in self.po.facts ]

    # XXX maybe show violating model as debug info?
    return rhguess + reductconstr + atomguess + csatomguess + ensure + nsmaller + facts

  def _assumptionFromActiveRules(self, activeRules):
    return [
      (clingo.Function(Aux.RHPRED, [clingo.Number(ruleidx)]),
        ruleidx in activeRules)
      for ruleidx in range(0, len(self.po.rules)) ]

  def _assumptionFromModel(self, mdl):
    syms = mdl.symbols(atoms=True, terms=True)
    return [
      (clingo.parse_term(Aux.CATOMTRUE+'_'+str(atm)), mdl.contains(atm))
      for atm, iatm in self.po.atom2int.items()
      if iatm not in self.po.replatoms ]

  def checkFLPViolation(self, activeRules, mdl):
    class OnModel:
      def __call__(self, mdl):
        logging.debug('flpModel = '+str(mdl)) 

    assumptions = self._assumptionFromActiveRules(activeRules) + self._assumptionFromModel(mdl)
    modelcb = OnModel()
    #logging.debug("assumptions:"+repr(assumptions))
    res = self.cc.solve(on_model=modelcb, assumptions=assumptions)
    logging.debug("res=%s", res)
    # if it is unsatisfiable, it has passed the test, i.e., it is an answer set
    return res.unsatisfiable

class FLPCheckerBase:
  def __init__(self, pcontext, ccontext, eaeval):
    pass
  def attach(self, clingocontrol):
    pass
  def checkModel(self, mdl):
    return True

class DummyFLPChecker(FLPCheckerBase):
  """
  FLP checker that will accept all answer sets
  """
  pass

class ExplicitFLPChecker(FLPCheckerBase):
  def __init__(self, propagatorFactory):
    logging.debug("initializing explicit FLP checker")
    self.__propfactory = propagatorFactory
    # we cannot initialize this in an eager way,
    # because we cannot force clingo to finish instantiation without running solve()
    self.__ruleActivityProgram = None
    # we cannot initialize this in an eager way,
    # because we cannot force clingo to finish instantiation without running solve()
    self.__checkProgram = None
    self.__programObserver = None

  def attach(self, clingocontrol):
    self.__programObserver = GroundProgramObserver()
    clingocontrol.register_observer(self.__programObserver)

  def checkModel(self, mdl):
    # returns True if mdl passes the FLP check (= is an answer set)
    logging.debug("FLP check for "+repr(mdl))
    ruleActivityProgram = self.ruleActivityProgram()
    activeRules = ruleActivityProgram.getActiveRulesForModel(mdl)
    logging.info("Rules in reduct:")
    for ridx in activeRules:
      r = self.__programObserver.rules[ridx]
      logging.info("  R rule: "+repr(self.__programObserver.formatRule(r)))
    checkProgram = self.checkProgram()
    is_answer_set = checkProgram.checkFLPViolation(activeRules, mdl)
    logging.debug("FLP check for {} returned {}".format(repr(mdl), repr(is_answer_set)))
    return is_answer_set

  def ruleActivityProgram(self):
    # on first call, creates control object and fills with program
    # otherwise reuses old one control object with new assumptions
    if not self.__ruleActivityProgram:
      self.__ruleActivityProgram = RuleActivityProgram(self.__programObserver)
    return self.__ruleActivityProgram

  def checkProgram(self):
    # on first call, creates control object and fills with program
    # otherwise reuses old one control object with new assumptions
    if not self.__checkProgram:
      self.__checkProgram = CheckOptimizedProgram(self.__programObserver, self.__propfactory)
    return self.__checkProgram
