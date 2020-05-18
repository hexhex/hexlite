import clingo

import logging
import sys

class GroundProgramPrinter:
  def __init__(self):
    # first collect rules
    self.rules = []
    self.weightrules = []
    # then get atom mapping
    # (clasp non-fact atoms)
    self.int2atom = {} # int to str

  def __output(self, what):
    sys.stderr.write(what+'\n')

  class WarnMissing:
    def __init__(self, name):
      self.name = name
    def __call__(self, *arguments):
      logging.warning("GPPWarning {} {}".format(self.name, repr(arguments)))
  def __getattr__(self, name):
    return self.WarnMissing(name)

  def output_atom(self, symbol, atom):
    logging.debug("GPPAtom symb=%s atm=%s", repr(symbol), repr(atom))
    if atom == 0:
      # 0 is a signal that the symbol is a fact
      self.__output(str(symbol)+'.')
    else:
      # do not print atoms that are not facts
      self.int2atom[atom] = str(symbol)

  def __lit2str(self, integer):
    iabs = abs(integer)
    try:
      istr = self.int2atom[iabs]
    except KeyError:
      istr = 'claspaux'+str(iabs)
    if integer > 0:
      return istr
    else:
      return "not "+ istr

  def __formatHead(self, choice, head):
    head = [ self.__lit2str(x) for x in head ]
    if not choice:
      # disjunctive rule or constraint
      return ' ; '.join(head)
    else:
      # choice rule
      return '{ '+' ; '.join(head)+' }'

  def rule(self, choice, head, body):
    logging.debug("GPPRule ch=%s hd=%s b=%s", repr(choice), repr(head), repr(body))
    self.rules.append( (choice, head, body) )

  def weight_rule(self, choice, head, lower_bound, body):
    logging.debug("GPPWeightRule ch=%s hd=%s lb=%s, b=%s", repr(choice), repr(head), repr(lower_bound), repr(body))
    self.weightrules.append( (choice, head, lower_bound, body) )

  def init_program(self, incr):
    logging.debug("GPPInit")
  def begin_step(self):
    logging.debug("GPPBeginStep")

  def end_step(self):
    logging.debug("GPEndStep")
    self.__output("GroundProgramPrinter START")
    def formatElement(idx, e):
      ilit, weight = e
      a = self.__lit2str(ilit)
      #return "{w},{idx}:{a}".format(a=a, idx=idx, w=weight)
      return "{w}:{a}".format(a=a, idx=idx, w=weight)
    for choice, head, body in self.rules:
      hstr = self.__formatHead(choice, head)
      body = [ self.__lit2str(x) for x in body ]
      bstr = ', '.join(body)
      self.__output(hstr+' :- '+bstr+'.')
    for choice, head, lower_bound, body in self.weightrules:
      hstr = self.__formatHead(choice, head)
      selems = ';'.join([formatElement(idx, e) for idx, e in enumerate(body)])
      self.__output(hstr+' :- '+str(lower_bound)+' <= #sum { '+selems + ' }.')
    self.__output("GroundProgramPrinter END")
