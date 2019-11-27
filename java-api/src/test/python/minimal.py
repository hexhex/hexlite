import jpype
from jpype import JImplements, java, JClass, JObject, JOverride

jpype.startJVM(convertStrings=False)

@JImplements(java.io.Serializable)
class MyClass(object):
    def __init__(self, mesg):
        self.mesg=mesg
    def getMessage(self):
        return self.mesg
    @JOverride
    def toString(self):
        return self.mesg

jl=JClass('java.util.ArrayList')()
jl.add(MyClass("foo"))

print(jl.get(0))
print(type(jl.get(0)))
# does not work with jpype 0.7 but is implemented due to 
print(jl.get(0).getMessage())