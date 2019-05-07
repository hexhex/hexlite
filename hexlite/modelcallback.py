import dlvhex
import hexlite.aux as aux

import logging, sys

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
      logging.debug('got cost'+repr(model.cost))
      pairs = [ '[{}:{}]'.format(p[1], p[0]+1) for p in enumerate(reversed(model.cost)) if p[1] != 0 ]
      costs=' <{}>'.format(','.join(pairs))
    else:
      costs = ''
    logging.info('showing (optimal) answer set')
    sys.stdout.write('{'+','.join(strsyms)+'}'+costs+'\n')

