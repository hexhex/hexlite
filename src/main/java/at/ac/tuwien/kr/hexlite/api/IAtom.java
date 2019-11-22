package at.ac.tuwien.kr.hexlite.api;

public interface IAtom extends ISymbol {
    public boolean isTrue();
    public boolean isFalse();
    public boolean isUnknown();
}
