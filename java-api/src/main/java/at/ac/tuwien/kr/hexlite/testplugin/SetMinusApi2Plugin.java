// compared to ConcatSetMinusPlugin, this implementation uses getTrueInputAtoms()
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
import at.ac.tuwien.kr.hexlite.api.IInterpretation;

public class SetMinusApi2Plugin implements IPlugin {
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
            // implementation 2: via IInterpretation::getTrueInputAtoms()
            final ISymbol predp = query.getInput().get(0);
            final ISymbol predq = query.getInput().get(1);

            final IInterpretation in = query.getInterpretation();
            HashSet<ArrayList<ISymbol> > setp = new HashSet<ArrayList<ISymbol> >();
            HashSet<ArrayList<ISymbol> > setq = new HashSet<ArrayList<ISymbol> >();
            //System.out.println("predp is "+predp.toString()+" predq is "+predq.toString());
            for(ISymbol atm : in.getTrueInputAtoms()) {
                final ArrayList<ISymbol> args = new ArrayList<ISymbol>( atm.tuple().subList(1,atm.tuple().size()) );
                //System.out.println("true input atom "+atm.toString()+" with tuple "+atm.tuple().toString()+" and args "+args.toString());
                //System.out.println("atm.tuple().get(0) is "+atm.tuple().get(0).toString());
                if(atm.tuple().get(0).equals(predp) )
                    setp.add(args);
                if(atm.tuple().get(0).equals(predq) )
                    setq.add(args);
            }
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
        return "SetMinusApi2Plugin";
    }

    @Override
    public AbstractCollection<IPluginAtom> createAtoms() {
        final LinkedList<IPluginAtom> atoms = new LinkedList<IPluginAtom>();
        atoms.add(new SetMinusAtom());
        return atoms;
	}
}