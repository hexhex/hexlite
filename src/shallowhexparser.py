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

literals = ('(', ')', '[', ']', '{', '}', '.', ',')
tokens = ('STRING', 'INTEGER', 'SEPRULE', 'SEPCOL', 'OTHER', 'COMMENT')

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

t_SEPRULE = r':-'
t_SEPCOL = r':'
t_STRING = r'"[^"]*"'
t_INTEGER = r'[0-9]+'
t_OTHER = r'[^()\[\]{},:;.\r\n\t" ]+'

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
  'content : statement'
  p[0] = [ p[1] ]

def p_statement(p):
  '''
  statement : rule '.'
            | elist '.'
  '''
  p[0] = alist('.', p[1])

def p_rule(p):
  '''
  rule : seplist SEPRULE seplist
       | SEPRULE seplist
  '''
  if len(p) == 4:
    p[0] = alist(p[2], [p[1], p[3]])
  else:
    p[0] = alist(p[1], [None, p[2]])

def p_seplist(p):
  '''
  seplist : commalist
  '''
  if len(p[1]) == 2:
    # remove list from child if it has 1 element
    p[0] = p[1][1]
  else:
    p[0] = p[1]

def p_commalist(p):
  '''
  commalist : commalist ',' elist
            | elist
  '''
  if len(p) == 4:
    p[0] = p[1] + [p[3]]
  else:
    p[0] = alist(',', [p[1]])

def p_elist(p):
  '''
  elist : eterm elist
        | eterm
  '''
  if len(p) == 3:
    p[0] = [p[1]] + p[2]
  else:
    p[0] = [p[1]]
  #raise Exception('TODO '+inspect.stack()[0][3]+' '+repr(p))

def p_eterm_1(p):
  '''
  eterm : '(' seplist ')'
        | '{' seplist '}'
        | '[' seplist ']'
  '''
  p[0] = alist(p[1], p[2])

def p_eterm_2(p):
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

def lexit(content):
  mylexer.input(content)
  return [tok for tok in mylexer]

def parse(content):
  return myparser.parse(content, lexer=mylexer, debug=DEBUG)

if __name__ == '__main__':
  import os, traceback
  TESTSDIR='../tests/'
  for t in ['setminuspartial2.hex']:
  #for t in os.listdir(TESTSDIR):
    if t.endswith('.hex'):
      s = open(TESTSDIR+t, 'r').read()
      try:
        toks = lexit(s)
        print('LOK: '+t)
        if DEBUG:
          print('===\n'+s+'\n===')
          print('LRES: '+repr(toks))

        r = parse(s)
        print('POK: '+t)
        if DEBUG:
          print('===\n'+s+'\n===')
        print('PRES: '+repr(r))
      except:
        print('FAIL: '+t)
        if DEBUG:
          print('===\n'+s+'\n===')
        print('EXC: '+traceback.format_exc())
