#!/usr/bin/env python3

# HEXLite-based solver for a fragment of the ActHEX language
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

import sys
import platform
import itertools

if platform.python_version().startswith('2'):
  sys.stdout.write("Please use Python 3 instead of Python 2!\n")
  sys.exit(-1)

import hexlite.app as app
app.setupLoggingBase()

# load rest after configuring logging
import hexlite
import hexlite.ast.shallowparser as shp
import hexlite.ast as ast
import hexlite.rewriter
import hexlite.modelcallback as modelcallback

# this is our own package for communicating with plugins
import dlvhex
import acthex
import acthex.rewriter
import acthex.actionmanager

# other things we need here
import os, argparse, traceback, pprint, logging

def loadPlugin(mname):
  # returns plugin info
  logging.info('loading plugin '+repr(mname))
  pmodule = __import__(mname, globals(), locals(), [], 0)
  logging.info('configuring acthex/dlvhex module for registering module '+repr(mname))
  # tell dlvhex module which other module is registering its atoms
  dlvhex.startRegistration(pmodule)
  logging.info('calling register() for '+repr(mname))
  pmodule.register()
  def briefInfo(name, holder):
    return "{}/{}/{}".format(name, dlvhex.humanReadableSpec(holder.inspec), holder.outnum)
  logging.info('list of known atoms is now {}'.format(', '.join(
    [ briefInfo(name, holder) for name, holder in dlvhex.eatoms.items() ])))
  def briefActionInfo(name, holder):
    return "{}/{}".format(name, dlvhex.humanReadableSpec(holder.inspec))
  logging.info('list of known actions is now {}'.format(', '.join(
    [ briefActionInfo(name, holder) for name, holder in acthex.actions.items() ])))
  return hexlite.Plugin(mname, pmodule)

def loadProgram(acthexfiles):
  ret = []
  for f in acthexfiles:
    with open(f, 'r') as inf:
      prog = shp.parse(inf.read())
      logging.debug('from file '+repr(f)+' parsed program\n'+pprint.pformat(prog, indent=2, width=250))
      ret += prog
  return ret

def interpretArguments(argv, config):
  parser = argparse.ArgumentParser(
    description='Acthex-Lite - Solver for a fragment of the ACTHEX formalism')
  parser.add_argument('acthexfiles', nargs='+', metavar='ACTHEXFILE', action='append', default=[],
    help='Filename(s) of ACTHEX source code.')
  parser.add_argument('--pluginpath', nargs='*', metavar='PATH', action='append', default=[],
    help='Paths to search for python modules.')
  parser.add_argument('--plugin', nargs='*', metavar='MODULE', action='append', default=[],
    help='Names of python modules to load as external atoms and actions (hexlite or acthex plugins).')
  parser.add_argument('--hidemodels', action='store_true', default=False,
    help='Do not print models encountered in each evaluation step.')
  config.add_common_arguments(parser)
  args = parser.parse_args(argv)
  if args.debug:
    logging.debug('args='+repr(args))
  config.process_arguments(args)
  # TODO derive acthex.Configuration from hexlite.Configuration?
  config.hidemodels = args.hidemodels
  return args

def setPaths(paths):
  for p in paths:
    sys.path.append(p)
  logging.info('sys.path='+repr(sys.path))

def loadPlugins(plugins):
  ret = []
  for p in plugins:
    pi = loadPlugin(p)
    logging.debug('for plugin '+p+' got plugin info '+repr(pi))
    ret.append(pi)
  return ret

class ActhexModelCallback(modelcallback.StandardModelCallback):
  def __init__(self, stringifiedFacts, config):
    modelcallback.StandardModelCallback.__init__(self, stringifiedFacts, config)
    self.optimal_model = None

  def __call__(self, model):
    assert(isinstance(model, dlvhex.Model))
    if not model.is_optimal:
      logging.info('not using suboptimal model (like dlvhex2)!')
      return
    logging.info('found optimal model!')
    # TODO call standard callback (=print model) depending on config
    if not self.config.hidemodels:
      modelcallback.StandardModelCallback.__call__(self, model)
    # remember optimal model and stop enumeration
    self.optimal_model = model
    raise modelcallback.StopModelEnumerationException()

def main():
  code = 1
  try:
    config = hexlite.Configuration()
    args = interpretArguments(sys.argv[1:], config)
    # import API here to fail early if clingo module does not exist
    app.importClingoAPI()
    # now set additional paths for plugin imports
    setPaths(hexlite.flatten(args.pluginpath))
    plugins = loadPlugins(hexlite.flatten(args.plugin))
    program = loadProgram(hexlite.flatten(args.acthexfiles))
    pcontext = hexlite.ProgramContext()
    if config.stats:
      pcontext.stats = hexlite.Statistics()
      # (per default, a dummy that does nothing is used)
    with pcontext.stats.context('rewriting'):
      hexlite.rewriter.classifyEAtomsInstallRewritingHandlers(pcontext)
      pr = acthex.rewriter.ProgramRewriter(pcontext, program, plugins, config)
      rewritten, facts = pr.rewrite()
    stringifiedFacts = frozenset(ast.normalizeFacts(facts))
    try:
      for iteration in itertools.count():
        logging.info("acthex iteration %d", iteration)
        envstr = str(acthex.environment())
        if len(envstr) > 0:
          sys.stdout.write("Environment: "+envstr+'\n')
        # evaluate program, collect answer set in callback
        acthexcallback = ActhexModelCallback(stringifiedFacts, config)
        callbacks = [ acthexcallback ]
        if len(dlvhex.modelCallbacks) > 0:
          # additional model callbacks
          callbacks += [ cb(stringifiedFacts, config) for cb in dlvhex.modelCallbacks ]
        solvecode = hexlite.clingobackend.execute(pcontext, rewritten, facts, plugins, config, callbacks)
        # find and execute actions on environment
        with pcontext.stats.context('executing actions'):
          acthex.actionmanager.executeActions(acthexcallback.optimal_model)
    except acthex.IterationExit:
      logging.info("got acthex iteration exit exception")
    # ignore code as dlvhex does
    code = 0
    pcontext.stats.display('final')
  except SystemExit:
    pass
  except:
    logging.error('Exception: '+traceback.format_exc())
    logging.error('For reporting bugs, unexpected behavior, or suggestions, please report an issue here: '+'https://github.com/hexhex/hexlite/issues')
  sys.exit(code)

if __name__ == '__main__':
  main()

# vim:expandtab:
