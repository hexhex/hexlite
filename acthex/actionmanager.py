
import dlvhex
import acthex

import hexlite.auxiliary as aux
import hexlite.ast.shallowparser as shp

import logging

class ActionToBeExecuted:
  def __init__(self, name, args, prio):
    assert(isinstance(name, str))
    self.name = name
    assert(isinstance(args, tuple))
    assert(all([isinstance(arg, dlvhex.ID) for arg in args]))
    self.arguments = args
    assert(isinstance(prio, int))
    self.prio = prio
  def __repr__(self):
    return str(self)
  def __str__(self):
    return "@{}({}){{{}}}".format(self.name, ','.join([str(x) for x in self.arguments]), self.prio)

def extractActions(model):
  def parseAction(a):
    assert(isinstance(a, dlvhex.ID))
    atuple = a.tuple()
    logging.debug("parseAction on tuple "+repr(atuple))
    aname, aargs, aprio = atuple[0].value(), atuple[1].tuple()[1:], atuple[2].intValue()
    aname = aname[len(aux.Aux.ACTREPL)+1:]
    logging.debug("from ID={} extracted name={} args={} prio={}".format(repr(a), repr(aname), repr(aargs), repr(aprio)))
    return ActionToBeExecuted(aname, aargs, aprio)
  return [ parseAction(a) for a in model.atoms if a.value().startswith(aux.Aux.ACTREPL) ]

def buildSchedule(actions):
  return sorted(actions, key=lambda action: action.prio)

def executeInternalAction(action):
  if action.name == 'acthexStop':
    if len(action.arguments) != 0:
      raise ValueError("acthexStop action does not take arguments: "+repr(action))
    # effect of this action is to stop iteration upon execution, this is done via this exception
    raise acthex.IterationExit()
  # action is not handled here
  return False

def executeAction(action):
  aname = action.name
  if executeInternalAction(action):
    return
  if aname not in acthex.actions:
    raise KeyError("action name {} of action {} was not registered with acthex!".format(aname, repr(action)))
  aholder = acthex.actions[aname]
  # TODO check aholder.inspec
  aholder.func(*action.arguments)

def executeActions(model):
  # extract actions from model
  actions = extractActions(model)
  logging.debug("extracted actions: %s", actions)
  # build schedule
  schedule = buildSchedule(actions)
  logging.info("action schedule: %s", schedule)
  # execute on environment
  for action in schedule:
    executeAction(action)
