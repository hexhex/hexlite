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
  atoms[name] = ExternalAtomHandler(name, inargumentspec, outargumentnum, props, callingModule, func)

#
# used by engine
#

atoms = {}
callingModule = None

def startRegistration(caller):
  # store who is registering next
  global callingModule
  callingModule = caller

class ExternalAtomHandler:
  def __init__(self, name, inspec, outnum, props, module, func):
    self.name = name
    self.inspec = inspec
    self.outnum = outnum
    self.props = props
    self.module = module
    self.func = func


logging.debug('loaded (internal) dlvhex module')
