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

class JavaPluginHolder:
	def __init__(self, classname, jplugin):
		self.classname = classname
		self.jplugin = jplugin

loadedPlugins = []

def convertExtSourceProperties(jesp):
	# convert only those parts that are implemented in hexlite
	ret = dlvhex.ExtSourceProperties()
	ret.setProvidesPartialAnswer(jesp.getProvidesPartialAnswer())
	return ret

MAPTYPE = {
		IPluginAtom.InputType.PREDICATE: dlvhex.PREDICATE,
		IPluginAtom.InputType.CONSTANT: dlvhex.CONSTANT,
		IPluginAtom.InputType.TUPLE: dlvhex.TUPLE,
	}
def convertInputArguments(jinputarguments):
	return tuple([ MAPTYPE[t] for t in jinputarguments ])

class JavaPluginCallWrapper:
	def __init__(self, eatomname, pluginholder, pluginatom):
		self.eatomname = eatomname
		self.pluginholder = pluginholder
		self.pluginatom = pluginatom

	def __call__(self, *arguments):
		logging.warning("TODO implement __call__ for %s", self.eatomname)

def register(arguments):
	logging.info("Java API loaded with arguments %s", arguments)	

	global loadedPlugins
	for classname in arguments:
		logging.info("loading Java Plugin %s", classname)
		jclass = jpype.JClass(classname)
		logging.debug("instantiating Plugin")
		jinst = jclass()
		jholder = JavaPluginHolder(classname, jinst)
		loadedPlugins.append(jholder)
		logging.info("registering atoms of plugin %s with name %s", classname, jinst.getName())
		for jpluginatom in jholder.jplugin.createAtoms():
			pred = str(jpluginatom.getPredicate())
			inputArguments = jpluginatom.getInputArguments()
			outputArguments = jpluginatom.getOutputArguments()
			jesp = jpluginatom.getExtSourceProperties()
			prop = convertExtSourceProperties(jesp)
			if pred in globals():
				logging.error("trying to override '%s' in globals - duplicate external atom name or conflict with python internal names", pred)
			else:
				globals()[pred] = JavaPluginCallWrapper(pred, jholder, jpluginatom)
				dlvhex.addAtom(pred, convertInputArguments(inputArguments), int(outputArguments), prop)
			
	logging.info("loaded %d Java plugins", len(loadedPlugins))
