package at.ac.tuwien.kr.hexlite.api;

public class ExtSourceProperties {
    protected boolean providesPartialAnswer;

    public ExtSourceProperties() {
        providesPartialAnswer = false;
        doInputOutputLearning = true;
    }

    public void setDoInputOutputLearning(boolean b) {
        doInputOutputLearning = b;
    }

    public boolean getDoInputOutputLearning() {
        return doInputOutputLearning;
    }

    public void setProvidesPartialAnswer(boolean b) {
        providesPartialAnswer = b;
    }

    public boolean getProvidesPartialAnswer() {
        return providesPartialAnswer;
    }
}
