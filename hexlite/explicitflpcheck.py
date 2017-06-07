# encoding: utf8
# This module provides functionality for finding out if a compatible set is or is not an answer set.

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
import sys

# assume that the main program has handled possible import problems
import clingo

from .aux import Aux

# head begin/separator/end sign for key=choice=True (choice rule) or False (disjunction)
HBEG = { True: '{', False: '' }
HSEP = { True: ' ; ', False: ' | ' }
HEND = { True: '}', False: '' }

# make it python2 and python3 compatible
if sys.version_info > (3,):
  # python3 has no long, everything is long
  long = int

def formatAssumptions(assumptions):
  return "{} not({})".format(
    repr([a for (a,t) in assumptions if t == True]),
    repr([a for (a,t) in assumptions if t == False]))

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
    # clasp auxiliary atoms
    self.auxatoms = set()
    # eatom truth replacement atoms (cache)
    self.replatoms = set()
    # facts
    self.facts = set()
    # received rules (will be erased at end_step! use only eareplrules and rules!)
    self.preliminaryrules = []
    # rules for eatom replacement guessing
    self.eareplrules = []
    # all other rules (index starts in self.rules and continues in self.weightrules)
    self.rules = []
    self.weightrules = []
    # helpers
    self.maxAtom = 1
    self.waitingForStuff = True

  def init_program(self, incr):
    logging.debug("GPInit")
    pass
  def begin_step(self):
    logging.debug("GPBeginStep")
    self.waitingForStuff = True
  def end_step(self):
    logging.debug("GPEndStep")
    # here we got rules and atoms so only here we can
    # * separate symbol atoms from auxiliary (and maybe projected/hidden) atoms
    self.extractAuxAtoms()
    # * separate rules from eareplrules
    self.extractEAtomReplacementGuesses()
    self.waitingForStuff = False
    self.printall()
  def __getattr__(self, name):
    return self.WarnMissing(name)
  def rule(self, choice, head, body):
    logging.debug("GPRule ch=%s hd=%s b=%s", repr(choice), repr(head), repr(body))
    # it seems we cannot ignore "deterministic" rules
    # sometimes they are necessary, and they concern atoms that have no symbol
    # (for an example, see tests/choicerule4.hex)
    self.preliminaryrules.append( (choice, head, body) )
  def weight_rule(self, choice, head, lower_bound, body):
    logging.debug("GPWeightRule ch=%s hd=%s lb=%s, b=%s", repr(choice), repr(head), repr(lower_bound), repr(body))
    self.weightrules.append( (choice, head, lower_bound, body) )
  def output_atom(self, symbol, atom):
    logging.debug("GPAtom symb=%s atm=%s", repr(symbol), repr(atom))
    if atom == long(0):
      # this is not a literal but a signal that symbol is always true (i.e., a fact)
      self.facts.add(symbol)
      assert(not symbol.name.startswith(Aux.EAREPL))
    else:
      self.atom2int[symbol] = atom
      self.int2atom[atom] = symbol
      self.maxAtom = max(self.maxAtom, atom)
      if symbol.name.startswith(Aux.EAREPL):
        self.replatoms.add(atom)

  def extractAuxAtoms(self):
    def extractAuxFromLits(lits):
      for lit in lits:
        alit = abs(lit)
        if alit not in self.int2atom:
          self.auxatoms.add(alit)
    for choice, head, body in self.preliminaryrules:
      extractAuxFromLits(head+body)
    for choice, head, lower_bound, body in self.weightrules:
      extractAuxFromLits(head+[at for (at,w) in body])

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
    absatom = abs(atom)
    if absatom in self.int2atom:
      stratom = str(self.int2atom[absatom])
    else:
      stratom = 'claspaux'+str(absatom)
    assert(atom != long(0))
    if atom > long(0):
      # positive literal
      return stratom
    else:
      # negative literal
      return 'not '+stratom

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

  def formatWeightBody(self, lower_bound, body):
    def formatElement(e):
      atom, weight = e
      a = self.formatAtom(atom)
      if atom < 0:
        aa = self.formatAtom(abs(atom))
        return "{w},n{aa}:{a}".format(a=a, aa=aa, w=weight)
      else:
        return "{w},{a}:{a}".format(a=a, w=weight)
    assert(len(body) > 0)
    return str(lower_bound)+'<=#sum{'+ ';'.join([formatElement(e) for e in body]) + '}'

  def formatWeightRule(self, weightrule):
    choice, head, lower_bound, body = weightrule
    headstr = HBEG[choice] + HSEP[choice].join([self.formatAtom(x) for x in head]) + HEND[choice]
    assert(len(body) > 0)
    return headstr + ':-' + self.formatWeightBody(lower_bound, body) + '.'

  def formatAnyRule(self, anyrule):
    if len(anyrule) == 3:
      return self.formatRule(anyrule)
    else:
      return self.formatWeightRule(anyrule)

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
      logging.debug("weight rules:")
      for r in self.weightrules:
        logging.debug('  '+self.formatWeightRule(r))

  def finished(self):
    # true if at least one program was fully received
    return not self.waitingForStuff

  def rule_by_index(self, idx):
    lsr = len(self.rules)
    if idx < lsr:
      return self.rules[idx]
    else:
      return self.weightrules[idx-lsr]

class RuleActivityProgram:
  '''
  This program is a transformed version of the ground program Pi with HEX replacement atoms.

  It contains:
  (I) a guess for each atom in Pi (non-fact rules are stored in self.po.eareplrules and self.po.rules)
      (auxiliary atoms in self.po.auxatoms)
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
    logging.debug("RAP grounding starts")
    self.cc.ground([("base", [])])
    logging.debug("RAP grounding finished")

  def _assumptionFromModel(self, mdl):
    syms = mdl.symbols(atoms=True, terms=True)
    ret = [ (atm, mdl.contains(atm)) for atm in self.po.atom2int ]
    ret += [ (clingo.Function(self.po.formatAtom(auxatm)), mdl.is_true(auxatm))
             for auxatm in self.po.auxatoms ]
    return ret

  def _build(self):
    def headActivityRule(idx, rule):
      # TODO it is ugly to do it like this but if we iterate separately then we need to make special index treatment
      activityatom = '{}({})'.format(Aux.RHPRED, idx)
      if len(rule) == 3:
        choice, head, body = rule
        # we only use the body!
        if len(body) == 0:
          return activityatom + '.'
        else:
          sbody = self.po.formatBody(body)
      else:
        choice, head, lbub, body = rule
        assert(len(body) > 0)
        sbody = self.po.formatWeightBody(lbub, body)
      return activityatom+':-'+sbody+'.'
    def atomGuessRule(atom):
      return  '{'+str(atom)+'}.'
      
    assert(self.po.finished())

    # (I) guess for each atom
    raguesses = [ atomGuessRule(atom) for atom in self.po.atom2int.keys() ]
    raguesses += [ atomGuessRule(self.po.formatAtom(auxatom)) for auxatom in self.po.auxatoms ]
    # (II) rules with special auxiliary heads
    rarules = [ headActivityRule(idx, rule) for idx, rule in
                enumerate(self.po.eareplrules + self.po.rules + self.po.weightrules) ]
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
    if __debug__:
      logging.debug("solving RAP with assumptions "+formatAssumptions(assumptions))
    modelcb = OnModel()
    res = self.cc.solve(on_model=modelcb, assumptions=assumptions)
    assert(res.satisfiable)
    assert(modelcb.activeRules is not None)
    return modelcb.activeRules

class CheckOptimizedProgram:
  '''
  This program is a transformed version of the ground program Pi with HEX replacement atoms.

  It is an adaptation of Proposition 2 from the following paper:
  Eiter, T., Fink, M., Krennwallner, T., Redl, C., & Schüller, P. (2014).
  Efficient HEX-Program Evaluation Based on Unfounded Sets.
  Journal of Artificial Intelligence Research, 49, 269–321.

  (The adaptation is about choice rules.)

  Let _atoms be all atoms with ID != 0 observed in GroundProgramObserver
    (some of these are clasp auxiliaries).
  Let _replatoms be atoms used in choice heads of external replacement guesses.
  Let _auxatoms be auxiliary atoms observed in GroundProgramObserver.
  Let _facts be facts observed in GroundProgramObserver.
  Let _rules and _weightrules be observed sequences of rules and weight rules.
  Given a set X of rules or weight rules,
    let CH(X) be the set of choice rules in X, and
    let noCH(X) be the set of non-choice rules in X.
  Let _chatoms = atoms in heads of rules CH(_rules+_weightrules) - _replatoms.
    (Atoms in heads of choice rules, except external atom guess rules.)
  Let _nchatoms = { <Aux_CHOICENEG>a | a \in _chatoms }.
    (Negations of atoms in _chatoms.)
  Let _minchatoms = _atoms - _replatoms + _nchatoms.
    (These atoms will be checked for minimality.)

  The check program contains:
  (I) a guess { <Aux.RHPRED>(ruleidx) }. for each index of a rule/weightrule
      (these truths will be fully determined by a solver assumption)
  (II) a guess { <Aux.CATOMTRUE>_A }. for each atom A in _minchatoms
      (will be determined by an assumption)
  (III) a guess { A }. for each atom A in _minchatoms in Pi (stored in self.po.int2atom/atom2int and self.po.auxatoms) a guess '{a}.'

  (IIa) a constraint :- <Aux.RHPRED>(ruleidx), {not <HEADATOMS>}, <POSBODYATOMS>. for each non-choice rule in Pi
  (IIb) a constraint :- <Aux.RHPRED>(ruleidx), not a, not <Aux.CHOICENEG>a, <POSBODYATOMS>.
      for each head atom a in each choice rule in Pi.
  (IIIb) for each atom a in the head of a choice rule in Pi a guess '{<Aux.CHOICENEG>a}.'

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

  (VIII) for all head atoms a_i in all ground choice rules { a1, .. am } :- body:
    a disjunctive guess 'a_i | auxneg_a_i :- body.'

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
    logging.debug("COP grounding starts")
    self.cc.ground([("base", [])])
    logging.debug("COP grounding finished")
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
      if len(rule) == 3:
        # normal rule
        choice, head, body = rule
        bodies = [activator]
        bodies += [ self.po.formatAtom(-h) for h in head ]
        bodies += [ self.po.formatAtom(b) for b in body ]
        return ':-'+','.join(bodies)+'.'
      else:
        # weight rule
        choice, head, lbub, body = rule
        bodies = [activator]
        bodies += [ self.po.formatAtom(-h) for h in head ]
        bodies += [ self.po.formatWeightBody(lbub, body) ]
        return ':-'+','.join(bodies)+'.'

    def atomGuessRule(atom):
      return  '{'+str(atom)+'}.'
      
    assert(self.po.finished())

    # (I) guess which rules are marked as active (will be determined with assumption)
    rhguess = [ rhGuessRule(idx) for idx in range(0, len(self.po.rules+self.po.weightrules)) ]
    # (II) check model of reduct (not for choice rules, because they are always satisfied)
    reductconstr = [
      ruleToReductConstraint(idx, rule)
      for idx, rule in enumerate(self.po.rules+self.po.weightrules)
      if rule[0] != True ]
    # (III) guess each atom in Pi
    atomguess = [ atomGuessRule(atom) for atom in self.po.atom2int ]
    atomguess += [ atomGuessRule(self.po.formatAtom(auxa)) for auxa in self.po.auxatoms ]
    # this is A(Pi) in the paper
    nonreplatoms = [ str(atom) for idx, atom in self.po.int2atom.items() if idx not in self.po.replatoms ]
    nonreplatoms += [ self.po.formatAtom(auxa) for auxa in self.po.auxatoms ]
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
    ret = [
      (clingo.parse_term(Aux.CATOMTRUE+'_'+str(atm)), mdl.contains(atm))
      for atm, iatm in self.po.atom2int.items()
      if iatm not in self.po.replatoms ]
    ret += [
      (clingo.Function(name=Aux.CATOMTRUE+'_'+self.po.formatAtom(auxatm)), mdl.is_true(auxatm))
      for auxatm in self.po.auxatoms ]
    return ret

  def checkFLPViolation(self, activeRules, mdl):
    class OnModel:
      def __call__(self, mdl):
        logging.debug('flpModel = '+str(mdl)) 

    assumptions = self._assumptionFromActiveRules(activeRules) + self._assumptionFromModel(mdl)
    modelcb = OnModel()
    if __debug__:
      logging.debug("solving COP with assumptions "+formatAssumptions(assumptions))
    res = self.cc.solve(on_model=modelcb, assumptions=assumptions)
    logging.debug("res=%s", res)
    # if it is unsatisfiable, it has passed the test, i.e., it is an answer set
    return res.unsatisfiable

class FLPCheckerBase:
  def __init__(self, propagatorFactory):
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
    if __debug__:
      logging.debug("FLP check for "+repr(mdl))
    ruleActivityProgram = self.ruleActivityProgram()
    activeRules = ruleActivityProgram.getActiveRulesForModel(mdl)
    if __debug__:
      logging.info("Rules in reduct:")
      for ridx in activeRules:
        r = self.__programObserver.rule_by_index(ridx)
        logging.info("  R rule: "+repr(self.__programObserver.formatAnyRule(r)))
    checkProgram = self.checkProgram()
    is_answer_set = checkProgram.checkFLPViolation(activeRules, mdl)
    if __debug__:
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
