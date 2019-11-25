import dlvhex

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


@jpype.JImplements(ISymbol)
class JavaSymbolImpl:
	def __init__(self, type_, tuple_=None, integer=None):
		# e.g. type_ = ISymbol.Type.CONSTANT
		# e.g. content = "foo"
		self.type_ = type_
		self.tuple_ = tuple_
		self.integer = integer
		assert(self.type_ == ISymbol.Type.INTEGER or self.integer is None) # if not integer then integer is none
		assert(not self.type_ == ISymbol.Type.INTEGER or self.tuple_ is None) # if integer then tuple is none
		assert(self.type_ == ISymbol.Type.INTEGER or self.tuple_ is not None) # if not an integer then there is a tuple
		assert(not self.type_ == ISymbol.Type.CONSTANT or (self.tuple_ is not None and len(self.tuple_) == 1)) # if constant then tuple has length 1

	@jpype.JOverride
	def getType(self):
		return self.type_

	@jpype.JOverride
	def getName(self):
		assert(self.type_ == ISymbol.Type.CONSTANT or self.type_ == ISymbol.Type.FUNCTION)
		logging.warning("getName of %s returns %s", str(self.tuple_), repr(self.tuple_[0]))
		return jpype.JString(self.tuple_[0])

	@jpype.JOverride
	def getInteger(self):
		assert(self.type_ == ISymbol.Type.INTEGER)
		return self.integer

	@jpype.JOverride
	def getArguments(self):
		assert(self.type_ == ISymbol.Type.FUNCTION or self.type_ == ISymbol.Type.TUPLE)
		if self.type_ == ISymbol.Type.FUNCTION:
			return self.tuple_[1:]
		else:
			return self.tuple_

	@jpype.JOverride
	def getTuple(self):
		assert(self.type_ != ISymbol.Type.INTEGER)
		return self.tuple_

	@jpype.JOverride
	def hashCode(self):
		return jpype.JInt(hash( (self.type_,self.tuple_,self.integer) ) & 0x7FFFFFFF)

	@jpype.JOverride
	def equals(self, other):
		if self == other:
			return True
		else:
			return (self.type_, self.tuple_, self.integer) == (other.type_, other.tuple_, other.integer)

class JavaConstantSymbolImpl(JavaSymbolImpl):
	def __init__(self, s):
		super().__init__(type_=ISymbol.Type.CONSTANT, tuple_=(s,))

class JavaIntegerSymbolImpl(JavaSymbolImpl):
	def __init__(self, i):
		super().__init__(type_=ISymbol.Type.INTEGER, integer=i)

def createTypedSymbol(something):
	if isinstance(something, str):
		return JavaConstantSymbolImpl(something)
	elif isinstance(something, int):
		return JavaIntegerSymbolImpl(something)
	elif isinstance(something, (tuple,list)):
		return JavaIntegerSymbolImpl(something)



@jpype.JImplements(IPluginAtom.IQuery)
class JavaQueryImpl:
	def __init__(self, *arguments):
		# arguments = the query to the external atom
		self.arguments = arguments
		jit = jpype.JClass("java.util.ArrayList")()
		for arg in self.arguments:
			jit.add(JavaConstantSymbolImpl(arg))
		self.jinputTuple = jit

	@jpype.JOverride
	def getInterpretation(self):
		logging.warning("TBD")
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
		logging.warning("TBD")
		return jpype.JObject(None, IAtom)

	@jpype.JOverride
	def storeAtom(self, atom):
		logging.warning("TBD")
		return None

	@jpype.JOverride
	def storeConstant(self, s):
		logging.warning("TBD store %s", s)
		return JavaSymbolImpl('stored({})'.format(s))

	@jpype.JOverride
	def learn(self, nogood):
		logging.warning("TBD")


class JavaPluginCallWrapper:
	def __init__(self, eatomname, pluginholder, pluginatom):
		self.eatomname = eatomname
		self.pluginholder = pluginholder
		self.pluginatom = pluginatom

	def __call__(self, *arguments):
		try:
			logging.debug("executing java __call__ for %s", self.eatomname)
			jsc = JavaSolverContextImpl()
			jq = JavaQueryImpl(*arguments)
			logging.info("executing retrieve")
			janswer = self.pluginatom.retrieve(jsc, jq)
			logging.info("retrieved")
			tt = janswer.getTrueTuples()
			logging.info("true tuples")
			logging.info("true tuples = %s", str(tt.toString()))
			#logging.debug("retrieved %s", janswer.toString())
		except jpype.JClass("java.lang.Exception") as ex:
			logging.error("Java exception: %s", ex.toString())
			st = ex.getStackTrace()
			for ste in st:
				logging.error("\t at %s", ste.toString())
			#sb.append(ex.getClass().getName() + ": " + ex.getMessage() + "\n");
			raise


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
