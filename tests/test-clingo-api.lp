#script (python)
import clingo
F = clingo.Function

def a():
  return [clingo.Function('a'), clingo.Function('b')]
#end.

interesting1(a) :- not a = @a().
interesting1(b) :- not b = @a().
interesting2(a) :- not a = X : X = @a().
interesting2(b) :- not b = X : X = @a().
interesting3(X) :- X = @a().

aux(X) :- X = @a().
interesting4(a) :- not aux(a).
interesting4(b) :- not aux(b).

interesting5(a) :- a != @a().
interesting5(b) :- b != @a().
