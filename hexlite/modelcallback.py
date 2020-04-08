import dlvhex
import hexlite.auxiliary as aux
import hexlite.clingobackend
import clingo

import logging, sys, json

class StopModelEnumerationException(Exception):
  '''
  throw this exception from model callback to stop enumeration
  '''
  pass

class StandardModelCallback:
  def __init__(self, stringifiedFacts, config):
    self.facts = stringifiedFacts
    self.config = config

  def __call__(self, model):
    assert(isinstance(model, dlvhex.Model))
    if not model.is_optimal:
      logging.info('not showing suboptimal answer set')
      return
    strsyms = [ str(x) for x in model.atoms ]
    if self.config.nofacts:
      strsyms = [ s for s in strsyms if s not in self.facts ]
    if not self.config.auxfacts:
      strsyms = [ s for s in strsyms if not s.startswith(aux.Aux.PREFIX) ]
    if len(model.cost) > 0:
      # first entry = highest priority level
      # last entry = lowest priority level (1)
      #logging.debug('got cost'+repr(model.cost))
      pairs = [ '[{}:{}]'.format(p[1], p[0]+1) for p in enumerate(reversed(model.cost)) if p[1] != 0 ]
      costs=' <{}>'.format(','.join(pairs))
    else:
      costs = ''
    logging.info('showing (optimal) answer set')
    sys.stdout.write('{'+','.join(strsyms)+'}'+costs+'\n')

class JSONModelCallback:
  def __init__(self, stringifiedFacts, config):
    self.facts = stringifiedFacts
    self.config = config

  def structify_r(self, tup, d=0):
    #logging.debug("%sstructify_r %s", ' '*d, tup)
    if isinstance(tup, (tuple,list)):
      # tuples
      if len(tup) == 1:
        return self.structify_r(tup[0], d+1)
      else:
        return { 'name': self.structify_r(tup[0], d+1), 'args': [ self.structify_r(x,d+1) for x in tup[1:] ] }
    else:
      x = tup
      assert(isinstance(x, hexlite.clingobackend.ClingoID))
      if x.symlit.sym.type == clingo.SymbolType.Function and len(x.symlit.sym.arguments) > 0:
        return self.structify_r(x.tuple(), d+1)
      elif x.isInteger():
        return x.intValue()
      else:
        return x.value()

  def structify(self, sym):
    assert(isinstance(sym, dlvhex.ID))
    atomtuple = sym.tuple()
    return self.structify_r(atomtuple)

  def __call__(self, model):
    assert(isinstance(model, dlvhex.Model))
    if not model.is_optimal:
      logging.info('not showing suboptimal answer set')
      return
    str_struc_syms = [ (x,str(x)) for x in model.atoms ]
    if self.config.nofacts:
      # filter out by matching string representation with stringified facts
      str_struc_syms = [ (sym, strsym) for sym, strsym in str_struc_syms if strsym not in self.facts ]
    if not self.config.auxfacts:
      str_struc_syms = [ (sym, strsym) for sym, strsym in str_struc_syms if not strsym.startswith(aux.Aux.PREFIX) ]
    out = {
      'cost': [ { 'priority': p[0]+1, 'cost': p[1] } for p in enumerate(reversed(model.cost)) if p[1] != 0 ],
      'atoms': [ self.structify(sym) for sym, strsym in str_struc_syms ],
      'stratoms': [ strsym for sym, strsym in str_struc_syms ]
    }
    sys.stdout.write(json.dumps(out)+'\n')
    sys.stdout.flush()

