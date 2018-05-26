# this is the acthex addon for testing the acthex implementation in hexlite

import acthex

# persistence test:
# environment = set of tuples of strings (=atoms), initialized with single atom ('init',)
# @persistenceSet(atom) -> remembers atom in environment
# @persistenceUnset(atom) -> forgets atom in environment
# &persistenceByPred[pred](atom) -> true for all atoms with predicate pred that are remembered in environment
class PersistenceEnvironment(acthex.Environment): 
  def __init__(self):
    self.atoms = set()

  def persistence_set_unset(self, atom, set_unset):
    assert(isinstance(atom, acthex.ID))
    assert(isinstance(set_unset, acthex.ID))
    # below: TODO
    assert(all([isinstance(e, str) for e in atom]))
    assert(set_unset in (True, False))
    if set_unset:
      self.atoms.add(atom)
    else:
      self.atoms.remove(atom)

def persistenceSet(atom):
  assert(isinstance(atom, (tuple, str)))
  assert(isinstance(acthex.environment(), PersistenceEnvironment))
  acthex.environment().persistence_set_unset(atom, True)

def persistenceUnset(atom):
  assert(isinstance(atom, (tuple, str)))
  assert(isinstance(acthex.environment(), PersistenceEnvironment))
  acthex.environment().persistence_set_unset(atom, False)

def persistenceByPred(pred):
  assert(isinstance(pred, acthex.ID))
  assert(isinstance(acthex.environment(), PersistenceEnvironment))
  for a in acthex.environment().atoms:
    if a[0] == pred:
      # output tuple with single term containing full atom
      term = '{}({})'.format(a[0], ','.join(a[1:]))
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
    sys.stdout.write('Index: '+['{:3}'.format(x) for x in range(0,MAX)])
    sys.stdout.write('Value: '+['{:3}'.format(x) for x in self.sequence])
    sys.stdout.flush()

def sortSwap(i, j):
  assert(isinstance(i, int))
  assert(isinstance(j, int))
  assert(isinstance(acthex.environment(), SortEnvironment))
  acthex.environment().swap(i, j)

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
def printLine(inputs):
  assert(all([isinstance(x, str) for x in inputs]))
  sys.stdout.write('printLine: "'+' '.join(inputs)+'"\n')
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
