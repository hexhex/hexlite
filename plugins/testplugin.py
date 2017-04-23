import dlvhex;

import logging

#def id(p):
#	for x in dlvhex.getTrueInputAtoms():
#		dlvhex.output((x.tuple()[1], ))

def testZeroArity0():
	pass

def testZeroArity1():
	dlvhex.output(tuple())

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

	prop = dlvhex.ExtSourceProperties()
	prop.addFiniteOutputDomain(0)
	dlvhex.addAtom("testConcat", (dlvhex.TUPLE,), 1, prop)

#	dlvhex.addAtom("id", (dlvhex.PREDICATE, ), 1)

# vim:list:noet:
