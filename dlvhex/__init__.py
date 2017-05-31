# This package is imported by plugins and used to communicate with the main program!

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

#
# used by plugins
#

CONSTANT = 1
PREDICATE = 2
TUPLE = 3

class ExtSourceProperties:
  def __init__(self):
    pass
  def addFiniteOutputDomain(self, argidx):
    pass
  def __getattr__(self, name):
    class Generic:
      def __init__(self, name):
        self.name = name
      def __call__(self, *arguments):
        logging.info("not implemented: ExtSourceProperties.{}({})".format(
          self.name, ','.join([repr(x) for x in arguments])))
    return Generic(name)

def addAtom(name, inargumentspec, outargumentnum, props=None):
  global callingModule, eatoms
  if name in eatoms:
    raise Exception("atom with name {} registered by module {} already defined by module {}!".format(
      name, callingModule.__name__, eatoms[name].module.__name__))
  try:
    func = getattr(callingModule, name) 
  except:
    raise Exception("could not get function for external atom {} in module {}".format(name, callingModule.__name__))
  if props is None:
    props = ExtSourceProperties()
  eatoms[name] = ExternalAtomHolder(name, inargumentspec, outargumentnum, props, callingModule, func)

def output(tpl):
  global currentOutput
  currentOutput.append(tpl)

def storeAtom(tpl):
  # in dlvhex2 this function registers a new ID for an atom specified in a tuple or retrieves its existing ID
  # WARNING we cannot extend the theory so we will just lookup in the backend
  # WARNING if we do not find in the backend we return an ID with None backend to let other backend code ignore this ID
  raise Exception("TODO implement")

def getInputAtoms():
  global currentInput
  assert(currentInput)
  return currentInput

def getTrueInputAtoms():
  global currentInput
  return [ i for i in currentInput if i.isTrue() ]
  
#
# used by engine
#

# key = eatom name, value = ExternalAtomHolder instance
eatoms = {}
# plugin module that is currently registering eatoms
callingModule = None
# list of ID objects that are predicate input for the currently called external atom
# None if eatom does not take predicate input
currentInput = []
# tuples returned by the current/previously called external atom
currentOutput = []

# called by engine before calling <pluginmodule>.register()
def startRegistration(caller):
  global callingModule
  callingModule = caller

# called by engine before calling external atom function
def startExternalAtomCall(inputs):
  global currentOutput, currentInput
  currentOutput = []
  currentInput = inputs

# called by engine after calling external atom function
def cleanupExternalAtomCall():
  global currentOutput, currentInput
  currentOutput = []
  currentInput = []

class ExternalAtomHolder:
  def __init__(self, name, inspec, outnum, props, module, func):
    assert(isinstance(name, str))
    self.name = name
    assert(isinstance(inspec, tuple) and all([isinstance(x, int) for x in inspec]))
    self.inspec = inspec
    assert(isinstance(outnum, int))
    self.outnum = outnum
    assert(isinstance(props, ExtSourceProperties))
    self.props = props
    self.module = module
    self.func = func
    # this will be set by the engine
    self.executionHandler = None

_specToString = {
  TUPLE: 'TUPLE',
  PREDICATE: 'PREDICATE',
  CONSTANT: 'CONSTANT'
}
def humanReadableSpec(spec):
  return [ _specToString[s] for s in spec ]
