# This package is imported by plugins and used to communicate with the main program!

# HEXLite-based solver for a fragment of the ActHEX language
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

import dlvhex

import logging

#
# used by plugins (inherit from dlvhex API)
#

CONSTANT=dlvhex.CONSTANT
PREDICATE=dlvhex.PREDICATE
TUPLE=dlvhex.TUPLE

ExtSourceProperties=dlvhex.ExtSourceProperties

class Environment:
  def __init__(self):
    pass

  def __str__(self):
    return ''

# TODO if we just do addAtom=dlvhex.addAtom will it work the same? (global = global to module where method is registered?)
#def addAtom(name, inargumentspec, outargumentnum, props=None):
#  dlvhex.addAtom(name, inargumentspec, outargumentnum, props)
addAtom=dlvhex.addAtom
output=dlvhex.output
outputUnknown=dlvhex.outputUnknown
learn=dlvhex.learn
storeAtom=dlvhex.storeAtom
storeOutputAtom=dlvhex.storeOutputAtom
getInputAtoms=dlvhex.getInputAtoms
getTrueInputAtoms=dlvhex.getTrueInputAtoms
humanReadableSpec=dlvhex.humanReadableSpec
ID=dlvhex.ID

def setEnvironment(env):
  global currentEnvironment
  logging.info("setting new environment of type %s, replacing environment of type %s", env.__class__, currentEnvironment.__class__)
  currentEnvironment = env

def addAction(name, inargumentspec):
    global actions
    callingModule = dlvhex.callingModule
    if name in actions:
        raise Exception("action with name {} registered by module {} already defined by module {}!".format(
            name, callingModule.__name__, actions[name].module.__name__))
    try:
        func = getattr(callingModule, name)
    except:
        raise Exception("could not get function for action {} in module {}".format(name, callingModule.__name__))
    actions[name] = ActionHolder(name, inargumentspec, callingModule, func)

def environment():
  global currentEnvironment
  return currentEnvironment

#
# used by engine
#

# key = action name, value = ActionHolder instance
actions = {}
currentEnvironment = Environment()

# we do not need our own CurrentExternalAtomEvaluation because only a single environment exists and it is stored in this module

# called by engine before calling action function
# TODO do we need tuple?
def startActionCall(input_tuple, inputs, backend, holder):
  '''
  inputs: frozenset of all ClingoIDs that are relevant to the current eatom evaluation as predicate inputs
  '''
  #currentEvaluation().reset(input_tuple, inputs, backend, holder)

# called by engine after calling external atom function
def cleanupActionCall():
  #currentEvaluation().reset()
  pass

class ActionHolder:
  def __init__(self, name, inspec, module, func):
    assert(isinstance(name, str))
    self.name = name
    assert(isinstance(inspec, tuple) and all([isinstance(x, int) for x in inspec]))
    self.inspec = inspec
    self.module = module
    self.func = func

class IterationExit(Exception):
  pass
