# This module is imported by plugin modules and used to communicate with the main program!

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

def addAtom(name, inargumentspec, outargumentnum, props=None):
  global callingModule, atoms
  if name in atoms:
    raise Exception("atom with name {} registered by module {} already defined by module {}!".format(
      name, callingModule.__name__, atoms[name].module.__name__))
  try:
    func = getattr(callingModule, name) 
  except:
    raise Exception("could not get function for external atom {} in module {}".format(name, callingModule.__name__))
  if props is None:
    props = ExtSourceProperties()
  atoms[name] = ExternalAtomHolder(name, inargumentspec, outargumentnum, props, callingModule, func)

def output(tpl):
  global currentOutput
  currentOutput.append(tpl)

#
# used by engine
#

# key = eatom name, value = ExternalAtomHolder instance
atoms = {}
# plugin module that is currently registering atoms
callingModule = None
# tuples returned by the current/previously called external atom
currentOutput = []

# called by engine before calling <pluginmodule>.register()
def startRegistration(caller):
  global callingModule
  callingModule = caller

# called by engine before calling external atom function
def startExternalAtomCall():
  global currentOutput
  currentOutput = []

# called by engine after calling external atom function
def cleanupExternalAtomCall():
  global currentOutput
  currentOutput = []

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

logging.debug('loaded (internal) dlvhex module')
