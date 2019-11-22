package at.ac.tuwien.kr.hexlite.api;

import java.util.ArrayList;
import java.util.HashSet;

public interface IPluginAtom {
    public enum InputType { PREDICATE, CONSTANT, TUPLE };

    public interface IQuery {
        // interpretation relevant to this external atom
        IInterpretation getInterpretation();
        // the input argument tuple
        ArrayList<ISymbol> getInput();
    }

    public interface IAnswer {
        HashSet<ArrayList<ISymbol>> getTrueTuples();
        HashSet<ArrayList<ISymbol>> getUnknownTuples();
    }

    // the following methods correspond to everything that must be setup in the constructor in C++
    // it also corresponds to the arguments of dlvhex.addAtom in Python
    public String getPredicate();
    public ArrayList<InputType> getInputArguments();
    public int getOutputArguments();
    public ExtSourceProperties getExtSourceProperties();

    // the following method implements semantics of the external atom

    public IAnswer retrieve(ISolverContext ctx, IQuery query);

}
