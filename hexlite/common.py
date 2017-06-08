# encoding: utf8
# This module provides shared datastructures for the hexlite engine.

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

import collections


class Plugin:
  def __init__(self, mname, pmodule):
    self.mname = mname
    self.pmodule = pmodule


class ProgramContext:
  '''
  program-global context
  collects external atom signatures
  remembers if maxint is given by program or by commandline
  '''
  def __init__(self):
    # key = eatomname, value = list of SignatureInfo
    self.eatoms = collections.defaultdict(list)
    self.wroteMaxint = False
  def addSignature(self, eatomname, relevancePred, replacementPred, arity):
    self.eatoms[eatomname].append(
      self.SignatureInfo(relevancePred, replacementPred, arity))

  class SignatureInfo:
    def __init__(self, relevancePred, replacementPred, arity):
      self.relevancePred = relevancePred
      self.replacementPred = replacementPred
      self.arity = arity


def flatten(listoflists):
  return [x for y in listoflists for x in y]
