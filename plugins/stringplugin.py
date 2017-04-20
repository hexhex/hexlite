import dlvhex

def concat(strs):
  needquote = any(['"' in s for s in strs])
  unquoted = [s.strip('"') for s in strs]
  result = ''.join(unquoted)
  if needquote:
    result = '"'+result+'"'
  dlvhex.output((result,))

def register():
	prop = dlvhex.ExtSourceProperties()
	prop.addFiniteOutputDomain(0)
	dlvhex.addAtom("concat", (dlvhex.TUPLE,), 1, prop)
