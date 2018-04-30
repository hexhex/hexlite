import dlvhex

import hexlite.ast.shallowparser as shp

import logging

def id(p):
	for x in dlvhex.getTrueInputAtoms():
		tup = x.tuple()
		if len(tup) != 2:
			raise Exception("this external atom processes only arity 1 predicate inputs")
		dlvhex.output( (tup[1],) )

def idc(c):
	dlvhex.output((c,))

def testZeroArity0():
	pass

def testZeroArity1():
	dlvhex.output(())

def testA(pred):
	if len(dlvhex.getTrueInputAtoms()) == 0:
		dlvhex.output(('foo',))
	else:
		dlvhex.output(('bar',))

def testB(pred1, pred2):
	if len(dlvhex.getTrueInputAtoms()) <= 1:
		dlvhex.output(('bar',))
	else:
		dlvhex.output(('foo',))

def testC(pred):
	for atom in dlvhex.getTrueInputAtoms():
		for x in atom.tuple()[1:]:
			# output arguments of input predicate
			dlvhex.output((x.value(),))

def testEven(pred1, pred2):
	true = [x for x in dlvhex.getTrueInputAtoms()]
	num = len(true)
	if num % 2 == 0:
		dlvhex.output(())

def testSubstr(string, start, length):
	stringv = string.value()
	needquote = '"' in stringv
	startv = start.intValue()
	lengthv = length.intValue()
	unquoted = stringv.strip('"')
	endv = min(startv+lengthv, len(unquoted)+1)
	out = unquoted[startv:endv]
	if needquote:
		out = '"'+out+'"'
	logging.debug('testSubstr with string={} start={} length={} creates out={}'.format(stringv, startv, lengthv, out))
	dlvhex.output((out,))

def testStrlen(string):
	stringv = string.value()
	unquoted = stringv.strip('"')
	dlvhex.output( (len(unquoted),) )

def testSmallerThan(int1, int2):
	if int1.intValue() < int2.intValue():
		dlvhex.output( () )

def testConcat(strs):
	#logging.debug('testConcat got '+repr(strs)+' '+str(strs.__class__)+' '+str(strs[0].__class__))
	values = [s.value() for s in strs]
	#logging.debug('testConcat values '+repr(values))
	needquote = any(['"' in s for s in values])
	#logging.debug('testConcat needquote '+repr(needquote))
	unquoted = [s.strip('"') for s in values]
	result = ''.join(unquoted)
	if needquote:
		result = '"'+result+'"'
	#logging.debug('testConcat returns '+repr(result))
	dlvhex.output((result,))

def isFunctionTerm(term):
	logging.debug('isFunctionTerm got '+repr(term))
	pinp = shp.parseTerm(term.value())
	logging.debug('parseTerm {}'.format(repr(pinp)))
	if len(pinp) > 1:
		# yes it is
		dlvhex.output( () )

def functionCompose(args):
	logging.debug('functionCompose got '+repr(args))
	if len(args) == 1:
		dlvhex.output((args[0],))
	else:
		apred = args[0].value()
		avalues = [a.value() for a in args[1:]]
		dlvhex.output(("{}({})".format(apred, ','.join(avalues)),))

def functionDecompose(term, narg):
	logging.debug('functionDecompose got {} and {}'.format(repr(term), narg))
	pinp = shp.parseTerm(term.value())
	logging.debug('parseTerm {}'.format(repr(pinp)))
	argidx = narg.intValue()
	if argidx < len(pinp):
		dlvhex.output( (shp.shallowprint(pinp[argidx]),) )

def functionDecomposeN(inp, N):
	logging.debug('functionDecomposeN got {} and {}'.format(repr(inp), N))
	pinp = shp.parseTerm(inp.value())
	logging.debug('parseTerm {}'.format(repr(pinp)))
	if len(pinp) == N+1:
		otuple = [ shp.shallowprint(x) for x in pinp ]
		dlvhex.output( tuple(otuple) )

def functionDecompose1(inp):
	functionDecomposeN(inp, 1)
def functionDecompose2(inp):
	functionDecomposeN(inp, 2)
def functionDecompose3(inp):
	functionDecomposeN(inp, 3)

def getArity(term):
	logging.debug('getArity got {}'.format(repr(term)))
	pinp = shp.parseTerm(term.value())
	logging.debug('parseTerm {}'.format(repr(pinp)))
	dlvhex.output( (len(pinp)-1,) )

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
	# returns true if the predicate input is true for more than 1 constant

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

def testSetMinus(p, q):
	# is true for all constants in extension of p but not in extension of q
	pset, qset = set(), set()
	for x in dlvhex.getTrueInputAtoms():
		tup = x.tuple()
		if tup[0].value() == p.value():
			pset.add(tup[1].value())
		elif tup[0].value() == q.value():
			qset.add(tup[1].value())
	rset = pset - qset
	for r in rset:
		dlvhex.output( (r,) )

def testSetMinusLearn(p, q):
	# is true for all constants in extension of p but not in extension of q
	# (same as testSetMinus)
	# uses learning
	for x in p.extension():
		if not x in q.extension():
			# learn that it is not allowed that p(x) and -q(x) and this atom is false for x
			dlvhex.learn((
					dlvhex.storeAtom((p, ) + x),
					dlvhex.storeAtom((q, ) + x).negate(),
					dlvhex.storeOutputAtom(x).negate()
					))
			dlvhex.output(x)

def testNonmon(p):
	pset = set()
	for x in dlvhex.getTrueInputAtoms():
		tup = x.tuple()
		pset.add(tup[1].intValue())
	mapping = {
		frozenset([]):    [2],
		frozenset([1]):   [1],
		frozenset([2]):   [1],
		frozenset([1,2]): [1,2],
	}
	pset = frozenset(pset)
	if pset not in mapping:
		raise Exception("testNonmon is supposed to handle only input domain {1,2}")
	for o in mapping[pset]:
		dlvhex.output( (o,) )

def testNonmon2(p):
	pset = set()
	for x in dlvhex.getTrueInputAtoms():
		tup = x.tuple()
		pset.add(tup[1].intValue())
	mapping = {
		frozenset([]):    [2],
		frozenset([1]):   [2],
		frozenset([2]):   [ ],
		frozenset([1,2]): [1,2],
	}
	pset = frozenset(pset)
	if pset not in mapping:
		raise Exception("testNonmon2 is supposed to handle only input domain {1,2}")
	for o in mapping[pset]:
		dlvhex.output( (o,) )

def rdf(uri):
	logging.warning('TODO implement &rdf (and #namespace)')
	dlvhex.output(('s', 'p', 'o'))

def issue_2_num(a):
	n = 0
	for x in dlvhex.getInputAtoms():
		if x.tuple()[0] == a and x.isTrue():
			n += 1
	dlvhex.output((n, ))

def register():
	#XFAIL = expected failure
	dlvhex.addAtom("testA", (dlvhex.PREDICATE,), 1)
	dlvhex.addAtom("testB", (dlvhex.PREDICATE, dlvhex.PREDICATE), 1)
	dlvhex.addAtom("testC", (dlvhex.PREDICATE,), 1)
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
	dlvhex.addAtom("testStrlen", (dlvhex.CONSTANT,), 1)
	dlvhex.addAtom("testSmallerThan", (dlvhex.CONSTANT,dlvhex.CONSTANT), 0)
	dlvhex.addAtom("testEven", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	#unused dlvhex.addAtom("testOdd", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	#unused dlvhex.addAtom("testLessThan", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	#unused dlvhex.addAtom("testEqual", (dlvhex.PREDICATE,dlvhex.PREDICATE), 0)
	dlvhex.addAtom("id", (dlvhex.PREDICATE,), 1)
	#XFAIL partial dlvhex.addAtom("idp", (dlvhex.PREDICATE,), 1)
	dlvhex.addAtom("idc", (dlvhex.CONSTANT,), 1)
	#TODO testCautiousQuery
	dlvhex.addAtom("testSetMinus", (dlvhex.PREDICATE,dlvhex.PREDICATE), 1)
	dlvhex.addAtom("testSetMinusLearn", (dlvhex.PREDICATE,dlvhex.PREDICATE), 1)

	dlvhex.addAtom("testNonmon", (dlvhex.PREDICATE,), 1)
	dlvhex.addAtom("testNonmon2", (dlvhex.PREDICATE,), 1)

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

	dlvhex.addAtom("functionCompose", (dlvhex.TUPLE,), 1)
	dlvhex.addAtom("functionDecompose", (dlvhex.CONSTANT,dlvhex.CONSTANT), 1)
	dlvhex.addAtom("functionDecompose1", (dlvhex.CONSTANT,), 2)
	dlvhex.addAtom("functionDecompose2", (dlvhex.CONSTANT,), 3)
	dlvhex.addAtom("functionDecompose3", (dlvhex.CONSTANT,), 4)
	dlvhex.addAtom("getArity", (dlvhex.CONSTANT,), 1)
	dlvhex.addAtom("isFunctionTerm", (dlvhex.CONSTANT,), 0)

	dlvhex.addAtom("rdf", (dlvhex.CONSTANT,), 3)

	dlvhex.addAtom("issue_2_num", (dlvhex.PREDICATE, ), 1)
# vim:list:noet:
