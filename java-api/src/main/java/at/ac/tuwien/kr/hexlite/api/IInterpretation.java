package at.ac.tuwien.kr.hexlite.api;

import java.util.AbstractList;
import java.util.AbstractSet;

public interface IInterpretation {
    public AbstractSet<ISymbol> getTrueInputAtoms();
    public AbstractSet<ISymbol> getInputAtoms();
    //public AbstractSet<AbstractList<ISymbol>> getExtension(String predicateName);
}
