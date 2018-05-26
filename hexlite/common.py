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
import logging
import argparse

class Configuration:
  def __init__(self):
    # whether to produce verbose output
    self.verbose = False
    # whether to produce debug output
    self.debug = False
    # maxint setting (for compatibility with dlvhex, actually not necessary here)
    self.maxint = 0
    # which type of FLP check to use, or 'none'
    self.flpcheck = 'explicit'
    # number of answer sets to enumerate (0 = all)
    self.number = 0
    # whether to suppress facts in output
    self.nofacts = False
    # whether to give auxiliary facts in output
    self.auxfacts = False

  def add_common_arguments(self, parser):
    assert(isinstance(parser, argparse.ArgumentParser))
    parser.add_argument('--liberalsafety', action='store_true', default=False,
      help='Whether liberal safety is requested (ignored).')
    parser.add_argument('--strongnegation-enable', action='store_true', default=False,
      help='Whether strong negation is enabled (ignored).')
    parser.add_argument('--flpcheck', choices=['explicit', 'none'], action='store', default='explicit',
      help='Which type of FLP check to use (explicit FLP check currently does not work for strong negation and optimization).')
    parser.add_argument('-n', '--number', metavar='N', action='store', default=0,
      help='Number of models to enumerate.')
    parser.add_argument('-N', '--maxint', metavar='N', action='store', default=None,
      help='Maximum integer (#maxint in the program can override this).')
    parser.add_argument('--nofacts', action='store_true', default=False,
      help='Whether to output given facts in answer set.')
    parser.add_argument('--auxfacts', action='store_true', default=False,
      help='Whether to output auxiliary facts in answer set.')
    parser.add_argument('--verbose', action='store_true', default=False, help='Activate verbose mode.')
    parser.add_argument('--debug', action='store_true', default=False, help='Activate debugging mode.')

  def setupLogging(self):
    level = logging.WARNING
    if self.verbose:
      level = logging.INFO
    if self.debug:
      level = logging.DEBUG
    # call only once
    logging.getLogger().setLevel(level)

  def process_arguments(self, args):
    self.verbose = args.verbose
    self.debug = args.debug
    self.setupLogging()
    if args.liberalsafety:
      logging.warning("ignored argument about liberal safety")
    if args.strongnegation_enable:
      logging.warning("ignored argument about strong negation")
    try:
      if args.maxint:
        self.maxint = int(args.maxint)
    except:
      raise ValueError("faulty maxint argument '{}'".format(args.maxint))
    if self.flpcheck not in ['explicit', 'none']:
      raise ValueError("invalid flpcheck setting '{}'".format(self.flpcheck))
    self.flpcheck = args.flpcheck
    try:
      if args.number:
        self.number = int(args.number)
    except:
      raise ValueError("faulty number argument '{}'".format(args.number))
    self.nofacts = args.nofacts
    self.auxfacts = args.auxfacts

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
