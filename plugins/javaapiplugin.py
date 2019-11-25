import dlvhex

import logging
import atexit

# this requires jpype to be installed and it requires a working Java runtime environment
import jpype
logging.debug("starting JVM")
jpype.startJVM(convertStrings=False)

# cleanup
logging.debug("registering JVM shutdown")
atexit.register(lambda: jpype.shutdownJVM())

# this loads the hexlite-API-specific classes (probably from hexlite-java-api.jar)
IPluginAtom = jpype.JClass("at.ac.tuwien.kr.hexlite.api.IPluginAtom")
ISolverContext = jpype.JClass("at.ac.tuwien.kr.hexlite.api.ISolverContext")
IAtom = jpype.JClass("at.ac.tuwien.kr.hexlite.api.IAtom")
ISymbol = jpype.JClass("at.ac.tuwien.kr.hexlite.api.ISymbol")

def register(arguments):
	logging.info("JAVA API loaded with arguments %s", arguments)
