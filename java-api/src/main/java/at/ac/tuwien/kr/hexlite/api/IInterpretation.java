package at.ac.tuwien.kr.hexlite.api;

import java.util.AbstractList;
import java.util.AbstractSet;

public interface IInterpretation {
    public AbstractSet<IAtom> getTrueAtoms();
    public AbstractSet<IAtom> getAtoms();
    public AbstractSet<AbstractList<ISymbol>> getExtension(String predicateName);
}
