import sys, os, logging, traceback

def setupLoggingBase():
  # initially log everything
  logging.basicConfig(
    level=15, stream=sys.stderr,
    format="%(levelname)1s:%(filename)10s:%(lineno)3d:%(message)s")
  # make log level names shorter so that we can show them
  logging.addLevelName(50, 'C')
  logging.addLevelName(40, 'E')
  logging.addLevelName(30, 'W')
  logging.addLevelName(20, 'I')
  logging.addLevelName(10, 'D')

def importClingoAPI():
  # clingo python API
  try:
    # try to import global clingo package
    logging.debug("attempting global clingo import with path %s", sys.path)
    import clingo
  except ImportError:
    logging.debug("Global clingo import:"+traceback.format_exc())
    # try in ~/.hexlite/
    try:
      sys.path.append(os.path.expanduser('~/.hexlite/'))
      import clingo
    except ImportError:
      logging.debug("Local clingo import:"+traceback.format_exc())
      logging.warning("Could not find clingo python module in global or local (~/.hexlite/) installation.")
      import hexlite.buildclingo as bcm
      if not bcm.build():
        logging.critical("Could not install clingo python module. Please retry or install manually and retry running hexlite.")
        sys.exit(-1)
    # now it should work
    try:
      # add a NEW path (non-existence of clingo module seems to be cached)
      sys.path.append(os.path.expanduser('~/.hexlite//'))
      import clingo
    except ImportError:
      logging.debug("Clingo build:"+traceback.format_exc())
      logging.critical("Installed clingo python module but cannot import it. Please report this to the developers.")
      sys.exit(-1)

  # import these after importing clingo, because it requires clingo too
  import hexlite.clingobackend
