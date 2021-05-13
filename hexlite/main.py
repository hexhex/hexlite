#!/usr/bin/env python3

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

import sys
import platform

if platform.python_version().startswith('2'):
  sys.stdout.write("Please use Python 3 instead of Python 2!\n")
  sys.exit(-1)

import hexlite.app as app
app.setupLoggingBase()

# load rest after configuring logging
import hexlite
import hexlite.rewriter as rewriter
import hexlite.ast.shallowparser as shp
import hexlite.ast as ast
from hexlite.modelcallback import StandardModelCallback

# this is our own package for communicating with plugins
import dlvhex

# other things we need here
import os, argparse, traceback, pprint, logging

def loadPlugin(pluginarray):
  # returns plugin info
  logging.info('loading plugin '+repr(pluginarray))
  mname = pluginarray[0]
  arguments = None
  if len(pluginarray) > 1:
    arguments = pluginarray[1:]
  logging.info('module {} with arguments {}'.format(mname, arguments))
  pmodule = __import__(mname, globals(), locals(), [], 0)
  logging.info('configuring dlvhex module for registering module '+repr(mname))
  # tell dlvhex module which other module is registering its atoms
  dlvhex.startRegistration(pmodule)
  logging.info('calling register() for '+repr(mname))
  if arguments:
    pmodule.register(arguments)
  else:
    pmodule.register()
  def briefInfo(name, holder):
    return "{}/{}/{}".format(name, dlvhex.humanReadableSpec(holder.inspec), holder.outnum)
  logging.info('list of known atoms is now {}'.format(', '.join(
    [ briefInfo(name, holder) for name, holder in dlvhex.eatoms.items() ])))
  return hexlite.Plugin(mname, pmodule, arguments)

def loadProgram(hexfiles):
  ret = []
  for f in hexfiles:
    with open(f, 'r') as inf:
      prog = shp.parse(inf.read())
      logging.debug('from file '+repr(f)+' parsed program\n'+pprint.pformat(prog, indent=2, width=250))
      ret += prog
  return ret

def interpretArguments(argv, config):
  parser = argparse.ArgumentParser(
    description='HEX-Lite - Answer Set Solver for fragment of the HEX formalism')
  parser.add_argument('hexfiles', nargs='+', metavar='HEXFILE', action='append', default=[],
    help='Filename(s) of HEX source code.')
  parser.add_argument('--pluginpath', nargs='*', metavar='PATH', action='append', default=[],
    help='Paths to search for python modules.')
  parser.add_argument('--plugin', nargs='+', metavar=('MODULENAME', 'ARGUMENT'), action='append', default=[],
    help='Python module to load as plugin, plus optional arguments for plugin. Can be given multiple times to load multiple plugins.')
  config.add_common_arguments(parser)
  args = parser.parse_args(argv)
  config.process_arguments(args)
  return args

def setPaths(paths):
  for p in paths:
    sys.path.append(p)
  logging.info('sys.path='+repr(sys.path))

def loadPlugins(plugins):
  ret = []
  for p in plugins:
    pi = loadPlugin(p)
    logging.debug('for plugin {} got plugin info {}'.format(pi.mname, repr(pi)))
    ret.append(pi)
  return ret

def teardownPlugins(plugins):
  for p in plugins:
    p.teardown()

def main():
  code = 1
  try:
    config = hexlite.Configuration()
    args = interpretArguments(sys.argv[1:], config)
    # import API here to fail early if clingo module does not exist
    app.importClingoAPI()
    # now set additional paths for plugin imports
    setPaths(hexlite.flatten(args.pluginpath))
    plugins = loadPlugins(args.plugin)
    program = loadProgram(hexlite.flatten(args.hexfiles))
    pcontext = hexlite.ProgramContext()
    if config.stats:
      pcontext.stats = hexlite.Statistics()
      # (per default, a dummy that does nothing is used)
    with pcontext.stats.context('rewriting'):
      rewriter.classifyEAtomsInstallRewritingHandlers(pcontext)
      pr = rewriter.ProgramRewriter(pcontext, program, plugins, config)
      rewritten, facts = pr.rewrite()
    stringifiedFacts = frozenset(ast.normalizeFacts(facts))
    modelcbs = None
    if len(dlvhex.modelCallbacks) > 0:
      # instantiate model callbacks
      modelcbs = [ cb(stringifiedFacts, config) for cb in dlvhex.modelCallbacks ]
    else:
      modelcbs = [StandardModelCallback(stringifiedFacts, config)]
    solvecode = hexlite.clingobackend.execute(pcontext, rewritten, facts, plugins, config, modelcbs)
    # ignore code as dlvhex does
    code = 0
    pcontext.stats.display('final')
    teardownPlugins(plugins)
  except SystemExit:
    pass
  except:
    logging.error('Exception: '+traceback.format_exc())
    logging.error('For reporting bugs, unexpected behavior, or suggestions, please report an issue here: '+'https://github.com/hexhex/hexlite/issues')
  sys.exit(code)

if __name__ == '__main__':
  main()

# vim:expandtab:
