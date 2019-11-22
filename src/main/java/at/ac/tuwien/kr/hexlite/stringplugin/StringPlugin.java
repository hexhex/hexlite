package at.ac.tuwien.kr.hexlite.stringplugin;

import java.util.AbstractCollection;
import java.util.ArrayList;
import java.util.LinkedList;

import at.ac.tuwien.kr.hexlite.api.Answer;
import at.ac.tuwien.kr.hexlite.api.ExtSourceProperties;
import at.ac.tuwien.kr.hexlite.api.IPlugin;
import at.ac.tuwien.kr.hexlite.api.IPluginAtom;
import at.ac.tuwien.kr.hexlite.api.ISolverContext;
import at.ac.tuwien.kr.hexlite.api.ISymbol;

public class StringPlugin implements IPlugin {
    public class ConcatAtom implements IPluginAtom {
        private final ArrayList<InputType> inputArguments;

        public ConcatAtom() {
            inputArguments = new ArrayList<InputType>();
            inputArguments.add(InputType.TUPLE);
        }

        @Override
        public String getPredicate() {
            return "concat";
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
            final StringBuffer b = new StringBuffer();
            b.append("\"");
            for (final ISymbol sym : query.getInput()) {
                final String name = sym.getName();
                switch (sym.getType()) {
                case CONSTANT:
                    if (name.startsWith("\"")) {
                        b.append(name.substring(1, name.length() - 1));
                    } else {
                        b.append(name);
                    }
                    break;
                case FUNCTION:
                case INTEGER:
                case TUPLE:
                    b.append(sym.toString());
                    break;
                }
            }
            b.append("\"");

            final Answer answer = new Answer();
            final ArrayList<ISymbol> t = new ArrayList<ISymbol>(1);
            t.add(ctx.storeConstant(b.toString()));
            answer.output(t);
            return answer;
        }
    }

    @Override
    public String getName() {
        return "TestStringPlugin";
    }

    @Override
    public AbstractCollection<IPluginAtom> createAtoms() {
        final LinkedList<IPluginAtom> atoms = new LinkedList<IPluginAtom>();
        atoms.add(new ConcatAtom());
        return atoms;
	}
}