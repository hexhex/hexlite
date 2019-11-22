package at.ac.tuwien.kr.hexlite.api;

import java.util.ArrayList;
import java.util.HashSet;

public class Answer implements IPluginAtom.IAnswer {

    protected HashSet<ArrayList<ISymbol>> trueTuples;
    protected HashSet<ArrayList<ISymbol>> unknownTuples;

    public Answer() {
        trueTuples = new HashSet<ArrayList<ISymbol>>();
        unknownTuples = new HashSet<ArrayList<ISymbol>>();
    }

    public void output(ArrayList<ISymbol> trueTuple) {
        trueTuples.add(trueTuple);
    }

    public void outputUnknown(ArrayList<ISymbol> unknownTuple) {
        unknownTuples.add(unknownTuple);
    }

    @Override
    public HashSet<ArrayList<ISymbol>>  getTrueTuples() {
        return trueTuples;
    }

    @Override
    public HashSet<ArrayList<ISymbol>>  getUnknownTuples() {
        return unknownTuples;
    }

    @Override
    public String toString() {
        return "Answer: " + trueTuples.size() + " true tuples";
    }
}