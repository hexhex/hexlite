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

def prefixAtom(atom, prefix):
  # prefix without breaking strong negation
  assert(isinstance(atom, str))
  if atom[0] == '-':
    return '-'+prefix+atom[1:]
  else:
    return prefix+atom

def prefixIfNonempty(s, prefix):
  if len(s) == 0:
    return s
  else:
    return prefix+s

def ruleHeadAux(idx):
  return Aux.RHPRED+'('+str(idx)+')'

class GroundProgramObserver:
  class WarnMissing:
    def __init__(self, name):
      self.name = name
    def __call__(self, *arguments):
      logging.debug("GPOWarning {} {}".format(self.name, repr(arguments)))

  def __init__(self):
    # a program is a set of rules, we assume gringo/clasp are clever enough to eliminate duplicates

    # facts (list of clingo.Symbol)
    self.facts = []
    # clasp non-fact and non-auxiliary atoms
    self.atom2int = {} # clingo.Symbol to int
    self.int2atom = {} # int to clingo.Symbol
    # clasp auxiliary atoms (set of int)
    self.auxatoms = set()
    # all atoms from int2atom and clasp auxiliaries (set of int)
    self.atoms = set()
    # eatom truth replacement atoms (set of int)
    self.replatoms = set()
    # atoms in choice rule heads that are not replatoms (set of int)
    self.chatoms = set()

    # weight rules and normal rules are stored together, distinguished by first tuple element
    # normal rule (0,choice,head,body)
    # weight rule (1,choice,head,lowerbound,body)
    # choice is the same for all rules in one of the following three (disjoint) lists
    # constraints are disjunctive rules with empty head

    # choice rules for eatom replacement guessing
    self.replrules = []
    # choice rules that are not for eatom replacement guessing
    self.chrules = []
    # disjunctive rules
    self.djrules = []
    # all rules in one container (only references copied)
    self.allrules = []
    # base indexes for rule containers in self.allrules
    self.replrules_base, self.chrules_base, self.djrules_base = 0, 0, 0

    # for receiving rules
    self.waitingForStuff = True
    self.preliminaryrules = []
    self.preliminaryweightrules = []

  def init_program(self, incr):
    logging.debug("GPInit")
    pass
  def begin_step(self):
    logging.debug("GPBeginStep")
    self.waitingForStuff = True
  def end_step(self):
    logging.debug("GPEndStep")
    # auxatoms
    self.extractAuxAtoms()
    # atoms
    self.atoms = self.auxatoms | set(self.int2atom.keys())
    # replatoms
    self.extractReplAtoms()
    # chatoms replrules chrules djrules
    self.preliminaryToCategorizedRules()
    # allrules
    self.allrules = self.replrules + self.chrules + self.djrules
    self.replrules_base = 0
    self.chrules_base = len(self.replrules)
    self.djrules_base = len(self.replrules)+len(self.chrules)
    # done!
    self.waitingForStuff = False
    if __debug__:
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
    self.preliminaryweightrules.append( (choice, head, lower_bound, body) )
  def output_atom(self, symbol, atom):
    logging.debug("GPAtom symb=%s atm=%s", repr(symbol), repr(atom))
    if atom == long(0):
      # this is not a literal but a signal that symbol is always true (i.e., a fact)
      self.facts.append(symbol)
    else:
      self.atom2int[symbol] = atom
      self.int2atom[atom] = symbol

  def extractAuxAtoms(self):
    def from_lits(lits):
      for lit in lits:
        alit = abs(lit)
        if alit not in self.int2atom:
          self.auxatoms.add(alit)
    for choice, head, body in self.preliminaryrules:
      from_lits(head+body)
    for choice, head, lower_bound, body in self.preliminaryweightrules:
      from_lits(head+[at for (at,w) in body])

  def extractReplAtoms(self):
    self.replatoms |= set([ at for at, sym in self.int2atom.items()
      if sym.name.startswith(Aux.EAREPL) ])

  def preliminaryToCategorizedRules(self):
    for choice, head, body in self.preliminaryrules:
      if not choice:
        self.djrules.append( (0,choice,head,body) )
      else:
        assert(len(head) > 0) # constraints should be disjunctive rules
        if head[0] in self.replatoms:
          assert(all([x in self.replatoms for x in head]))
          self.replrules.append( (0,choice,head,body) )
        else:
          assert(all([x not in self.replatoms for x in head]))
          self.chrules.append( (0,choice,head,body) )
          self.chatoms |= set(head)
    for choice, head, lowerbound, body in self.preliminaryweightrules:
      if not choice:
        self.djrules.append( (1,choice,head,lowerbound,body) )
      else:
        assert(len(head) > 0) # weight constraints should be disjunctive rules
        if head[0] in self.replatoms:
          assert(all([x in self.replatoms for x in head]))
          self.replrules.append( (1,choice,head,lowerbound,body) )
        else:
          assert(all([x not in self.replatoms for x in head]))
          self.chrules.append( (1,choice,head,lowerbound,body) )
          self.chatoms |= set(head)

    # after this categorization we should not use the following containers anymore
    del(self.preliminaryrules)
    del(self.preliminaryweightrules)

  ### above = building data structures, below = accessing data structures

  def formatAtom(self, iatom):
    absatom = abs(iatom)
    if absatom in self.int2atom:
      stratom = str(self.int2atom[absatom])
    else:
      stratom = Aux.CLATOM+str(absatom)
    assert(iatom != long(0))
    if iatom > long(0):
      # positive literal
      return stratom
    else:
      # negative literal
      return 'not '+stratom

  def formatHead(self, choice, ihead):
    return HBEG[choice] + HSEP[choice].join([self.formatAtom(x) for x in ihead]) + HEND[choice]

  def formatNormalBody(self, body):
    return ','.join([self.formatAtom(x) for x in body])

  def formatNormalRule(self, choice, head, body):
    headstr = self.formatHead(choice, head)
    if len(body) == 0:
      return headstr+'.'
    else:
      bodystr = self.formatNormalBody(body)
      return headstr+':-'+bodystr+'.'

  def formatWeightBody(self, lower_bound, body):
    # XXX DANGER: the weight rules in ASPIF have no collapsing mechanism
    # -> getting (1,-13), (1,-13) as body atoms needs to count 2 if 13 is false!
    def formatElement(idx, e):
      iatom, weight = e
      a = self.formatAtom(iatom)
      return "{w},{idx}:{a}".format(a=a, idx=idx, w=weight)
    assert(len(body) > 0)
    selems = ';'.join([formatElement(idx, e) for idx, e in enumerate(body)])
    return str(lower_bound)+'<=#sum{'+ selems + '}'

  def formatWeightRule(self, choice, head, lower_bound, body):
    headstr = self.formatHead(choice, head)
    assert(len(body) > 0)
    return headstr + ':-' + self.formatWeightBody(lower_bound, body) + '.'

  def formatRule(self, anyrule):
    if anyrule[0] == 0:
      # normal rule (0,choice,head,body)
      return self.formatNormalRule(*anyrule[1:])
    else:
      # weight rule (1,choice,head,lowerbound,body)
      assert(anyrule[0] == 1)
      return self.formatWeightRule(*anyrule[1:])

  def formatBody(self, anyrule):
    if anyrule[0] == 0:
      # normal rule (0,choice,head,body)
      return self.formatNormalBody(anyrule[3])
    else:
      # weight rule (1,choice,head,lowerbound,body)
      assert(anyrule[0] == 1)
      return self.formatWeightBody(anyrule[3], anyrule[4])

  def printall(self):
    logging.debug('facts:'+', '.join([ str(f) for f in self.facts]))
    logging.debug('auxatoms:'+', '.join([ self.formatAtom(ia) for ia in self.auxatoms]))
    logging.debug('replatoms:'+', '.join([ self.formatAtom(ia) for ia in self.replatoms]))
    logging.debug('chatoms:'+', '.join([ self.formatAtom(ia) for ia in self.chatoms]))
    logging.debug("replrules:")
    for r in self.replrules:
      logging.debug('  '+self.formatRule(r))
    logging.debug("chrules:")
    for r in self.chrules:
      logging.debug('  '+self.formatRule(r))
    logging.debug("djrules:")
    for r in self.djrules:
      logging.debug('  '+self.formatRule(r))

  def finished(self):
    # true if at least one program was fully received
    return not self.waitingForStuff

class RuleActivityProgram:
  '''
  This program is a transformed version of the ground program Pi with HEX replacement atoms.

  It contains:
  (I) a guess for each atom in Pi:
    { a }.  for $a \in atoms$
  (II) for each (non-fact) rule in Pi a rule with a unique head RHPRED(ruleidx) and the body of the original rule.
    RHPRED(i) :- BODY.  for all r_i \in (replrules \cup chrules \cup djrules)

  The purpose of this program is to find out which rule bodies are satisfied
  (i.e., which rules are in the FLP reduct) in a given answer set.

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
    ret = [ (atm, mdl.contains(atm)) for atm in self.po.atom2int.keys() ]
    ret += [ (clingo.Function(self.po.formatAtom(auxatm)), mdl.is_true(auxatm))
             for auxatm in self.po.auxatoms ]
    return ret

  def _build(self):
    def headActivityRule(idx, rule):
      activityatom = ruleHeadAux(idx)
      # normal rule (0,choice,head,body)
      # weight rule (1,choice,head,lowerbound,body)
      if rule[0] == 0:
        body = rule[3]
        if len(body) == 0:
          return activityatom + '.'
        else:
          return activityatom + ':-' + self.po.formatNormalBody(body) + '.'
      else:
        lb = rule[3]
        body = rule[4]
        assert(len(body) > 0)
        return activityatom + ':-' + self.po.formatWeightBody(lb, body) + '.'

    def atomGuessRule(iatm):
      return  '{'+self.po.formatAtom(iatm)+'}.'
      
    assert(self.po.finished())

    # (I) guess for each atom
    raguesses = [ atomGuessRule(atm) for atm in self.po.atoms ]
    # (II) rules with special auxiliary heads
    rarules = [ headActivityRule(idx, rule) for idx, rule in enumerate(self.po.allrules) ]
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

  It is an adaptation of Proposition 1 from the following paper:
  Eiter, T., Fink, M., Krennwallner, T., Redl, C., & Schüller, P. (2014).
  Efficient HEX-Program Evaluation Based on Unfounded Sets.
  Journal of Artificial Intelligence Research, 49, 269–321.

  (The adaptation is about choice rules.)

  We classify the following information from GroundProgramObserver:
  Let $facts$ be all symbols of facts.
    [assumption (ensured by clasp/clingo API) atoms and facts are disjoint]
  Let $atoms$ be all atoms with ID != 0.
    (Some of these are clasp auxiliaries, all others have a symbol, maybe strong negation.)
  Let $replatoms \subseteq atoms$ be atoms used in choice heads of external replacement guesses.
  Let $chatoms \subseteq atoms$ be atoms used in choice heads that are not external replacement guesses.
  Let $rules$ be all normal and weight rules.
  Let $replrules \subseteq rules$ be all choice rules (normal and weight rules) with only replatoms as heads.
  Let $chrules \subseteq$ be all choice rules (normal and weight rules) without replatoms in the head.
    [assumption: a choice rule either has a single replatom in the head, or only non-replatoms in their head]
  Let $djrules \subseteq rules$ be all non-choice rules (normal and weight rules).
    [assumption: disjunctive rules never have replatoms in their head]

  Then the set of \emph{counter-model atoms} is the set
    $cmatoms = atoms \setminus replatoms \cup { CHAUX(b) | b \in chatoms }$
  which contains original atoms without external atom replacements,
    plus auxiliaries for all atoms in (non-replacement rule) choice heads.

  Then the check program contains:
  (I) A guess for activity of each rule $r_i \in rules$:
    { AUX_RH(i) }.
    (These truths will be fully determined by a solver assumption to fix the FLP reduct.)
  (II) A guess of the compatible set that is investigated:
    for all atoms $x \in cmatoms$ (including choice auxiliaries) we have
    { AUX_CS(x) }.
    (These truths will be fully determined by a solver assumption to fix the compatible set.)
  (III) A guess { x } :- AUX_CS(x). for each atom $x \in cmatoms$ to guess countermodel atoms wrt a compatible set.
  (IV) A constraint that ensures that the countermodel is not greater than the compatible set:
    :- x, not AUX_CS(x).  for each atom $x \in cmatoms$
  (V) A rule that detects if the model is smaller than the compatible set:
    AUX_SMALLER :- not x, AUX_CS(x).  for each $x \in cmatoms$
  (VI) A constraint that requires to find a smaller answer set:
    :- not AUX_SMALLER.
  (VII) All facts from the original ground program (only needed for external atom evaluation):
    x.   for all $x \in facts$
  (VIII) For each rule $r_i \in djrules/replrules/chrules$:
    HEAD :- AUX_RH(i), BODY.
  (IX) For each choice rule $r_i = { ch_1 ; ... ; ch_n } :- BODY$ with $r_i \in chrules$:
    ch_i | AUX_CH(ch_i).  for all i \in 1,...,n
    [Without condition, for a choice head atom there is a disjunctive guess].

  The purpose of this program is to check if the FLP reduct has a model that is smaller than the original compatible set.

  This is determined using solver assumptions which
  * fully determine the guesses (I) to determine the FLP reduct, and
  * fully determine the guess (II) to determine the compatible set.

  For this program we also need to check if external atom semantics are correctly captured by the guesses,
  so we include the propagator from the main solver in the search.

  TODO share input/output cache for external atoms (if we implement one)
  '''
  def __init__(self, programObserver, propagatorFactory):
    self.po = programObserver
    # name of this propagator = FLP checker
    self.eatomPropagator = propagatorFactory('FLP')
    # build program
    self.cc = clingo.Control()
    # dictionary from self.po.chatoms (int) to the respective choice auxiliaries (str)
    self.chauxatoms = {}
    # list of str of all cmatoms that are relevant for the compatible set
    self.cmatoms = []
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
    assert(self.po.finished())

    # create dictionary from self.po.chatoms (int) to the respective choice auxiliaries (str)
    self.chauxatoms = dict([
      (ichatom, prefixAtom(self.po.formatAtom(ichatom), Aux.CHATOM))
      for ichatom in self.po.chatoms ])
    if __debug__:
      logging.debug('chauxatoms '+repr(self.chauxatoms))

    # compute cmatoms (strings of all atoms relevant for compatible set)
    self.cmatoms = [ self.po.formatAtom(iatom)
                     for iatom in self.po.atoms
                     if iatom not in self.po.replatoms ]
    self.cmatoms += self.chauxatoms.values()
    if __debug__:
      logging.debug('cmatoms '+repr(self.cmatoms))

    # (I)
    rhguess = [ '{'+ruleHeadAux(idx)+'}.' for idx in range(0, len(self.po.allrules)) ]
    # (II)
    csguess = [ '{'+prefixAtom(a, Aux.CSATOM)+'}.' for a in self.cmatoms ]
    # (III)
    atomguess = [ '{'+a+'}:-'+prefixAtom(a, Aux.CSATOM)+'.' for a in self.cmatoms ]
    # (IV)
    ensureng = [ ':-'+a+',not '+prefixAtom(a, Aux.CSATOM)+'.' for a in self.cmatoms ]
    # (V)
    defsmaller = [ Aux.SMALLER+':-not '+a+','+prefixAtom(a, Aux.CSATOM)+'.' for a in self.cmatoms ]
    # (VI)
    needsmaller = [ ':-not '+Aux.SMALLER+'.' ]
    # (VII)
    sfacts = [ str(f)+'.' for f in self.po.facts ]
    # (VIII)
    def formatAnyRuleInjectAux(rule, idx):
      # normal rule (0,choice,head,body)
      # weight rule (1,choice,head,lowerbound,body)
      choice, head = rule[1], rule[2]
      # automagic body formatting
      return self.po.formatHead(choice, head)+':-'+ruleHeadAux(idx)+prefixIfNonempty(self.po.formatBody(rule),',')+'.'
    allrules = [ formatAnyRuleInjectAux(rule, idx) for idx, rule
                in enumerate(self.po.allrules) ]
    # normal rule (0,choice,head,body)
    # weight rule (1,choice,head,lowerbound,body)
    chrules = [ self.po.formatAtom(iatm)+'|'+self.chauxatoms[iatm]+'.'
                for rule in self.po.chrules
                for iatm in rule[2] ]

    # transform cmatoms into clingo terms of the compatible set auxiliaries
    # (we no longer need them in their original form)
    # (we will need them in this way for the assumptions)
    #self.cmatoms = [ clingo.parse_term(a) for a in self.cmatoms ]

    return rhguess + csguess + atomguess + ensureng + defsmaller + needsmaller + sfacts + allrules + chrules

  def _assumptionFromActiveRules(self, activeRules):
    # activeRules is a set of integers (indices into self.po.allrules)
    # for each rule we either put positive or negative assumption to fully determine the FLP reduct
    # TODO this can be optimized over multiple checks by caching the sequence and only changing the booleans
    return [
      (clingo.Function(Aux.RHPRED, [clingo.Number(ruleidx)]), ruleidx in activeRules)
      for ruleidx in range(0, len(self.po.allrules)) ]

  def _assumptionFromModel(self, mdl):
    # mdl contains the answer set candidate
    # we here create assumptions for compatible set auxiliaries
    ret = []

    #
    # for all atoms in Pi that are not replatoms we create an assumption
    #

    # symbolic atoms that are not replatoms
    for iatm, atm in self.po.int2atom.items():
      if iatm in self.po.replatoms:
        continue
      # TODO cache csAtom <-> iatm
      csAtom = clingo.parse_term(prefixAtom(str(atm), Aux.CSATOM))
      # TODO maybe use is_true here too (iatm) TODO benchmark this
      ret.append( (csAtom, mdl.contains(atm)) )

    # clasp auxiliaries (that are implicitly never replatoms)
    for iauxatm in self.po.auxatoms:
      # TODO cache csAtom <-> iauxatm
      csAtom = clingo.Function(name=prefixAtom(self.po.formatAtom(iauxatm), Aux.CSATOM))
      ret.append( (csAtom, mdl.is_true(iauxatm)) )

    #
    # additionally, for choice auxiliaries of chatoms in Pi we create assumptions
    # these assumptions are the negation of the positive chatom value
    #

    # choice auxiliaries of chatoms
    for ichatom, chauxatom in self.chauxatoms.items():
      # TODO cache csAtom <-> iauxatm
      csAtom = clingo.parse_term(prefixAtom(chauxatom, Aux.CSATOM))
      ret.append( (csAtom, not mdl.is_true(ichatom)) )
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
        r = self.__programObserver.allrules[ridx]
        logging.info("  R rule: "+repr(self.__programObserver.formatRule(r)))
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
