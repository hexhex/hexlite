package at.ac.tuwien.kr.hexlite.testplugin;

import java.util.AbstractCollection;
import java.util.AbstractSet;
import java.util.ArrayList;
import java.util.LinkedList;
import java.util.HashSet;

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
            boolean outputString = false;
            for (final ISymbol sym : query.getInput()) {
                final String value = sym.value();
                //System.out.println("got value "+value.toString());
                if (value.startsWith("\"")) {
                    b.append(value.substring(1, value.length() - 1));
                    outputString = true;
                } else {
                    b.append(value);
                }
            }
            //System.out.println("returning constant "+b.toString());

            final Answer answer = new Answer();
            final ArrayList<ISymbol> t = new ArrayList<ISymbol>(1);
            if( outputString ) {
                t.add(ctx.storeString(b.toString()));
            } else {
                // TODO handle integers explicitly or use storeParseable
                t.add(ctx.storeConstant(b.toString()));
            }
            answer.output(t);
            return answer;
        }
    }

    public class SetMinusAtom implements IPluginAtom {
        // def testSetMinus(p, q):
        // # is true for all constants in extension of p but not in extension of q
        // pset, qset = set(), set()
        // for x in dlvhex.getTrueInputAtoms():
        // 	tup = x.tuple()
        // 	if tup[0].value() == p.value():
        // 		pset.add(tup[1].value())
        // 	elif tup[0].value() == q.value():
        // 		qset.add(tup[1].value())
        // rset = pset - qset
        // for r in rset:
        // 	dlvhex.output( (r,) )

        private final ArrayList<InputType> inputArguments;

        public SetMinusAtom() {
            inputArguments = new ArrayList<InputType>();
            inputArguments.add(InputType.PREDICATE);
            inputArguments.add(InputType.PREDICATE);
        }

        @Override
        public String getPredicate() {
            return "testSetMinus";
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
            //System.out.println("in retrieve! with input "+query.getInput());
            // implementation 1: via ISymbol::extension()
            final ISymbol predp = query.getInput().get(0);
            final ISymbol predq = query.getInput().get(1);
            //System.out.println("getting extension setp");
            final HashSet<ArrayList<ISymbol> > setp = predp.extension();
            //System.out.println("getting extension setq");
            final HashSet<ArrayList<ISymbol> > setq = predq.extension();
            //System.out.println("got setp "+setp.toString()+" setq "+setq.toString());
            final HashSet<ArrayList<ISymbol> > result = new HashSet<ArrayList<ISymbol> >();
            //System.out.println("adding to result");
            for(ArrayList<ISymbol> i: setp) {
                //System.out.println(" adding " + i.toString());
                result.add(i);
            }
            //System.out.println("result " + result.toString() + " next removing");
            for(ArrayList<ISymbol> j: setq) {
                //System.out.println(" removing " + j.toString());
                result.remove(j);
            }
            //System.out.println("result " + result.toString() + " next returning");

            // // implementation 2: via IInterpretation.getTrueInputAtoms()
            // final IInterpretation in = query.getInterpretation();
            // AbstractSet<AbstractList<ISymbol> > setp = new HashSet<AbstractList<ISymbol> >();
            // AbstractSet<AbstractList<ISymbol> > setq = new HashSet<AbstractList<ISymbol> >();
            // for(ISymbol atm : in.getTrueInputAtoms()) {
            //     final AbstractList<ISymbol> args = atm.tuple().subList(1,len(atm.tuple()-1));
            //     if(atm.tuple().at(0) == predp)
            //         setp.add(args);
            // }
            
            final Answer answer = new Answer();
            for(ArrayList<ISymbol> t: result) {
                answer.output(t);
            }
            //System.err.println("for input "+setp.toString()+" and "+setq.toString()+" producing result "+result.toString());

            return answer;
        }
    }

    @Override
    public String getName() {
        return "ConcatSetMinusPlugin";
    }

    @Override
    public AbstractCollection<IPluginAtom> createAtoms() {
        final LinkedList<IPluginAtom> atoms = new LinkedList<IPluginAtom>();
        atoms.add(new ConcatAtom());
        atoms.add(new SetMinusAtom());
        return atoms;
	}
}
