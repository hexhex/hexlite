package at.ac.tuwien.kr.hexlite.api;

public class ExtSourceProperties {
    protected boolean providesPartialAnswer;

    public ExtSourceProperties() {
        providesPartialAnswer = false;
    }

    public void setProvidesPartialAnswer(boolean b) {
        providesPartialAnswer = b;
    }

    public boolean getProvidesPartialAnswer() {
        return providesPartialAnswer;
    }
}
