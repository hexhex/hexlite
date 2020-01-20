package at.ac.tuwien.kr.hexlite.api;

import java.util.ArrayList;
import java.util.HashSet;

// corresponds to dlvhex::ID class
public interface ISymbol {
    // get negated symbol (works for non-integers)
    public ISymbol negate();

    // complete value as a string
    public String value();
    public Integer intValue();

    public boolean isTrue();
    public boolean isFalse();
    public boolean isAssigned();

    // structured representation of the symbol
    public ArrayList<ISymbol> tuple();

    // all arguments X such that this sumbol(X) is true in the current interpretation
    // symbol must be a constant term
    // return value is a set of tuples of arguments
    public HashSet<ArrayList<ISymbol> > extension();

    // as part of an answer set, it must be hashable and equal-able
    public int hashCode();
    public boolean equals(Object o);
    // in order to convert it to string within Java
    public String toString();
}
