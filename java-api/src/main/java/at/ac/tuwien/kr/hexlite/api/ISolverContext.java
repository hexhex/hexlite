package at.ac.tuwien.kr.hexlite.api;

import java.util.ArrayList;
import java.util.HashSet;

public interface ISolverContext {
    public static class StoreAtomException extends Exception {
        public StoreAtomException(String message) {
            super(message);
        }
    }
    // otuple = the output tuple of the current evaluation that shall be represented as an ISymbol
    public ISymbol storeOutputAtom(ArrayList<ISymbol> otuple) throws StoreAtomException;
    // tuple = predicate + arguments of an atom to be represented as an ISymbol
    public ISymbol storeAtom(ArrayList<ISymbol> tuple) throws StoreAtomException;
    public ISymbol storeConstant(String s);
    public ISymbol storeString(String s);
    public ISymbol storeInteger(Integer i);
    public void learn(HashSet<ISymbol> nogood);
}