# this is the acthex addon for testing the acthex implementation in hexlite

import acthex

import logging
import sys

# persistence test:
# environment = set of tuples of strings (=atoms), initialized with single atom ('init',)
# @persistenceSet(atom) -> remembers atom in environment
# @persistenceUnset(atom) -> forgets atom in environment
# &persistenceByPred[pred](atom) -> true for all atoms with predicate pred that are remembered in environment
class PersistenceEnvironment(acthex.Environment): 
  def __init__(self):
    self.atoms = set([ ('init',) ])

  def strtuple_of_atom(self, atom):
    return tuple([ x.value() for x in atom.tuple() ])

  def persistence_set_unset(self, atom, set_unset):
    assert(isinstance(atom, acthex.ID))
    assert(set_unset in [True, False])
    if set_unset:
      self.atoms.add(self.strtuple_of_atom(atom))
    else:
      self.atoms.remove(self.strtuple_of_atom(atom))

def persistenceSet(atom):
  assert(isinstance(atom, acthex.ID))
  assert(isinstance(acthex.environment(), PersistenceEnvironment))
  acthex.environment().persistence_set_unset(atom, True)

def persistenceUnset(atom):
  assert(isinstance(atom, acthex.ID))
  assert(isinstance(acthex.environment(), PersistenceEnvironment))
  acthex.environment().persistence_set_unset(atom, False)

def persistenceByPred(pred):
  #logging.debug('persistenceByPred:'+repr(pred))
  assert(isinstance(pred, acthex.ID))
  assert(isinstance(acthex.environment(), PersistenceEnvironment))
  predstr = pred.value()
  for a in acthex.environment().atoms:
    logging.debug("in environment: "+repr(a))
    if a[0] == predstr:
      # output tuple with single term containing full atom
      term = '{}({})'.format(a[0], ','.join(a[1:]))
      logging.debug('persistenceByPred output:'+repr(term))
      acthex.output( (term,) )

# sort test:
# environment = sequence of integers, initialized with 2132635
# @sortSwap(i,j) -> swap positions i and j (0-based) in environment
# @sortDisplay -> display list in environment to stdout
# &sortVal(idx,val) -> provide integer pairs: index/value

class SortEnvironment(acthex.Environment): 
  def __init__(self):
    self.sequence = [2, 1, 3, 2, 6, 3, 5]

  def swap(self, i, j):
    assert(isinstance(i, int))
    assert(isinstance(j, int))
    self.sequence[i], self.sequence[j] = self.sequence[j], self.sequence[i]

  def display(self):
    MAX = len(self.sequence)
    sys.stdout.write('Index: '+', '.join(['{:3}'.format(x) for x in range(0,MAX)])+'\n')
    sys.stdout.write('Value: '+', '.join(['{:3}'.format(x) for x in self.sequence])+'\n')
    sys.stdout.flush()

def sortSwap(i, j):
  assert(isinstance(i, acthex.ID))
  assert(isinstance(j, acthex.ID))
  assert(isinstance(acthex.environment(), SortEnvironment))
  acthex.environment().swap(i.intValue(), j.intValue())

def sortDisplay():
  assert(isinstance(acthex.environment(), SortEnvironment))
  acthex.environment().display()

def sortVal():
  assert(isinstance(acthex.environment(), PersistenceEnvironment))
  for idx, val in enumerate(acthex.environment().sequence):
    acthex.output( (idx, val) )

# combine persistence and sort environments

class TestEnvironment(PersistenceEnvironment,SortEnvironment):
  def __init__(self):
    PersistenceEnvironment.__init__(self)
    SortEnvironment.__init__(self)

# action without environment: print input tuple space-separated to stdout
def printLine(*inputs):
  assert(all([isinstance(x, acthex.ID) for x in inputs]))
  sys.stdout.write(' '.join([x.value().strip('"') for x in inputs])+'\n')
  sys.stdout.flush()

def register():
  acthex.setEnvironment(TestEnvironment())

  acthex.addAction('persistenceSet', (acthex.CONSTANT,))
  acthex.addAction('persistenceUnset', (acthex.CONSTANT,))
  acthex.addAtom('persistenceByPred', (acthex.CONSTANT,), 1)

  acthex.addAction('sortSwap', (acthex.CONSTANT, acthex.CONSTANT))
  acthex.addAction('sortDisplay', ())
  acthex.addAtom('sortVal', (), 2)

  acthex.addAction('printLine', (acthex.TUPLE,))

# vim:nolist:noet:
