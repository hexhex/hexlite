# encoding: utf8
# This module provides shared datastructures for the hexlite engine.

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

import sys, time, collections, logging, argparse, json

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
    # whether to output stats as json lines on stderr
    self.stats = False
    # whether to enable a generic cache for external atom calls
    self.enable_generic_eatom_cache = True
    # whether to enable nogoods specified by external atoms (if false, these nogoods are just ignored)
    self.enable_eatom_specified_nogoods = True
    # whether to check before external atom evaluations if a nogood determines the result, and if yes, skip the evaluation
    self.consider_skipping_evaluation_if_nogood_determines_truth = True
    # additional arguments for backend (currently directly given to clingo)
    self.backend_additional_args = []

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
    parser.add_argument('--backend_arg', nargs=1, metavar='ARGUMENT', action='append', default=[],
      help='Argument to pass to backend. Can be given multiple times to pass multiple arguments.')
    parser.add_argument('--nocache', action='store_true', default=False,
      help='Disable caching of external atom calls.')
    parser.add_argument('--noeatomlearn', action='store_true', default=False,
      help='Disable processing of nogoods that are generated by external computations.')
    parser.add_argument('--noskipevalfromnogoods', action='store_true', default=False,
      help='Disable skipping of external evaluation based on existing nogoods provided by the external computation. (Use this if you are not sure if eatom nogoods mess up the search space.)')
    parser.add_argument('--dump-grounding', action='store_true', default=False, help='Dump the ground program to STDERR.')
    parser.add_argument('--verbose', action='store_true', default=False, help='Activate verbose mode.')
    parser.add_argument('--debug', action='store_true', default=False, help='Activate debugging mode.')
    parser.add_argument('--stats', action='store_true', default=False, help='Activate statistics output as JSON on stdout.')

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
    self.dump_grounding = args.dump_grounding
    self.debug = args.debug
    self.stats = args.stats
    self.setupLogging()
    self.backend_additional_args = args.backend_arg
    if len(self.backend_additional_args) > 0:
      logging.info("passing additional arguments to backend: "+repr(self.backend_additional_args))
    if args.liberalsafety:
      logging.warning("ignored argument about liberal safety")
    if args.strongnegation_enable:
      logging.warning("ignored argument about strong negation")
    if args.nocache:
      self.enable_generic_eatom_cache = False
    if args.noeatomlearn:
      self.enable_eatom_specified_nogoods = False
    if args.noskipevalfromnogoods:
      self.consider_skipping_evaluation_if_nogood_determines_truth = False
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
  def __init__(self, mname, pmodule, arguments=None):
    self.mname = mname
    self.pmodule = pmodule
    self.arguments = arguments

  def teardown(self):
    if hasattr(self.pmodule, 'teardown'):
      self.pmodule.teardown()

class Statistics:
  '''
  collect statistics (real time, cpu time, counter) in categories
  '''
  def __init__(self):
    self.initial = time.perf_counter(), time.process_time()
    # accumulation of times and counts used in certain categories (real time, cpu time, counter)
    self.categories = collections.defaultdict(lambda: [0.0, 0.0, 0])
    # sequence of categories currently being benchmarked
    # each nesting creates another entry at the end
    self.statstack = [ 'all' ]
    # latest time taken
    self.latest = self.initial

  # not to be used from outside
  def _timestamp(self, addtocategory, increment):
    current = time.perf_counter(), time.process_time()
    for i in [0, 1]:
      self.categories[addtocategory][i] += current[i] - self.latest[i]
    if increment:
      self.categories[addtocategory][2] += 1
    self.latest = current

  # not to be used from outside
  class _Closure:
    def __init__(self, stats, category):
      self.stats = stats
      self.category = category

    def __enter__(self):
      # count time difference to last timestamp for statstack [-1]
      self.stats._timestamp(self.stats.statstack[-1], increment=False)
      # add element to statstack
      self.stats.statstack.append(self.category)

    def __exit__(self, exc_type, exc_value, exc_tb):
      assert(self.stats.statstack[-1] == self.category)
      # count time difference to last timestamp for statstack [-1] and increment counter (for leaving the closure)
      self.stats._timestamp(self.stats.statstack[-1], increment=True)
      # remove element from statstack
      self.stats.statstack.pop()

  # do "with stats.context('category'): ..." (nesting is OK)
  def context(self, categoryname):
    return Statistics._Closure(self, categoryname)

  def accumulate(self):
    # accumulate some categories
    eatoms = [ v for k,v in self.categories.items() if k.startswith('eatom') ]
    return {
      'all.real': sum([ v[0] for v in self.categories.values() ]),
      'all.cpu': sum([ v[1] for v in self.categories.values() ]),

      'eatoms.real': sum([ v[0] for v in eatoms ]),
      'eatoms.cpu': sum([ v[1] for v in eatoms ]),
      'eatoms.count': sum([ v[2] for v in eatoms ]),
    }

  def display(self, name):
    # count time difference to last timestamp for statstack[-1] and also count this once
    self._timestamp(self.statstack[-1], increment=True)
    # accumulate stats
    accum = self.accumulate()
    # print stats
    sys.stderr.write(json.dumps({ 'event':'stats', 'name':name, 'stack': self.statstack, 'categories': dict(self.categories), 'accumulated': accum })+'\n')
    sys.stderr.flush()
    # decrement again in case we display() multiple times
    self.categories[self.statstack[-1]][2] -= 1

# statistics class that does nothing
class StatisticsDummy:
  def __init__(self):
    pass
  class _Closure:
    def __init__(self):
      pass
    def __enter__(self):
      pass
    def __exit__(self, exc_type, exc_value, exc_tb):
      pass
  
  def context(self, categoryname):
    return StatisticsDummy._Closure()
  def display(self, name):
    pass

class ProgramContext:
  '''
  program-global context
  * collects external atom signatures
  * remembers if maxint is given by program or by commandline
  * holds statistics
  '''
  def __init__(self):
    # key = eatomname, value = list of SignatureInfo
    self.eatoms = collections.defaultdict(set)
    self.wroteMaxint = False
    self.stats = StatisticsDummy()

  def addSignature(self, eatomname, relevancePred, replacementPred, arity):
   self.eatoms[eatomname].add(
      self.SignatureInfo(relevancePred, replacementPred, arity))

  class SignatureInfo:
    def __init__(self, relevancePred, replacementPred, arity):
      self.relevancePred = relevancePred
      self.replacementPred = replacementPred
      self.arity = arity

    def __hash__(self):
      return hash( (self.relevancePred, self.replacementPred, self.arity) )

    def __eq__(self, other):
      return (self.relevancePred == other.relevancePred) and (self.replacementPred == other.replacementPred) and (self.arity == other.arity)

    def __repr__(self):
      return str(self)

    def __str__(self):
      return "SignatureInfo(rel={},repl={},arity={})".format(self.relevancePred, self.replacementPred, self.arity)

def flatten(listoflists):
  return [x for y in listoflists for x in y]
