# this plugin registers the JSON output model callback

import dlvhex
from hexlite.modelcallback import JSONModelCallback

def register():
	dlvhex.registerModelCallbackClass(JSONModelCallback)
