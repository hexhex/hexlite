import dlvhex;

import logging

#def id(p):
#	for x in dlvhex.getTrueInputAtoms():
#		dlvhex.output((x.tuple()[1], ))

def testConcat(strs):
	logging.debug('testConcat got '+repr(strs)+' '+str(strs.__class__)+' '+str(strs[0].__class__))
	needquote = any(['"' in s for s in strs])
	unquoted = [s.strip('"') for s in strs]
	result = ''.join(unquoted)
	if needquote:
		result = '"'+result+'"'
	dlvhex.output((result,))

def register():
#	dlvhex.addAtom("id", (dlvhex.PREDICATE, ), 1)

	prop = dlvhex.ExtSourceProperties()
	prop.addFiniteOutputDomain(0)
	dlvhex.addAtom("testConcat", (dlvhex.TUPLE,), 1, prop)

# vim:list:noet:
