# This parser should be able to parse most ASP-related languages, including HEX and ASP-Core-2.

# HEXLite Python-based solver for a fragment of HEX
# Copyright (C) 2017  Peter Schueller <schueller.p@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
The parser can be used as follows:

import shallowhexparser
structure = shallowhexparser.parse(text)
structure = shallowhexparser.parseTerm(text)

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
import logging

literals = ('(', ')', '[', ']', '{', '}', ',', ';')
tokens = ('STRING', 'INTEGER', 'SEPRULE', 'SEPCOL', 'STOP', 'OTHER', 'OPERATOR')

def message(s):
  logging.info(s)

class alist(list):
  '''
  a generic list with some special properties
  used to store lists separated by ',' or ':' or ';'
  used to store lists enclosed with '()' or '[]' or '{}'
  '''
  def sleft(self):
    if self.left:
      return self.left
    else:
      return ''
  def sright(self):
    if self.right:
      return self.right
    else:
      return ''
  def ssep(self):
    if self.sep:
      return self.sep
    else:
      return ''
  def __init__(self, content=[], left=None, right=None, sep=None):
    #logging.debug("alist.__init__ {} {} {} {}".format(repr(content), left, right, sep))
    assert(isinstance(content, list) and not isinstance(content, alist))
    class MyError(Exception):
      pass
    def takeOrThrow(first, second):
      if first is None:
        return second
      elif second is None:
        return first
      else:
        raise MyError()
    # collapse one-element-alists if left, right, sep can be merged without losing information
    if not isinstance(content, alist) and len(content) == 1 and isinstance(content[0], alist):
      try:
        self.left = takeOrThrow(left, content[0].left)
        self.right = takeOrThrow(right, content[0].right)
        self.sep = takeOrThrow(sep, content[0].sep)
        list.__init__(self,[ x for x in content[0] ])
        #logging.debug("alist.__init__ incorporated {} {} {} {}".format(repr(content), left, sep, right))
        return
      except MyError:
        # if not possible continue with normal constructor
        pass
    list.__init__(self, content)
    self.left = left
    self.right = right
    self.sep = sep

  def dupModify(self, content=None, left=None, right=None, sep=None):
    out = alist(self.content, self.left, right.left, sep=sep)
    if content:
      out.content = content
    if left:
      out.left = left
    if right:
      out.right = right
    if sep:
      out.sep = sep
    return out

  def __add__(self, other):
    # preserve list property
    if isinstance(other, alist):
      assert(other.left == self.left and other.right == self.right and other.sep == self.sep)
    return alist(list.__add__(self, other), self.left, self.right, self.sep)

  def __repr__(self):
    left = 'alist<{}^{}^{}<'.format(self.left, self.sep, self.right)
    right = '>>'
    return '{}{}{}'.format(left, list.__repr__(self), right)
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
t_OPERATOR = r'(==|=|!=|<=|>=|<>|<|>|@)'
t_OTHER = r'[^()\[\]{}@=!<>,:;.?\r\n\t" ]+'

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
    p[0] = [alist([p[1]], right='.'), alist([p[4]], left='[', right=']')]
  else:
    p[0] = alist([p[1]], right='.')

def p_rule(p):
  '''
  rule : disjlist SEPRULE disjlist
       | SEPRULE disjlist
  '''
  if len(p) == 4:
    head = p[1]
    sep = p[2]
    body = p[3]
  else:
    head = None
    sep = p[1]
    body = p[2]
  if not isinstance(body, alist) or body.sep != ',':
    # make sure every rule body is a conjunction
    body = alist([body], sep=',')
  p[0] = alist([head, body], sep=sep)

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
  p[0] = alist([p[1], p[3]], sep=';')


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
  p[0] = alist([p[1], p[3]], sep=':')

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
  p[0] = alist([p[1], p[3]], sep=',')

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
  p[0] = alist([p[2]], left=p[1], right=p[3])

def p_eterm_2(p):
  '''
  eterm : '(' ')'
        | '[' ']'
        | '{' '}'
  '''
  p[0] = alist([], left=p[1], right=p[2])

def p_eterm_3(p):
  '''
  eterm : STRING
        | INTEGER
        | OPERATOR
        | OTHER
  '''
  p[0] = p[1]

def p_error(p):
  msg = "unexpected '{}'\n".format(repr(p))
  raise Exception(msg)

# TODO manage installation of yacc-generated scripts somehow and reactivate write_tables
# , optimize=not __debug__
myparser = yacc.yacc(start='content', write_tables=False)
mytermparser = yacc.yacc(start='elist', write_tables=False, errorlog=None)

def parseTerm(content):
  '''
  this is a method you can use from outside the module!
  '''
  return mytermparser.parse(content, lexer=mylexer, debug=False)

def parse(content):
  '''
  this is a method you can use from outside the module!
  '''
  return myparser.parse(content, lexer=mylexer, debug=False)

def testparse():
  DEBUG=False
  dbglog = logging.getLogger()
  TESTSDIR='../tests/'
  lok, pok, lfail, pfail = 0, 0, 0, 0
  for t in os.listdir(TESTSDIR):
    if t.endswith('.hex'):
      s = open(TESTSDIR+t, 'r').read()
      try:
        mylexer.input(s)
        toks = [tok for tok in mylexer]
        message('LOK: '+t)
        lok += 1
        #if DEBUG:
        #  message('LRES: '+repr(toks))
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
        if DEBUG:
          #message('===\n'+s+'\n===')
          message(pprint.pformat(r))
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

def shallowprint(x):
  if isinstance(x, alist):
    ret = (
      x.sleft() +
      (' '+x.ssep()+' ').join(
        [ shallowprint(y) for y in x]) + 
      x.sright())
    if ret.endswith('.'):
      ret += '\n'
    return ret
  if isinstance(x, list):
    return ' '.join([ shallowprint(y) for y in x ])
  if isinstance(x, str):
    return x
  if isinstance(x, int):
    return str(x)
  if x is None:
    return ''
  raise Exception("unexpected "+repr(x))

def testprint():
  TESTSDIR='../tests/'
  for t in os.listdir(TESTSDIR):
    if t.endswith('.hex'):
      try:
        s = open(TESTSDIR+t, 'r').read()
        r = parse(s)
        prt = shallowprint(r)
        message('===\n'+prt+'\n===')
        #p = subprocess.Popen('clingo', shell=True,
        #  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #out, err = p.communicate(prt.encode('utf8'))
        #if p.returncode != 0:
        #  message("clingo failed\n"+err.decode('utf8'))
      except:
        message('EXC: '+traceback.format_exc())

def main():
  logging.basicConfig(
    level=logging.DEBUG,
    format="%(filename)10s:%(lineno)4d:%(message)s",
    stream=sys.stdout
  )
  testparse()
  testprint()

if __name__ == '__main__':
  import os, traceback, pprint, subprocess
  main()

