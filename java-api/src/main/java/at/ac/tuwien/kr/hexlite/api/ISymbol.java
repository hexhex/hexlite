package at.ac.tuwien.kr.hexlite.api;

import java.util.AbstractList;

public interface ISymbol {
    // Type of symbol
    // Predicates and Function terms are FUNCTION
    // strings are CONSTANT (and name starts/ends with quotes)
    public enum Type { CONSTANT, INTEGER, FUNCTION, TUPLE }
    public Type getType();

    // Constant or Function name (CONSTANT, FUNCTION), null otherwise
    public String getName();
    // integer value (INTEGER), null otherwise
    public Integer getInteger();
    // Arguments (FUNCTION, TUPLE), null otherwise
    public AbstractList<ISymbol> getArguments();
    // Overall tuple containing getName() and getArguments()
    // null values are omitted
    public AbstractList<ISymbol> getTuple();

    // as part of an answer set, it must be hashable and equal-able
    public int hashCode();
    public boolean equals(Object o);
}
