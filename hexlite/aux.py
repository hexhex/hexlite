# encoding: utf8
#
# This module provides constants for auxiliaries used in auxiliary programs.
#

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

class Aux:
  # prefix for all auxiliaries [just rename in case of conflicts in an application]
  PREFIX = 'aux_'

  # maxint
  MAXINT = PREFIX+'maxint'

  # relevance of external atoms + input tuple grounding
  EAREL = PREFIX+'r'
  # truth of external atoms (in the papers "external replacement atoms")
  EAREPL = PREFIX+'t'

  # auxiliary for rule heads in explicitflpcheck.RuleActivityProgram
  RHPRED = PREFIX+'h'

  # for explicitflpcheck.CheckOptimizedProgram
  # auxilary for unnamed clasp atoms
  CLATOM = PREFIX+'C'
  # auxiliary for atoms in compatible set
  CSATOM = PREFIX+'c'
  # auxiliary for atoms in choice heads 
  CHATOM = PREFIX+'H'
  # auxiliary for smaller atom
  SMALLER = PREFIX+'smaller'

def predEAtomRelevance(arity, eatomname):
  return Aux.EAREL+'_'+str(arity)+'_'+eatomname

def predEAtomTruth(arity, eatomname):
  return Aux.EAREPL+'_'+str(arity)+'_'+eatomname
