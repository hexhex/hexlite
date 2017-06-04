# encoding: utf8
# This module provides common data structure for the Clingo backend.

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

# assume that the main program has handled possible import problems
import clingo

class ClaspContext:
  '''
  context within the propagator
  '''
  def __init__(self):
    self.propcontrol = None
  def __call__(self, control):
    '''
    initialize context with control object
    '''
    assert(self.propcontrol == None)
    assert(control != None)
    self.propcontrol = control
    return self
  def __enter__(self):
    pass
  def __exit__(self, type, value, traceback):
    self.propcontrol = None

class SymLit:
  '''
  Holds the symbol of a symbolic atom of Clingo plus its solver literal.

  x <- init.symbolic_atoms.by_signature
  sym <- x.symbol
  lit <- init.solver_literal(x.literal)
  '''
  def __init__(self, sym, lit):
    self.sym = sym
    self.lit = lit

class ClingoID:
  # the ID class as passed to plugins, from view of Clingo backend
  def __init__(self, ccontext, symlit):
    assert(isinstance(ccontext, ClaspContext))
    self.ccontext = ccontext
    self.symlit = symlit
    self.__value = str(symlit.sym)

  def value(self):
    return self.__value

  def intValue(self):
    if self.symlit.sym.type == clingo.SymbolType.Number:
      return self.symlit.sym.number
    else:
      raise Exception('intValue called on ID {} which is not a number!'.format(self.__value))

  def isTrue(self):
    if not self.symlit.lit:
      raise Exception("cannot call isTrue on term that is not an atom")
    return self.__assignment().is_true(self.symlit.lit)

  def isFalse(self):
    if not self.symlit.lit:
      raise Exception("cannot call isFalse on term that is not an atom")
    return self.__assignment().is_false(self.symlit.lit)

  def isAssigned(self):
    if not self.symlit.lit:
      raise Exception("cannot call isAssigned on term that is not an atom")
    return self.__assignment().value(self.symlit.lit) != None

  def tuple(self):
    tup = tuple([ ClingoID(self.ccontext, SymLit(sym, None)) for sym in
                  [clingo.Function(self.symlit.sym.name)]+self.symlit.sym.arguments])
    return tup

  def __assignment(self):
    return self.ccontext.propcontrol.assignment

  def __str__(self):
    return self.__value

  def __repr__(self):
    return "ClingoID({})".format(str(self))

  def __getattr__(self, name):
    raise Exception("not (yet) implemented: ClingoID.{}".format(name))
