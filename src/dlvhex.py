# this module is imported by plugin modules and used to communicate with the main program!

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

#
# used by engine
#

atoms = {}
callingModule = None

def startRegistration(caller):
  # store who is registering next
  global callingModule
  callingModule = caller

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
