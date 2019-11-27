package at.ac.tuwien.kr.hexlite.api;

import java.util.AbstractSet;

public interface ISolverContext {
    public IAtom storeOutputAtom(IPluginAtom atom);
    public IAtom storeAtom(IPluginAtom atom);
    public ISymbol storeConstant(String s);
    public ISymbol storeInteger(Integer i);
    public void learn(AbstractSet<IAtom> nogood);
}