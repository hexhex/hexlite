package at.ac.tuwien.kr.hexlite.testplugin;

import java.util.AbstractCollection;
import java.util.ArrayList;
import java.util.LinkedList;

import at.ac.tuwien.kr.hexlite.api.Answer;
import at.ac.tuwien.kr.hexlite.api.ExtSourceProperties;
import at.ac.tuwien.kr.hexlite.api.IPlugin;
import at.ac.tuwien.kr.hexlite.api.IPluginAtom;
import at.ac.tuwien.kr.hexlite.api.ISolverContext;
import at.ac.tuwien.kr.hexlite.api.ISymbol;

public class ConcatSetMinusPlugin implements IPlugin {
    public class ConcatAtom implements IPluginAtom {
        private final ArrayList<InputType> inputArguments;

        public ConcatAtom() {
            inputArguments = new ArrayList<InputType>();
            inputArguments.add(InputType.TUPLE);
        }

        @Override
        public String getPredicate() {
            return "testConcat";
        }

        @Override
        public ArrayList<InputType> getInputArguments() {
            return inputArguments;
        }

        @Override
        public int getOutputArguments() {
            return 1;
        }

        @Override
        public ExtSourceProperties getExtSourceProperties() {
            return new ExtSourceProperties();
        }

        @Override
        public IAnswer retrieve(final ISolverContext ctx, final IQuery query) {
            //System.out.println("in retrieve!");
            final StringBuffer b = new StringBuffer();
            b.append("\"");
            for (final ISymbol sym : query.getInput()) {
                final String value = sym.value();
                //System.out.println("got value "+value.toString());
                if (value.startsWith("\"")) {
                    b.append(value.substring(1, value.length() - 1));
                } else {
                    b.append(value);
                }
            }
            b.append("\"");
            //System.out.println("returning constant "+b.toString());

            final Answer answer = new Answer();
            final ArrayList<ISymbol> t = new ArrayList<ISymbol>(1);
            t.add(ctx.storeConstant(b.toString()));
            answer.output(t);
            return answer;
        }
    }

    @Override
    public String getName() {
        return "ConcatSetMinusTestPlugin";
    }

    @Override
    public AbstractCollection<IPluginAtom> createAtoms() {
        final LinkedList<IPluginAtom> atoms = new LinkedList<IPluginAtom>();
        atoms.add(new ConcatAtom());
        return atoms;
	}
}