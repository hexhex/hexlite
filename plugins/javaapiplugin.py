import dlvhex
from dlvhex import ID
import hexlite

import atexit
import logging
import os
import re
import sys
import threading
import time

# this requires jpype to be installed and it requires a working Java runtime environment
import jpype
from jpype import java
from jpype.types import *
logging.debug("starting JVM")
java_args = os.environ.get('HEXLITE_JAVA_ARGUMENTS', [])
if java_args != []:
	java_args = java_args.split(' ')
jpype.startJVM(*java_args, convertStrings=False)

def logJavaExceptionWithStacktrace(ex):
	logging.error("Java exception: %s", ex.toString())
	st = ex.getStackTrace()
	for ste in st:
		logging.error("\t at %s", ste.toString())
	#sb.append(ex.getClass().getName() + ": " + ex.getMessage() + "\n");

# this loads the hexlite-API-specific classes (from hexlite-java-plugin-api-XYZ.jar)
IPluginAtom = JClass("at.ac.tuwien.kr.hexlite.api.IPluginAtom")
ISolverContext = JClass("at.ac.tuwien.kr.hexlite.api.ISolverContext")
JStoreAtomException = JClass("at.ac.tuwien.kr.hexlite.api.ISolverContext.StoreAtomException")
IInterpretation = JClass("at.ac.tuwien.kr.hexlite.api.IInterpretation")
ISymbol = JClass("at.ac.tuwien.kr.hexlite.api.ISymbol")

class JavaPluginHolder:
	def __init__(self, classname, jplugin):
		self.classname = classname
		self.jplugin = jplugin

loadedPlugins = []

def convertExtSourceProperties(jesp):
	# convert only those parts that are implemented in hexlite
	ret = dlvhex.ExtSourceProperties()
	ret.setProvidesPartialAnswer(jesp.getProvidesPartialAnswer())
	ret.setDoInputOutputLearning(jesp.getDoInputOutputLearning())
	return ret

def convertInputArguments(jinputarguments):
	def convertOne(t):
		if t == IPluginAtom.InputType.PREDICATE:
			return dlvhex.PREDICATE
		elif t == IPluginAtom.InputType.CONSTANT:
			return dlvhex.CONSTANT
		elif t == IPluginAtom.InputType.TUPLE:
			return dlvhex.TUPLE
		else:
			raise ValueError("unknown input argument type "+repr(t))
	ret = tuple([ convertOne(t) for t in jinputarguments ])
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
		#logging.info("JavaSymbolImpl with hid %s %s", self.hid, self.__valuecache)

	@jpype.JOverride
	def negate(self):
		#logging.info("want to negate %s", self.hid)
		return JavaSymbolImpl(self.hid.negate())

	@jpype.JOverride
	def value(self):
		#logging.info("value of %s", self.hid)
		return self.hid.value()

	@jpype.JOverride
	def intValue(self):
		#logging.info("intvalue of %s", self.hid)
		return self.hid.intValue()

	@jpype.JOverride
	def isTrue(self):
		#logging.info("isTrue of %s", self.hid)
		return self.hid.isTrue()

	@jpype.JOverride
	def isFalse(self):
		#logging.info("isFalse of %s", self.hid)
		return self.hid.isFalse()

	@jpype.JOverride
	def isAssigned(self):
		#logging.info("isAssigned of %s", self.hid)
		return self.hid.isAssigned()

	@jpype.JOverride
	def tuple(self):
		ret = java.util.ArrayList()
		#logging.info("want to get tuple of %s", self.hid)
		for e in self.hid.tuple():
			ret.add(JavaSymbolImpl(e))
		return ret

	@jpype.JOverride
	def extension(self):
		#logging.info("creating hashset")
		ret = java.util.HashSet()
		#logging.info("filling hashset")
		for e in self.hid.extension():
			#logging.info("adding tuple %s from extension", e)
			#ret.add(e)
			tup = java.util.ArrayList()
			for t in e:
				#jsym = jpype.JObject(JavaSymbolImpl(t))
				jsym = JavaSymbolImpl(t)
				#logging.info("adding symbol %s %s as %s", t, t.__class__, repr(jsym))
				tup.add(jsym)
			#logging.info("adding tuple %s to result as %s", tup, repr(tup))
			ret.add(tup)
		#logging.info("returning %s %s", ret, ret.__class__)
		return ret

	@jpype.JOverride
	def hashCode(self):
		#logging.info("returning hash code for %s", self)
		return int(hash(self.__valuecache) & 0x7FFFFFFF)

	def __eq__(self, other):
		#logging.info("__eq__ got called on %s vs repr(%s)", self.hid, repr(other))
		if not isinstance(other, JavaSymbolImpl):
			return False
		return self.hid == other.hid

	@jpype.JOverride
	def equals(self, other):
		# we could just write self == other, but let's make it explicit that we call above method
		# reminder:
		#   in Java, == only compares memory locations, and content comparison is done with equals()
		#   in Python, == is the same as __eq__ and it may do whatever it wants
		return self.__eq__(other)

	def __str__(self):
		#logging.info("__str__ of %s %s", self.hid, self.__valuecache)
		return str(self.hid)

	@jpype.JOverride
	def toString(self):
		#logging.info("toString of %s %s", self.hid, self.__valuecache)
		return str(self.hid)

@jpype.JImplements(IInterpretation)
class JavaInterpretationImpl:
	def __init__(self):
		pass

	@jpype.JOverride
	def getTrueInputAtoms(self):
		return self._adapt(dlvhex.getTrueInputAtoms())

	@jpype.JOverride
	def getInputAtoms(self):
		return self._adapt(dlvhex.getInputAtoms())

	def _adapt(self, items):
		ret = java.util.HashSet()
		# each atom from dlvhex.getInputAtoms() is converted
		# from hexlite to a java ISymbol
		for x in items:
			#logging.warning("adapting %s", x)
			ret.add(JObject(JavaSymbolImpl(x)))
		return ret


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
		return JavaInterpretationImpl()

	@jpype.JOverride
	def getInput(self):
		return self.jinputTuple


rValidConstant = re.compile(r'^[a-z][a-z0-9A-Z_]+$')
@jpype.JImplements(ISolverContext)
class JavaSolverContextImpl:
	def __init__(self):
		pass

	@jpype.JOverride
	def storeOutputAtom(self, otuple):
		# all the otuple elements are ISymbol s
		#logging.info("jSC.storeOutputAtom %s", otuple)
		try:
			s = dlvhex.storeOutputAtom([ x.hid for x in otuple ])
		except dlvhex.StoreAtomException as e:
			raise JStoreAtomException(str(e))
		r = JavaSymbolImpl(s)
		ret = jpype.JObject(r, ISymbol)
		#logging.info("jSC.storeOutputAtom %s returns %s with type %s", otuple, repr(ret), type(ret))
		return ret

	@jpype.JOverride
	def getInstantiatedOutputAtoms(self):
		ret = java.util.ArrayList()
		for oa in dlvhex.getInstantiatedOutputAtoms():
			ret.add(jpype.JObject(JavaSymbolImpl(oa), ISymbol))
		#logging.info("jSC.getInstantiatedOutputAtoms returns %s", repr(ret))
		return ret

	@jpype.JOverride
	def storeAtom(self, tuple_):
		# all the tuple_ elements are ISymbol s
		#logging.info("jSC.storeAtom %s", tuple_)
		try:
			s = dlvhex.storeAtom([ x.hid for x in tuple_ ])
		except dlvhex.StoreAtomException as e:
			raise JStoreAtomException(str(e))
		r = JavaSymbolImpl(s)
		ret = jpype.JObject(r, ISymbol)
		#logging.info("jSC.storeAtom %s returns %s with type %s", tuple_, repr(ret), type(ret))
		return ret

	@jpype.JOverride
	def storeConstant(self, s):
		# convert to python string, otherwise various string operations done within hexlite will fail on the java strings
		pythonstr = str(s)
		if len(pythonstr) == 0 or (pythonstr[0] != '"' and pythonstr[-1] != '"' and not rValidConstant.match(pythonstr)):
			raise ValueError("cannot storeConstant for term '{}' with is probably a string (use storeString)".format(pythonstr))
		r = jpype.JObject(JavaSymbolImpl(dlvhex.storeConstant(pythonstr)), ISymbol)
		#logging.info("storeConstant %s returns %s with type %s", s, repr(r), type(r))
		return r

	@jpype.JOverride
	def storeString(self, s):
		pythonstr = str(s)
		r = jpype.JObject(JavaSymbolImpl(dlvhex.storeString(pythonstr)), ISymbol)
		#logging.info("storeString %s returns %s with type %s", s, repr(r), type(r))
		return r

	@jpype.JOverride
	def storeInteger(self, i):
		return JavaSymbolImpl(dlvhex.storeInteger(s))

	@jpype.JOverride
	def learn(self, nogood):
		logging.info("java learns nogood %s", nogood.toString())
		dlvhex.learn([ x.hid for x in nogood ])

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
			#logging.debug("retrieved")
			tt = janswer.getTrueTuples()
			#logging.info("true tuples")
			if __debug__:
				# sort for reproducable runs (java hashing is not stable across runs)
				tt = sorted(tt, key=lambda t: t.toString())
			for t in tt:
				logging.debug("true tuple = %s %s", repr(t), t.toString())
				for idx, elem in enumerate(t):				
					logging.debug(" idx %d = %s %s", idx, repr(elem), elem.toString())
				assert(all([ isinstance(e, JavaSymbolImpl) for e in t ]))
				tupleOfID = tuple([ e.hid for e in t ])
				#logging.warning("retrieve created output %s for java output %s", tupleOfID, t.toString())
				dlvhex.output(tupleOfID)
		except jpype.JException as e:
			logging.error("plugin call wrapper got Java exception %s %s", e, e.__class__)
			logJavaExceptionWithStacktrace(e)
			raise
		except Exception as e:
			logging.error("plugin call wrapper got exception that is not a JException %s %s", e, e.__class__)
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

def teardown():
	logging.info("teardown: JVM shutdown")
	def watchdog():
		logging.info("watchdog started")
		time.sleep(1)
		logging.info("watchdog still alive -> killing")
		os._exit(-1)
	stt = threading.Thread(target=watchdog, daemon=True)
	stt.start()
	jpype.shutdownJVM()
	logging.info("JVM shutdown successful")

