# This module handles evaluation of external atoms via plugins.

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

# assume that the main program has handled possible import problems
import clingo

from .clingocommon import ClaspContext, SymLit, ClingoID

import dlvhex

class EAtomEvaluator:
  '''
  Clingo-backend-specific evaluation of external atoms implemented in Python
  using the same API as in the dlvhex solver (but fully realized in Python).

  This closely interacts with the dlvhex package.
  '''
  def __init__(self, claspcontext):
    assert(isinstance(claspcontext, ClaspContext))
    self.ccontext = claspcontext

  def clingo2hex(self, term):
    assert(isinstance(term, clingo.Symbol))
    #logging.debug("convertClingoToHex got {} with type {}".format(repr(term), term.type))
    return ClingoID(self.ccontext, SymLit(term, None))
    #if term.type is clingo.SymbolType.Number:
    #  ret = term.number
    #elif term.type in [clingo.SymbolType.String, clingo.SymbolType.Function]:
    #  ret = str(term)
    #else:
    #  raise Exception("cannot convert clingo term {} of type {} to external atom term!".format(
    #    repr(term), str(term.type)))
    #return ret

  def hex2clingo(self, term):
    if isinstance(term, ClingoID):
      return term.symlit.sym
    elif isinstance(term, str):
      if term[0] == '"':
        ret = clingo.String(term[1:-1])
      else:
        ret = clingo.parse_term(term)
    elif isinstance(term, int):
      ret = clingo.Number(term)
    else:
      raise Exception("cannot convert external atom term {} to clingo term!".format(repr(term)))
    return ret


  def evaluate(self, holder, inputtuple, predicateinputatoms):
    '''
    Convert input tuple (from clingo to dlvhex) and call external atom semantics function.
    Convert output tuple (from dlvhex to clingo).

    * converts input tuple for execution
    * prepares dlvhex.py for execution
    * executes
    * converts output tuples
    * cleans up
    * return result
    '''
    out = None
    dlvhex.startExternalAtomCall(predicateinputatoms)
    try:
      # prepare input tuple
      plugin_arguments = []
      for spec_idx, inp in enumerate(holder.inspec):
        if inp in [dlvhex.PREDICATE, dlvhex.CONSTANT]:
          arg = self.clingo2hex(inputtuple[spec_idx])
          plugin_arguments.append(arg)
        elif inp == dlvhex.TUPLE:
          if (spec_idx + 1) != len(holder.inspec):
            raise Exception("got TUPLE type which is not in final argument position")
          # give all remaining arguments as one tuple
          args = [ self.clingo2hex(x) for x in inputtuple[spec_idx:] ]
          plugin_arguments.append(tuple(args))
        else:
          raise Exception("unknown input type "+repr(inp))

      # call external atom in plugin
      logging.debug('calling plugin eatom with arguments '+repr(plugin_arguments))
      holder.func(*plugin_arguments)
      
      # interpret output
      # list of tuple of terms (maybe empty tuple)
      out = [ tuple([ self.hex2clingo(val) for val in _tuple ]) for _tuple in dlvhex.currentOutput ]
    finally:
      dlvhex.cleanupExternalAtomCall()
    return out

