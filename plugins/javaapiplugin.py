import dlvhex
from dlvhex import ID
import hexlite

import logging
import atexit

# this requires jpype to be installed and it requires a working Java runtime environment
import jpype
logging.debug("starting JVM")
jpype.startJVM(convertStrings=False)

# cleanup
def shutdownJVM():
	logging.info("JVM shutdown")
	jpype.shutdownJVM()
logging.debug("registering JVM shutdown")
atexit.register(shutdownJVM)

def logJavaExceptionWithStacktrace(ex):
	logging.error("Java exception: %s", ex.toString())
	st = ex.getStackTrace()
	for ste in st:
		logging.error("\t at %s", ste.toString())
	#sb.append(ex.getClass().getName() + ": " + ex.getMessage() + "\n");

# this loads the hexlite-API-specific classes (probably from hexlite-java-api.jar)
IPluginAtom = jpype.JClass("at.ac.tuwien.kr.hexlite.api.IPluginAtom")
ISolverContext = jpype.JClass("at.ac.tuwien.kr.hexlite.api.ISolverContext")
IAtom = jpype.JClass("at.ac.tuwien.kr.hexlite.api.IAtom")
ISymbol = jpype.JClass("at.ac.tuwien.kr.hexlite.api.ISymbol")
JException = jpype.JClass("java.lang.Exception")

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
	ret = tuple([ MAPTYPE[t] for t in jinputarguments ])
	#logging.debug("XXX converted jinputarguments %s to %s", jinputarguments, ret)
	return ret

@jpype.JImplements(ISymbol)
class JavaSymbolImpl:
	# a JavaSymbolImpl mainly holds a hid (hexlite.ID)
	# (concretely at the moment it always holds a hexlite.clingobackend.ClingoID)
	def __init__(self, hid=None):
		assert(isinstance(hid,ID))
		self.hid = hid
		self.__valuecache = hid.value()
		#logging.info("JavaSymbolImpl with hid %s", repr(self.hid))

	@jpype.JOverride
	def negate(self):
		return JavaSymbolImpl(self.hid.negate())

	@jpype.JOverride
	def value(self):
		return jpype.JString(self.hid.value())

	@jpype.JOverride
	def intValue(self):
		return jpype.JInt(self.hid.intValue())

	@jpype.JOverride
	def isTrue(self):
		return jpype.JBoolean(self.hid.isTrue())

	@jpype.JOverride
	def isFalse(self):
		return jpype.JBoolean(self.hid.isFalse())

	@jpype.JOverride
	def isAssigned(self):
		return jpype.JBoolean(self.hid.isAssigned())

	@jpype.JOverride
	def tuple(self):
		ret = jpype.JClass("java.util.ArrayList")()
		for e in self.hid.tuple():
			ret.add(e)
		return ret

	@jpype.JOverride
	def extension(self):
		ret = jpype.JClass("java.util.ArrayList")()
		for e in self.hid.extension():
			ret.add(e)
		return ret

	@jpype.JOverride
	def hashCode(self):
		return jpype.JInt(hash(self.__valuecache) & 0x7FFFFFFF)

	@jpype.JOverride
	def equals(self, other):
		return jpype.JBoolean(self == other or self.hid == other.hid)

	@jpype.JOverride
	def toString(self):
		return str(self.hid)

@jpype.JImplements(IPluginAtom.IQuery)
class JavaQueryImpl:
	def __init__(self, arguments):
		self.jinputTuple = jpype.JClass("java.util.ArrayList")()
		# each argument is converted from hexlite to a java ISymbol
		# each argument is an ID or a tuple
		# we follow the structure of the argument
		for arg in arguments:
			#logging.debug("argument is %s", repr(arg))
			assert(isinstance(arg, (JavaSymbolImpl,ISymbol)))
			self.jinputTuple.add(arg)

	@jpype.JOverride
	def getInterpretation(self):
		logging.error("TBD")
		return None

	@jpype.JOverride
	def getInput(self):
		return self.jinputTuple


@jpype.JImplements(ISolverContext)
class JavaSolverContextImpl:
	def __init__(self):
		pass

	@jpype.JOverride
	def storeOutputAtom(self, atom):
		logging.error("TBD")
		return jpype.JObject(None, IAtom)

	@jpype.JOverride
	def storeAtom(self, atom):
		logging.error("TBD")
		return None

	@jpype.JOverride
	def storeConstant(self, s):
		# convert to python string, otherwise various string operations done within hexlite will fail on the java strings
		pythonstr = str(s)
		r = jpype.JObject(JavaSymbolImpl(dlvhex.storeConstant(pythonstr)), ISymbol)
		#logging.info("storeConstant returns %s with type %s", repr(r), type(r))
		return r

	@jpype.JOverride
	def storeInteger(self, i):
		return JavaSymbolImpl(dlvhex.storeInteger(s))

	@jpype.JOverride
	def learn(self, nogood):
		logging.error("TBD")

def convertArguments(pyArguments):
	# all ID classes stay the same way
	# all tuples become unfolded (only at the end of the list)
	# this is necessary because we do not want Java to get either Tuple or ISymbol as arguments
	if len(pyArguments) == 0:
		return []

	assert(all([ isinstance(a, ID) for a in pyArguments[:-1] ]))
	assert(isinstance(pyArguments[-1], (ID, tuple)))
	ret = [ JavaSymbolImpl(a) for a in pyArguments[:-1] ]
	if isinstance(pyArguments[-1], ID):
		# convert last element as one
		ret.append( JavaSymbolImpl(pyArguments[-1]) )
	else:
		# extend list from converted list of parts of last element (variable length argument list)
		ret.extend([ JavaSymbolImpl(a) for a in pyArguments[-1] ])
	return ret

class JavaPluginCallWrapper:
	def __init__(self, eatomname, pluginholder, pluginatom):
		self.eatomname = eatomname
		self.pluginholder = pluginholder
		self.pluginatom = pluginatom

	def __call__(self, *arguments):
		try:
			logging.debug("executing java __call__ for %s with %d arguments", self.eatomname, len(arguments))
			jsc = JavaSolverContextImpl()			
			jq = JavaQueryImpl(convertArguments(arguments))
			#logging.info("executing retrieve")
			janswer = self.pluginatom.retrieve(jsc, jq)
			logging.debug("retrieved")
			tt = janswer.getTrueTuples()
			#logging.info("true tuples")
			for t in tt:
				#logging.info("true tuple = %s %s", repr(t), t.toString())
				assert(all([ isinstance(e, JavaSymbolImpl) for e in t ]))
				tupleOfID = tuple([ e.hid for e in t ])
				dlvhex.output(tupleOfID)
		except JException as e:
			logJavaExceptionWithStacktrace(e)
			raise


def register(arguments):
	logging.info("Java API loaded with arguments %s", arguments)	

	global loadedPlugins
	for classname in arguments:
		logging.info("loading Java Plugin %s", classname)
		try:
			jclass = jpype.JClass(classname)
			assert(jclass is not None)
			logging.debug("instantiating Plugin")
			jinst = jclass()
			assert(jinst is not None)
			jholder = JavaPluginHolder(classname, jinst)
			assert(jholder is not None)
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
		except JException as e:
			logJavaExceptionWithStacktrace(e)
			raise

			
	logging.info("loaded %d Java plugins", len(loadedPlugins))
