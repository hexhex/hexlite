# This file defines the (very) basic datastructure used for (very permissive) parsing.

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

def findVariables(structure):
  # XXX maybe we want a "findFreeVariables" and not search for variables within aggregate bodies ...
  return deepCollect(structure,
    lambda x: isinstance(x, str) and x[0].isupper())

def dfVisit(structure, visitor):
  'depth-first traversal of structure, calls visitor on everything'
  if isinstance(structure, list):
    for elem in structure:
      dfVisit(elem, visitor)
  visitor(structure)

def deepCollect(liststructure, condition):
  'recursively traverses liststructure and retrieves items where condition is true'
  out = []
  def recursiveCollect(structure):
    if condition(structure):
      out.append(structure)
    if isinstance(structure, list):
      for elem in structure:
        recursiveCollect(elem)
  recursiveCollect(liststructure)
  return out

def deepCollectAtDepth(liststructure, depthfilter, condition):
  'recursively traverses liststructure and retrieves items where condition is true at depth in depthfilter'
  out = []
  def recursiveCollectAtDepth(structure, depth):
    if depthfilter(depth) and condition(structure):
      out.append(structure)
    if isinstance(structure, list):
      for elem in structure:
        recursiveCollectAtDepth(elem, depth+1)
  recursiveCollectAtDepth(liststructure, 0)
  return out
