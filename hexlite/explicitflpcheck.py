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

def msg(s):
  logging.info(s)


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
    self.atom2int = {}
    self.int2atom = {}
    self.rules = [] # it is a set but let's assume gringo/clasp are clever enough
    self.facts = set()
    self.maxAtom = 1
    self.waitingForStuff = True

  def init_program(self, incr):
    pass
  def begin_step(self):
    self.waitingForStuff = True
  def end_step(self):
    self.waitingForStuff = False
    self.printall()
  def __getattr__(self, name):
    return self.WarnMissing(name)
  def rule(self, choice, head, body):
    #logging.debug("GPRule ch={} hd={} b={}".format(repr(choice), repr(head), repr(body)))
    if choice == False and len(head) == 1 and len(body) == 0:
      # ignore rules for facts, they are eliminated from bodies anyways
      pass
    else:
      self.rules.append( (choice, head, body) )
  def weight_rule(self, choice, head, lower_bound, body):
    raise Exception("weight_rule [aggregates] not yet implemented in FLP checker")
  def output_atom(self, symbol, atom):
    #logging.debug("GPAtom symb={} atm={}".format(repr(symbol), repr(atom)))
    if atom == 0L:
      self.facts.add(symbol)
    else:
      self.atom2int[symbol] = atom
      self.int2atom[atom] = symbol
      self.maxAtom = max(self.maxAtom, atom)
  def printall(self):
    if __debug__:
      logging.debug("facts:")
      logging.debug('  '+', '.join([ str(f) for f in self.facts]))
      logging.debug("rules:")
      for choice, head, body in self.rules:
        #logging.debug('triple:'+repr((choice, head, body)))
        #logging.debug('keys:'+repr(self.int2atom.keys()))
        headstr = HSEP[choice].join([str(self.int2atom[x]) for x in head])
        #logging.debug('headstr' + headstr)
        bodystr = ' , '.join([str(self.int2atom[x]) for x in body])
        #logging.debug('bodystr' + bodystr)
        logging.debug('  {}{}{}:-{}.'.format(HBEG[choice], headstr, HEND[choice], bodystr))

  def finished(self):
    # true if at least one program was fully received
    return not self.waitingForStuff

  def cargo(self):
    return self.facts, self.rules, self.atom2int, self.int2atom, self.maxAtom

class RuleActivityProgram:
  AUXRHPRED = 'aux_rh'
  def __init__(self, programObserver):
    self.po = programObserver
    self.cc = clingo.Control()
    prog = self._build()
    with self.cc.builder() as b:
      for rule in prog:
        logging.debug('parsing rule: '+repr(rule))
        clingo.parse_program(rule, lambda ast: b.add(ast))
    self.cc.ground([("base", [])])

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

  def _assumptionFromModel(self, mdl):
    syms = mdl.symbols(atoms=True, terms=True)
    return [ (atm, mdl.contains(atm)) for atm in self.po.atom2int ]

  def _build(self):
    def headActivityRule(idx, chb, int2atom):
      choice, head, body = chb
      # we only use the body!
      sbody = ','.join([str(int2atom[x]) for x in body])
      if len(body) == 0:
        return '{}({}).'.format(self.AUXRHPRED, idx)
      else:
        return '{}({}) :- {}.'.format(self.AUXRHPRED, idx, sbody)
    def atomGuessRule(atom):
      return  '{'+str(atom)+'}.'
      
    assert(self.po.finished())
    cargo = self.po.cargo()
    facts, rules, atom2int, int2atom, maxAtom = cargo

    # add rules but put new atoms instead of heads
    rarules = [ headActivityRule(idx, chb, int2atom) for idx, chb in enumerate(rules) ]
    raguesses = [ atomGuessRule(atom) for atom in atom2int.keys() ]
    return rarules + raguesses + ['#show {}/1.'.format(self.AUXRHPRED)]

class ExplicitFLPChecker:
  def __init__(self):
    self._ruleActivityProgram = None
    logging.debug("initializing explicit FLP checker")

  def attach(self, clingocontrol):
    self.programObserver = GroundProgramObserver()
    clingocontrol.register_observer(self.programObserver)

  def checkModel(self, mdl):
    # returns True if mdl passes the FLP check (= is an answer set)
    ruleActivityProgram = self.ruleActivityProgram()
    activeRules = ruleActivityProgram.getActiveRulesForModel(mdl)
    for r in activeRules:
      logging.info("rule active in reduct: "+repr(self.programObserver.rules[r]))
      raise Exception("TODO next: debug reduct and build check program")
    return True

  def ruleActivityProgram(self):
    # on first call, creates control object and fills with program
    # otherwise reuses old one control object with new assumptions
    if not self._ruleActivityProgram:
      self._ruleActivityProgram = RuleActivityProgram(self.programObserver)
    return self._ruleActivityProgram
