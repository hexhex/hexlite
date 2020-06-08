# This package is imported by plugins and used to communicate with the main program!

# HEXLite Python-based solver for a fragment of HEX
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

import logging, inspect

#
# used by plugins
#

CONSTANT = 1
PREDICATE = 2
TUPLE = 3

class StoreAtomException(Exception):
  '''
  this exception is thrown if storeAtom(...) and similar are called for symbols that do not exist in the solver

  (nogoods that should contain these atoms can not, must not, and need not be learned)
  '''
  def __init__(self, msg):
    super().__init__(msg)

class ExtSourceProperties:
  def __init__(self):
    self.provides_partial = False
    self.doInputOutputLearning = True
  def setProvidesPartialAnswer(self, provides_partial):
    self.provides_partial = provides_partial
  def addFiniteOutputDomain(self, argidx):
    pass

  def setDoInputOutputLearning(self, doInputOutputLearning):
    # True = add nogood for input/output behavior of external atom
    # set this to False if the external atom creates own nogoods that cut the search space much better than naive nogoods created in hexlite
    self.doInputOutputLearning = doInputOutputLearning
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

def output(tuple_):
  assert(isinstance(tuple_, tuple)) # because we store it in a set
  logging.debug("got output tuple %s", repr(tuple_))
  currentEvaluation().outputKnownTrue.add(tuple_)

def outputUnknown(tuple_):
  assert(isinstance(tuple_, tuple)) # because we store it in a set
  currentEvaluation().outputUnknown.add(tuple_)

def learn(nogood):
  # add nogood (given as IDs) to search process
  currentEvaluation().backend.learn(nogood)

def storeAtom(tpl):
  # build an atom specified in a tuple and retrieves its existing ID or registers a new atom (and ID)
  # WARNING hexlite will not extend the theory during search so we will just lookup in the backend
  # WARNING if we do not find in the backend we throw StoreAtomException
  return currentEvaluation().backend.storeAtom(tpl)

def storeOutputAtom(args, sign=True):
  # build a replacement atom for the currently called external atom with the given tuple as arguments and retrieves its ID or registers a new atom (and ID)
  # WARNING hexlite will not extend the theory during search so we will just lookup in the backend
  # WARNING if we do not find in the backend we throw StoreAtomException
  return currentEvaluation().backend.storeOutputAtom(args, sign)

def getInstantiatedOutputAtoms():
  # obtain all output atoms of currently called external atom that have been instantiated in the solver and can therefore be used in nogoods
  # the return value is a list of symbols of replacement atoms
  return currentEvaluation().backend.getInstantiatedOutputAtoms()

def storeConstant(c):
  # gives back an ID that represents the constant c
  return currentEvaluation().backend.storeConstant(c)

def storeString(s):
  # gives back an ID that represents the string s
  return currentEvaluation().backend.storeString(s)

def storeInteger(i):
  # gives back an ID that represents the integer i
  return currentEvaluation().backend.storeInteger(i)

def storeParseable(p):
  # gives back an ID that represents the parsable term p
  return currentEvaluation().backend.storeParseable(p)

def getInputAtoms():
  return currentEvaluation().input

def getTrueInputAtoms():
  return [ i for i in currentEvaluation().input if i.isTrue() ]

def registerModelCallbackClass(handler):
  '''
  register a model callback class (see hexlite.modelcallbacks)
  '''
  global modelCallbacks
  assert(inspect.isclass(handler))
  modelCallbacks.append(handler)

def removeModelCallbackClass(handler):
  global modelCallbacks
  modelCallbacks = [ x for x in modelCallbacks if x != handler ]

#
# used by engine
#

class Backend:
  def learn(self, nogood):
    logging.warning("not implemented: Backend::learn")

  def storeAtom(self, tpl):
    logging.warning("not implemented: Backend::storeAtom")
    return None

  def storeOutputAtom(self, args, sign):
    logging.warning("not implemented: Backend::storeOutputAtom")
    return None

  def storeConstant(self, s: str):
    logging.warning("not implemented: Backend::storeConstant")
    return None

  def storeInteger(self, i: int):
    logging.warning("not implemented: Backend::storeInteger")
    return None

# key = eatom name, value = ExternalAtomHolder instance
eatoms = {}
# plugin module that is currently registering eatoms
callingModule = None
# list of handlers to be called, default handler is called if empty
modelCallbacks = []

class CurrentExternalAtomEvaluation:
  def __init__(self):
    self.reset()

  def reset(self, inputTuple=(), inputs=frozenset(), backend=Backend(), holder=None):
    # current input tuple (also passed directly to function, but for storeOutputAtom we need to know this, too)
    self.inputTuple = inputTuple
    # frozen set of ID objects that are predicate input for the currently called external atom
    # None if eatom does not take predicate input
    self.input = inputs
    # tuples returned by the current/previously called external atom
    self.outputKnownTrue = set()
    self.outputUnknown = set()
    # object realizing the Backend interface for the currently calling backend
    self.backend = backend
    # currently processed eatom holder
    self.holder = holder

# all data relevant to external atom evaluation (dlvhex.* API)
currentEvaluationStorage = CurrentExternalAtomEvaluation()

def currentEvaluation():
  return currentEvaluationStorage

# called by engine before calling <pluginmodule>.register()
def startRegistration(caller):
  global callingModule
  callingModule = caller

# called by engine before calling external atom function
def startExternalAtomCall(input_tuple, inputs, backend, holder):
  '''
  inputs: frozenset of all ClingoIDs that are relevant to the current eatom evaluation as predicate inputs
  '''
  currentEvaluation().reset(input_tuple, inputs, backend, holder)
  logging.debug("starting evaluation %s %s", tuple([ str(x) for x in input_tuple ]), sorted([ str(x) for x in inputs if x.isTrue() ]))

# called by engine after calling external atom function
def cleanupExternalAtomCall():
  currentEvaluation().reset()

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
    # this is for rewriting
    self.executionHandler = None

_specToString = {
  TUPLE: 'TUPLE',
  PREDICATE: 'PREDICATE',
  CONSTANT: 'CONSTANT'
}
def humanReadableSpec(spec):
  return [ _specToString[s] for s in spec ]

class ID:
  '''
  atoms and constants as communicated between hexlite and plugins

  the name is historic from the 64 bit ID datatype in dlvhex
  '''
  def negate(self):
    raise NotImplementedError()
  def value(self):
    raise NotImplementedError()
  def intValue(self):
    raise NotImplementedError()
  def isTrue(self):
    raise NotImplementedError()
  def isFalse(self):
    raise NotImplementedError()
  def isAssigned(self):
    raise NotImplementedError()
  def tuple(self):
    raise NotImplementedError()
  def extension(self):
    raise NotImplementedError()
  def __str__(self):
    raise NotImplementedError()
  def __repr__(self):
    raise NotImplementedError()

class Model:
  def __init__(self, atoms, cost, is_optimal):
    assert(isinstance(atoms, frozenset))
    assert(all([isinstance(x, ID) for x in atoms]))
    self.atoms = atoms
    assert(isinstance(cost, list))
    assert(all([isinstance(x, int) for x in cost]))
    self.cost = cost
    assert(is_optimal in [True, False])
    self.is_optimal = is_optimal

