package at.ac.tuwien.kr.hexlite.api;

import java.util.AbstractSet;

public interface ISolverContext {
    public ISymbol storeOutputAtom(IPluginAtom atom);
    public ISymbol storeAtom(IPluginAtom atom);
    public ISymbol storeConstant(String s);
    public ISymbol storeInteger(Integer i);
    public void learn(AbstractSet<ISymbol> nogood);
}