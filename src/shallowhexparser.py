"""
this parser can be used as follows:

import shallowhexparser
structure = shallowhexparser.parse(text)

The parser recognizes all HEX/ASP programs but distinguishes
in the structure only the following structural elements:

 * content is a list of statements
 * statement is an elist or a rule (terminated with .)
 * a rule contains two seplists (separated lists) next to ":-" or ":~"
 * a seplist is a nonempty separated list of elists
 * an elist is a nonempty sequence of elements
 * an element is a string, integer, or other token,
              or a bracket around a seplist

"""

import ply.lex as lex
import ply.yacc as yacc

import sys
import inspect

DEBUG=True

literals = ('(', ')', '[', ']', '{', '}', ',', ';')
tokens = ('STRING', 'INTEGER', 'SEPRULE', 'SEPCOL', 'STOP', 'OTHER')

def message(s):
  sys.stderr.write(s+'\n')

class alist(list):
  def __init__(self, what, content):
    list.__init__(self, [what]+content)
  def __repr__(self):
    return 'alist_{}_{}'.format(self[0], repr(self[1:]))
  __str__ = __repr__

# count line numbers and ignore them
def t_newline(t):
  r'[\r\n]+'
  t.lexer.lineno += len(t.value)
  # return nothing -> token does not go to parser
  return

def t_COMMENT(t):
  r'%[^\r\n]*'
  # return nothing -> token does not go to parser
  pass

t_ignore = ' \t'

t_STOP = '[?.]'
t_SEPRULE = r':[~-]'
t_SEPCOL = r':(?![~-])'
t_STRING = r'"[^"]*"'
t_INTEGER = r'[0-9]+'
t_OTHER = r'[^()\[\]{},:;.?\r\n\t" ]+'

def t_error(t):
  msg = "unexpected character '{}'\n".format(repr(t))
  raise Exception(msg)
  #t.lexer.skip(1)

mylexer = lex.lex()

start='content'

def p_content_1(p):
  'content : statement content'
  p[0] = [ p[1] ] + p[2]
def p_content_2(p):
  'content : '
  p[0] = [ ]

def p_statement(p):
  '''
  statement : rule STOP '[' expandlist ']'
            | rule STOP
            | disjlist STOP
  '''
  if len(p) == 6:
    p[0] = p[1] + alist('[', p[4])
  else:
    p[0] = p[1]

def p_rule_1(p):
  'rule : disjlist SEPRULE disjlist'
  p[0] = alist(p[2], [p[1], p[3]])
def p_rule_2(p):
  'rule : SEPRULE disjlist'
  p[0] = alist(p[1], [None, p[2]])

def p_disjlist(p):
  '''
  disjlist : semicollist
           | expandlist
  '''
  p[0] = p[1]

def p_semicollist_1(p):
  "semicollist : semicollist ';' expandlist"
  p[0] = p[1] + [p[3]]
def p_semicollist_2(p):
  "semicollist : expandlist ';' expandlist"
  p[0] = alist(';', [p[1], p[3]])


def p_expandlist(p):
  '''
  expandlist : collist
             | conjlist
  '''
  p[0] = p[1]

def p_collist_1(p):
  "collist : collist SEPCOL conjlist"
  p[0] = p[1] + [p[3]]
def p_collist_2(p):
  "collist : conjlist SEPCOL conjlist"
  p[0] = alist(':', [p[1], p[3]])

def p_conjlist(p):
  '''
  conjlist : commalist
           | elist
  '''
  p[0] = p[1]

def p_commalist_1(p):
  "commalist : commalist ',' elist"
  p[0] = p[1] + [p[3]]
def p_commalist_2(p):
  "commalist : elist ',' elist"
  p[0] = alist(',', [p[1], p[3]])

def p_elist_1(p):
  'elist : eterm elist'
  p[0] = [p[1]] + p[2]
def p_elist_2(p):
  'elist : eterm'
  p[0] = [p[1]]

def p_eterm_1(p):
  '''
  eterm : '(' disjlist ')'
        | '{' disjlist '}'
        | '[' disjlist ']'
  '''
  p[0] = alist(p[1], p[2])

def p_eterm_2(p):
  '''
  eterm : '(' ')'
        | '[' ']'
        | '{' '}'
  '''
  p[0] = alist(p[1], [])

def p_eterm_3(p):
  '''
  eterm : STRING
        | INTEGER
        | OTHER
  '''
  p[0] = p[1]

def p_error(p):
  msg = "unexpected '{}'\n".format(repr(p))
  raise Exception(msg)

myparser = yacc.yacc()

def parse(content):
  return myparser.parse(content, lexer=mylexer, debug=False)

if __name__ == '__main__':
  import os, traceback, logging
  logging.basicConfig(
    level=logging.DEBUG,
    format="%(filename)10s:%(lineno)4d:%(message)s",
    stream=sys.stderr
  )
  dbglog = logging.getLogger()
  TESTSDIR='../tests/'
  lok, pok, lfail, pfail = 0, 0, 0, 0
  #for t in ['setminuspartial2.hex']:
  for t in os.listdir(TESTSDIR):
    if t.endswith('.hex'):
      s = open(TESTSDIR+t, 'r').read()
      try:
        mylexer.input(s)
        toks = [tok for tok in mylexer]
        message('LOK: '+t)
        lok += 1
        #if DEBUG:
        #  print('LRES: '+repr(toks))
      except:
        message('LFAIL: '+t)
        lfail += 1
        if DEBUG:
          message('===\n'+s+'\n===')
          try:
            mylexer.lex(s, lexer=mylexer, debug=dbglog)
          except:
            pass
        message('EXC: '+traceback.format_exc())

      try:
        r = parse(s)
        pok += 1
        message('POK: '+t)
        #if DEBUG:
        #  message('===\n'+s+'\n===')
        message('PRES: '+repr(r))
      except:
        message('FAIL: '+t)
        pfail += 1
        if DEBUG:
          message('===\n'+s+'\n===')
          try:
            myparser.parse(s, lexer=mylexer, debug=dbglog)
          except:
            pass
        message('EXC: '+traceback.format_exc())
  message("LOK {} LFAIL {} POK {} FFAIL {}".format(lok, lfail, pok, pfail))
