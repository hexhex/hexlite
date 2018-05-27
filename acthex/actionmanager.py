
import dlvhex

import hexlite.aux as aux
import hexlite.ast.shallowparser as shp

import logging

class ActionToBeExecuted:
  def __init__(self, name, args, prio):
    self.name = name
    self.args = args
    self.prio = prio

def extractActions(model):
  def parseAction(a):
    assert(isinstance(a, dlvhex.ID))
    aname, aargs, aprio = a.tuple()
    aname = aname[len(aux.Aux.ACTREPL):]
    logging.debug("from ID={} extracted name={} args={} prio={}".format(repr(a), repr(aname), repr(aargs), repr(aprio)))
    return ActionToBeExecuted(aname, aargs, aprio)
  return [ parseAction(a) for a in model.atoms if a.value().startswith(aux.Aux.ACTREPL) ]

def executeActions(model):
  # extract actions from model
  actions = extractActions(model)
  logging.debug("extracted actions: %s", actions)
  # build schedule
  # execute on environment
  raise Exception("not implemented")
