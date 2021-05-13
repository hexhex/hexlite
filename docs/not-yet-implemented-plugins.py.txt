# this file contains plugin functionality from dlvhex that has not been implemented in hexlite

import dlvhex

def test(a, b, c):
	dlvhex.output((a, a))

def neg(p):
	if dlvhex.learnSupportSets():
		dlvhex.learn((
				dlvhex.storeAtom((p, )).negate(),	# if p is true
				dlvhex.storeOutputAtom(()).negate()	# then () is in the output
				));
	else:
		for x in dlvhex.getTrueInputAtoms():
			return
                dlvhex.output(())

def aOrNotB(a,b):

	if dlvhex.learnSupportSets():
		dlvhex.learn((
				dlvhex.storeAtom((a, )),
				dlvhex.storeOutputAtom(()).negate()	# then () is in the output
				));
		dlvhex.learn((
				dlvhex.storeAtom((b, )).negate(),
				dlvhex.storeOutputAtom(()).negate()	# then () is in the output
				));
	else:
		aIsTrue = dlvhex.isTrue(dlvhex.storeAtom((a, )))
		bIsFalse = dlvhex.isFalse(dlvhex.storeAtom((b, )))
		if aIsTrue or bIsFalse:
			dlvhex.output(())

def parity(p):

	if dlvhex.learnSupportSets():
		pos = ()
		for x in dlvhex.getInputAtoms():
			pos = pos + (False, )

		# special case: no input
		if pos == ():
			# always true
			dlvhex.learn(dlvhex.storeOutputAtom(()).negate(), )

		else:
			pos = pos[:-1]
			pos = list(pos)
			overflow = False 
			while not overflow:
				ng = ()
				# enumerate all combinations except for the last element (which is then definite)
				last = False
				for i in range(0, len(pos)):
					if pos[i] == True:
						ng = ng + (dlvhex.getInputAtoms()[i], )
						last = not last
					else:
						ng = ng + (dlvhex.getInputAtoms()[i].negate(), )

				# add last element with a sign such that the partiy is even
				if last:
					ng = ng + (dlvhex.getInputAtoms()[-1], )
				else:
        	                        ng = ng + (dlvhex.getInputAtoms()[-1].negate(), )

				# generate nogood which implies that the external atom is true
				supset = ng + (dlvhex.storeOutputAtom(()).negate(), )
				dlvhex.learn(supset)

				# go to next combination and check if we have an overflow, i.e., all combinations have been enumerated
				inc=0
				pos[inc] = not pos[inc]
				while not overflow and not pos[inc]:
					inc = inc + 1
                                        if inc >= len(pos):
                                                overflow = True
					else:
						pos[inc] = not pos[inc]

	even = True
	for atom in dlvhex.getInputAtoms():
		if atom.isTrue():
			even = not even
	if even:
		dlvhex.output(())

def fibonacci(val):
	dlvhex.output((fibonacci_comp(val.intValue()), ))
	
def fibonacci_comp(val):
	if val <= 2:
		return 1
	else:
		return fibonacci_comp(val - 1) + fibonacci_comp(val - 2)

def testSetMinus(p, q):

	premisse = ()
	outputatoms = ()

	input = dlvhex.getInputAtoms()
	for x in input:
		tup = x.tuple()
		if tup[0].value() == p.value():
			# keep true monotonic input atoms
			if dlvhex.isTrue(x):
				premisse = (x, ) + premisse

			if x.isTrue() and not dlvhex.isTrue(dlvhex.storeAtom((q, tup[1]))):
				outputatoms = (dlvhex.storeOutputAtom((tup[1], )), ) + outputatoms
				dlvhex.output((tup[1], ))

		if tup[0].value() == q.value():
			# keep false antimonotonic input atoms
			if not dlvhex.isTrue(x):
				premisse = (x.negate(), ) + premisse

	# learn one nogood for each output atom
	for x in outputatoms:
		dlvhex.learn((x.negate(), ) + premisse)

def greaterOrEqual(p, idx, bound):
	sum = 0
	for x in dlvhex.getTrueInputAtoms():
		if x.tuple()[0] == p:
			sum += x.tuple()[idx.intValue()].intValue()
	if sum >= bound.intValue():
		dlvhex.output(())

def greater(a,b):
	if a.value() != "bad" and b.value() != "bad":
		if int(a.value()[1:]) > int(b.value()[1:]):
			dlvhex.output(())

def date():
	from datetime import datetime
	t = "\"" + datetime.now().strftime('%Y-%m-%d') + "\""
	dlvhex.output((t, ))

def tail(str):
	if (len(str.value()) > 1 and str.value() != "\"\""):
		dlvhex.output((str.value()[:-1], ))
	else:
		dlvhex.output(("\"\"", ))

def cnt(p):
	c = 0
	for x in dlvhex.getTrueInputAtoms():
		c = c + 1
	dlvhex.output((c, ))

def main():
	h1 = dlvhex.storeAtom(("q", "X"))
	h2 = dlvhex.storeAtom(("r", "X"))
	b = dlvhex.storeExternalAtom("concat", ("a", "b"), ("X", ))
	f = dlvhex.storeAtom(("p", "a"))
	r = dlvhex.storeRule((h1, h2, ), (b, ), ());
	a = dlvhex.evaluateSubprogram(((f, ), (r, )))

	prog = dlvhex.loadSubprogram("examples/3col.hex")
	print("Evaluating the program:")
	print(dlvhex.getValue(prog[1]))
	print("Facts:")
	print(dlvhex.getValue(prog[0]))

	ans = dlvhex.evaluateSubprogram(prog)
	for x in ans:
		print("Answer set:", dlvhex.getValue(x))

def register():
	dlvhex.addAtom("test", (dlvhex.PREDICATE, dlvhex.CONSTANT, dlvhex.CONSTANT), 2)

	prop = dlvhex.ExtSourceProperties()
	prop.setSupportSets(True)
	prop.setCompletePositiveSupportSets(True)
	dlvhex.addAtom("neg", (dlvhex.PREDICATE, ), 0, prop)

	prop = dlvhex.ExtSourceProperties()
	prop.setSupportSets(True)
	prop.setCompletePositiveSupportSets(True)
	dlvhex.addAtom("aOrNotB", (dlvhex.PREDICATE, dlvhex.PREDICATE), 0, prop)

	prop = dlvhex.ExtSourceProperties()
	prop.setSupportSets(True)
	prop.setCompletePositiveSupportSets(True)
	dlvhex.addAtom("parity", (dlvhex.PREDICATE, ), 0, prop)

	dlvhex.addAtom("fibonacci", (dlvhex.CONSTANT, ), 1)

	dlvhex.addAtom("date", (), 1)

	prop = dlvhex.ExtSourceProperties()
	dlvhex.addAtom("greater", (dlvhex.CONSTANT, dlvhex.CONSTANT), 0, prop)

	dlvhex.addAtom("greaterOrEqual", (dlvhex.PREDICATE, dlvhex.CONSTANT, dlvhex.CONSTANT), 0)

	prop = dlvhex.ExtSourceProperties()
	prop.addWellorderingStrlen(0, 0)
	dlvhex.addAtom("tail", (dlvhex.CONSTANT, ), 1, prop)

	dlvhex.addAtom("cnt", (dlvhex.PREDICATE, ), 1)

# vim:noexpandtab:nolist:
