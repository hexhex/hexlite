package at.ac.tuwien.kr.hexlite.api;

import java.util.AbstractCollection;

/**
 * Most methods correspond to the C++ interface.
 * 
 * Some things have been omitted.
 */
public interface IPlugin {
    public String getName();

    public AbstractCollection<IPluginAtom> createAtoms();
}