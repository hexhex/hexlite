import sys, logging

logging.basicConfig(level=15, stream=sys.stderr, format="%(levelname)1s:%(filename)10s:%(lineno)3d:%(message)s")                         
# make log level names shorter so that we can show them                                   
logging.addLevelName(50, 'C')
logging.addLevelName(40, 'E')
logging.addLevelName(30, 'W')
logging.addLevelName(20, 'I')
logging.addLevelName(10, 'D')

logging.info("test1")

import jpype
jpype.startJVM(convertStrings=False)

IPluginAtom = jpype.JClass("at.ac.tuwien.kr.hexlite.api.IPluginAtom")
ISolverContext = jpype.JClass("at.ac.tuwien.kr.hexlite.api.ISolverContext")
IAtom = jpype.JClass("at.ac.tuwien.kr.hexlite.api.IAtom")
ISymbol = jpype.JClass("at.ac.tuwien.kr.hexlite.api.ISymbol")

@jpype.JImplements(ISymbol)
class JavaSymbolImpl:
    def __init__(self, what):
        self.what = what

    @jpype.JOverride
    def getType(self):
        return ISymbol.Type.CONSTANT

    @jpype.JOverride
    def getName(self):
        return self.what

    @jpype.JOverride
    def getInteger(self):
        return 4711

    @jpype.JOverride
    def getArguments(self):
        return []

    @jpype.JOverride
    def getTuple(self):
        return [self.getName()]

    @jpype.JOverride
    def hashCode(self):
        return jpype.JInt(hash(self.what) & 0x7FFFFFFF)

    @jpype.JOverride
    def equals(self, other):
        if self == other:
            return True
        elif self.what == other.what:
            return True
        else:
            return False


@jpype.JImplements(IPluginAtom.IQuery)
class JavaQueryImpl:
    def __init__(self):
        pass

    @jpype.JOverride
    def getInterpretation(self):
        logging.warning("TBD")
        return None

    @jpype.JOverride
    def getInput(self):
        ret = jpype.JClass("java.util.ArrayList")()
        ret.add(JavaSymbolImpl('foo'))
        ret.add(JavaSymbolImpl('bar'))
        return ret

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

def jmain():
    logging.info("test2")
    jls = jpype.JClass("java.lang.System")
    jls.out.println("i am printing java.class.path")
    print(jls.getProperty("java.class.path"))

    JStringPlugin = jpype.JClass("at.ac.tuwien.kr.hexlite.stringplugin.StringPlugin")
    logging.info("got JStringPlugin %s", JStringPlugin)
    splugin = JStringPlugin()
    logging.info("got splugin %s", splugin)
    jatoms = splugin.createAtoms()
    logging.info("got atoms %s", jatoms)
    jconcat = jatoms[0]

    jcontext = JavaSolverContextImpl()
    jquery = JavaQueryImpl()

    janswer = jconcat.retrieve(jcontext, jquery)
    logging.info("answer is %s", janswer)

    jpype.shutdownJVM()
    logging.info("done")

def main():
    try:
        jmain()
    except jpype.JClass("java.lang.Exception") as ex:
        logging.error("exception: %s", ex.toString())
        st = ex.getStackTrace()
        for ste in st:
            logging.error("\t at %s", ste.toString())
        #sb.append(ex.getClass().getName() + ": " + ex.getMessage() + "\n");
main()
