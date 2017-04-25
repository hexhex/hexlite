import dlvhex;

import logging

#def id(p):
#	for x in dlvhex.getTrueInputAtoms():
#		dlvhex.output((x.tuple()[1], ))

def idc(c):
	dlvhex.output((c,))

def testZeroArity0():
	pass

def testZeroArity1():
	dlvhex.output(())

def testEven(pred1, pred2):
	true = [x for x in dlvhex.getTrueInputAtoms()]
	num = len(true)
	if num % 2 == 0:
		dlvhex.output(())

def testSubstr(string, start, length):
	if not isinstance(string, str) or not isinstance(start, int) or not isinstance(length, int):
		raise Exception("testSubstr expects inputs [str,int,int]")
	unquoted = string.strip('"')
	if start+length < len(unquoted):
		dlvhex.output((unquoted[start:start+length],))

def testConcat(strs):
	logging.debug('testConcat got '+repr(strs)+' '+str(strs.__class__)+' '+str(strs[0].__class__))
	needquote = any(['"' in s for s in strs])
	unquoted = [s.strip('"') for s in strs]
	result = ''.join(unquoted)
	if needquote:
		result = '"'+result+'"'
	dlvhex.output((result,))

def isEmpty(assignment):

	true = 0
	false = 0
	unknown = 0

	premisse = ()
	for x in dlvhex.getInputAtoms():
		if x.isTrue():
			true = true + 1
		elif x.isFalse():
			false = false + 1
		else:
			unknown = unknown + 1

	if true > 0:
		# external atom is true
		dlvhex.output(())
	elif (true + unknown) > 0:
		# external atom can be true
		dlvhex.outputUnknown(())
	else:
		# else case applies: (true + unknown) < min.intValue() or true > max.intValue()
		#
		# external atom is certainly not true
		v = 0

def numberOfBalls(assignment, min, max):

	true = 0
	false = 0
	unknown = 0

	premisse = ()
	for x in dlvhex.getInputAtoms():
		if x.isTrue():
			true = true + 1
		elif x.isFalse():
			false = false + 1
		else:
			unknown = unknown + 1
			v = 0

	if true >= min.intValue() and (true + unknown) <= max.intValue():
		# external atom is true
		dlvhex.output(())
	elif (true + unknown) >= min.intValue() and true <= max.intValue():
		# external atom can be true
		dlvhex.outputUnknown(())
	else:
		# else case applies: (true + unknown) < min.intValue() or true > max.intValue()
		#
		# external atom is certainly not true
		v = 0

def numberOfBallsSE(assignment, max):

	true = 0
	false = 0
	unknown = 0

	premisse = ()
	for x in dlvhex.getInputAtoms():
		if x.isTrue():
			true = true + 1
		elif x.isFalse():
			false = false + 1
		else:
			unknown = unknown + 1
			v = 0

	if (true + unknown) <= max.intValue():
		# external atom is true
		dlvhex.output(())
	elif true <= max.intValue():
		# external atom can be true
		dlvhex.outputUnknown(())
	else:
		# else case applies: if true > max.intValue()
		#
		# external
		v = 0

def numberOfBallsGE(assignment, min):

	true = 0
	false = 0
	unknown = 0

	premisse = ()
	for x in dlvhex.getInputAtoms():
		if x.isTrue():
			true = true + 1
		elif x.isFalse():
			false = false + 1
		else:
			unknown = unknown + 1
			v = 0

	if true >= min.intValue():
		# external atom is true
		dlvhex.output(())
	elif (true + unknown) >= min.intValue():
		# external atom can be true
		dlvhex.outputUnknown(())
	else:
		# else case applies: if (true + unknown) < min.intValue()
		#
		# external
		v = 0

# no native implementations for these, so let's use the non-native ones
testIsEmpty = isEmpty
testNumberOfBalls = numberOfBalls
testNumberOfBallsSE = numberOfBallsSE
testNumberOfBallsGE = numberOfBallsGE

def partialTest(assignment):

	true = 0
	false = 0
	unknown = 0

	premisse = ()
	for x in dlvhex.getInputAtoms():
		if x.isTrue():
			true = true + 1
#			premisse = premisse + (x, )
#			print "true input atom:", x.value()
		elif x.isFalse():
			false = false + 1
#			premisse = premisse + (x.negate(), )
#			print "false input atom:", x.value()
		else:
			unknown = unknown + 1
#			print "unknown input atom:", x.value()
			v = 0

	if true > 1:
#		dlvhex.learn(premisse + (dlvhex.storeOutputAtom((), False).negate(), ))
		dlvhex.output(())
	elif true + unknown > 1:
		dlvhex.outputUnknown(())

def rdf(uri):
	logging.warning('TODO implement &rdf (and #namespace)')
	dlvhex.output(('s', 'p', 'o'))

def register():
	#XFAIL = expected failure (out of fragment)
	#XFAIL dlvhex.addAtom("testA", (dlvhex.PREDICATE,), 1)
	#XFAIL dlvhex.addAtom("testB", (dlvhex.PREDICATE, dlvhex.PREDICATE), 1)
	#XFAIL dlvhex.addAtom("testC", (dlvhex.PREDICATE,), 1)
	dlvhex.addAtom("testZeroArity0", tuple(), 0)
	dlvhex.addAtom("testZeroArity1", tuple(), 0)
	#XFAIL unused dlvhex.addAtom("testConcatAll", (dlvhex.PREDICATE,), 1)
	#unused dlvhex.addAtom("testListDomain", (dlvhex.TUPLE,), 1)
	#unused dlvhex.addAtom("testListConcat", (dlvhex.TUPLE,), 1)
	#unused dlvhex.addAtom("testListLength", (dlvhex.CONSTANT,dlvhex.CONSTANT), 1)
	#unused dlvhex.addAtom("testListSplit", (dlvhex.CONSTANT,dlvhex.CONSTANT), 2)
	#unused dlvhex.addAtom("testListHalf", (dlvhex.CONSTANT,), 2)
	#unused dlvhex.addAtom("testListMerge", (dlvhex.CONSTANT,dlvhex.CONSTANT,dlvhex.CONSTANT), 2)
	dlvhex.addAtom("testSubstr", (dlvhex.CONSTANT,dlvhex.CONSTANT,dlvhex.CONSTANT), 1)
	dlvhex.addAtom("testEven", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	#unused dlvhex.addAtom("testOdd", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	#unused dlvhex.addAtom("testLessThan", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	#unused dlvhex.addAtom("testEqual", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	#XFAIL dlvhex.addAtom("id", (dlvhex.PREDICATE,), 1)
	dlvhex.addAtom("idc", (dlvhex.CONSTANT,), 1)
	#TODO testCautiousQuery
	#XFAIL (TODO) testSetMinus

	prop = dlvhex.ExtSourceProperties()
	prop.setProvidesPartialAnswer(True)
	dlvhex.addAtom("isEmpty", (dlvhex.PREDICATE, ), 0, prop)
	dlvhex.addAtom("testIsEmpty", (dlvhex.PREDICATE, ), 0, prop)

	prop = dlvhex.ExtSourceProperties()
	prop.setProvidesPartialAnswer(True)
	dlvhex.addAtom("numberOfBalls", (dlvhex.PREDICATE, dlvhex.CONSTANT, dlvhex.CONSTANT), 0, prop)
	dlvhex.addAtom("testNumberOfBalls", (dlvhex.PREDICATE, dlvhex.CONSTANT, dlvhex.CONSTANT), 0, prop)

	prop = dlvhex.ExtSourceProperties()
	prop.setProvidesPartialAnswer(True)
	prop.addAntimonotonicInputPredicate(0)
	dlvhex.addAtom("numberOfBallsSE", (dlvhex.PREDICATE, dlvhex.CONSTANT), 0, prop)
	dlvhex.addAtom("testNumberOfBallsSE", (dlvhex.PREDICATE, dlvhex.CONSTANT), 0, prop)

	prop = dlvhex.ExtSourceProperties()
	prop.setProvidesPartialAnswer(True)
	prop.addMonotonicInputPredicate(0)
	dlvhex.addAtom("numberOfBallsGE", (dlvhex.PREDICATE, dlvhex.CONSTANT), 0, prop)
	dlvhex.addAtom("testNumberOfBallsGE", (dlvhex.PREDICATE, dlvhex.CONSTANT), 0, prop)

	prop = dlvhex.ExtSourceProperties()
	prop.setProvidesPartialAnswer(True)
	dlvhex.addAtom("partialTest", (dlvhex.PREDICATE, ), 0, prop)

	#XFAIL (TODO) sumD0
	#XFAIL getreq
	#unused mapping
	#unused getSizes
	#unused getSizesRestr
	#XFAIL getDiagnoses

	prop = dlvhex.ExtSourceProperties()
	prop.addFiniteOutputDomain(0)
	dlvhex.addAtom("testConcat", (dlvhex.TUPLE,), 1, prop)

	dlvhex.addAtom("rdf", (dlvhex.CONSTANT,), 3)

# vim:list:noet:
