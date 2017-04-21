#!/usr/bin/python3

import sys, logging
# initially log everything
logging.basicConfig(level=logging.NOTSET, format="%(filename)10s:%(lineno)4d:%(message)s", stream=sys.stderr)

# load rest after configuring logging
import os, argparse, traceback, pprint
import shallowhexparser as shp
import dlvhex

class Plugin:
  def __init__(self, mname, pmodule):
    self.mname = mname
    self.pmodule = pmodule

def flatten(listoflists):
  return [x for y in listoflists for x in y]

def loadPlugin(mname):
  # returns plugin info
  logging.info('loading plugin '+repr(mname))
  pmodule = __import__(mname, globals(), locals(), [], 0)
  logging.info('configuring dlvhex module for registering module '+repr(mname))
  # tell dlvhex module which other module is registering its atoms
  dlvhex.startRegistration(pmodule)
  logging.info('calling register() for '+repr(mname))
  pmodule.register()
  logging.info('list of known atoms is now {}'.format(', '.join(dlvhex.atoms.keys())))
  return Plugin(mname, pmodule)

def loadProgram(hexfiles):
  ret = []
  for f in hexfiles:
    with open(f, 'r') as inf:
      prog = shp.parse(inf.read())
      logging.debug('from file '+repr(f)+' parsed program\n'+pprint.pformat(prog, indent=2, width=250))
      ret += prog
  return ret

def rewrite(program, plugins):
  logging.error('TODO rewrite')
  #"testConcat", (dlvhex.TUPLE,), 1, prop)
  '''
  go over all rules of program
  for each rule find external atoms and handle them with EAtomHandler
  (this can change the rule and create new rules)
  '''
  for statement in program:
    logging.debug('RWR '+pprint.pformat(statement, width=1000)
    eatoms = findExternalAtoms(statement)
    logging.debug('RWR eatoms='+repr(eatoms))
    safeVars = findSafeVariables(statement)
    while len(eatoms) > 0:
      logging.debug('RWR safeVars='+repr(safeVars))
      safeEatm = findSafeExternalAtom(statement, eatoms, safeVars)
      logging.debug('RWR safeEatm='+repr(safeEatm))
      if safeEatm:
        newRules = transformExternalAtomInStatement(statement, safeEatm)
        logging.debug('RWR safeEatm='+repr(safeEatm))
      else:
        break
  return rewritten

def execute(rewritten, plugins):
  logging.error('TODO prepare gringo context')
  logging.error('TODO ground with gringo context')
  logging.error('TODO prepare propagator')
  logging.error('TODO run with clingo API and propagator')
  logging.error('TODO transform answer sets and return')
  return code


class EAtomHandlerBase:
  def __init__(self, holder):
    assert(isinstance(holder, dlvhex.ExternalAtomHolder))
    self.holder = holder

class NoOutputEAtomHandler(EAtomHandlerBase):
  def __init__(self, holder):
    EAtomHandlerBase.__init__(self, holder)

class ConstantInputEAtomHandler(EAtomHandlerBase):
  def __init__(self, holder):
    EAtomHandlerBase.__init__(self, holder)

def classifyExternalAtoms():
  '''
  For now we can only handle the following:
  * NoOutputEAtomHandler:
    external atom has no output and arbitrary input
    -> we transform this atom into an input/guessing rule as in dlvhex2
    -> we use a propagator to evaluate during solving
  * ConstantInputEAtomHandler:
    external atom has only constant/tuple input(s)
    -> we transform this atom into a gringo external
    -> we do not (need to) consider it during solving
  '''
  for name, holder in dlvhex.atoms.items():
    # uses ConstantInputEAtomHandler if possible (even if output is 0)
    # (external atom functions cannot change during evaluation,
    # hence it is safe to evaluate these atoms in grounding)
    inspec_types = set(holder.inspec)
    if dlvhex.PREDICATE not in inspec_types:
      holder.executionHandler = ConstantInputEAtomHandler(holder)
    elif holder.outnum == 0:
      holder.executionHandler = NoOutputEAtomHandler(holder)
    else:
      raise Exception("cannot handle external atom '{}' from plugin '{}' because of input signature {} and nonempty ({}) output signature (please use dlvhex2)".format(
        name, holder.module.__name__, repr(dlvhex.humanReadableSpec(holder.inspec)), holder.outnum))

def interpretArguments(argv):
  parser = argparse.ArgumentParser(
    description='HEX-Lite - Answer Set Solver for fragment of the HEX formalism')
  parser.add_argument('hexfiles', nargs='+', metavar='HEXFILE', action='append', default=[],
    help='Filename(s) of HEX source code.')
  parser.add_argument('--pluginpath', nargs='*', metavar='PATH', action='append', default=[],
    help='Paths to search for python modules.')
  parser.add_argument('--plugin', nargs='*', metavar='MODULE', action='append', default=[],
    help='Names of python modules to load as external atoms.')
  parser.add_argument('--verbose', action='store_true', default=False, help='Activate verbose mode.')
  parser.add_argument('--debug', action='store_true', default=False, help='Activate debugging mode.')
  args = parser.parse_args(argv)
  setupLogging(args)
  logging.debug('args='+repr(args))
  return args

def setupLogging(args):
  level = logging.WARNING
  if args.verbose:
    level=logging.INFO
  if args.debug:
    level=logging.DEBUG
  # call only once
  logging.getLogger().setLevel(level)
  
def main():
  try:
    args = interpretArguments(sys.argv[1:])
    setPaths(flatten(args.pluginpath))
    plugins = loadPlugins(flatten(args.plugin))
    program = loadProgram(flatten(args.hexfiles))
    rewritten = rewrite(program, plugins)
    code = execute(rewritten, plugins)
    return code
  except:
    logging.error('Exception: '+traceback.format_exc())
    return -1

def loadPlugins(plugins):
  ret = []
  for p in plugins:
    pi = loadPlugin(p)
    logging.debug('for plugin '+p+' got plugin info '+repr(pi))
    ret.append(pi)
  classifyExternalAtoms()
  return ret

def setPaths(paths):
  for p in paths:
    sys.path.append(p)
  logging.info('sys.path='+repr(sys.path))

if __name__ == '__main__':
  main()
