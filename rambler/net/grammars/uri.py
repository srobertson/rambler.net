from __future__ import with_statement
from collections import deque
import string
import sys


from Rambler.grammar import (And, Literal, Octet, Optional, OneOrMore, Or, 
  Parser, ParseError, State, Word, ZeroOrMore,
  ALPHA,DIGIT,ALPHANUM,HEXDIG)
  
  

__test__ = {}

sub_delims    = Octet(*(list("!$&'()*+,;=")))
gen_delims    = Octet(*(list(":/?#[]@")))
reserved      = Octet(gen_delims, sub_delims)
unreserved    = Octet(ALPHA, DIGIT,  "-" , "." , "_" , "~")


class PctEncoded(And):
  """Decodes '%' HEXDIG HEXDIG to the coresponding ascii character.
  
  >>> pct_encoded = PctEncoded()
  >>> with Parser(pct_encoded) as parser:
  ...   for c in "%20":
  ...     parser.feed(c)
  
  >>> pct_encoded.value
  ' '
  
  """
  def __init__(self, **kw):
    super(And, self).__init__('%', HEXDIG(), HEXDIG(), **kw)
    
  def enter(self):
    self._value = None
    super(PctEncoded,self).enter()
    
  def exit(self):
    hex_digits = ''.join([s.value for s in self.states[1:]])
    self._value = chr(int(hex_digits, 16))
    super(PctEncoded,self).exit()
  
  @property  
  def value(self):
    return self._value

pchar_octet   = Octet(unreserved, sub_delims, ":" ,"@")
pchar         = Or(pchar_octet, PctEncoded()) 

__test__['pchar'] = """
>>> with Parser(OneOrMore(pchar)) as parser:
...   for c in 'hi%20mom':
...     parser.feed(c)
"""

query         = ZeroOrMore(Or(Octet(pchar_octet, ":" ,"@","/", "?"), PctEncoded()))
fragment      = ZeroOrMore(Or(Octet(pchar_octet, ":" ,"@","/", "?"), PctEncoded()))

segment       = ZeroOrMore(pchar)
segment_nz    = OneOrMore(pchar)
segment_nz_nc = OneOrMore(Or(Octet(unreserved, sub_delims, '@'), PctEncoded()))



path_abempty  = ZeroOrMore(And('/', segment), name="path_abempty")
__test__['path_abempty'] ="""
>>> with Parser(path_abempty) as parser:
...   for c in '/blah/fooey':
...     parser.feed(c)


>>> with Parser(path_abempty) as parser:
...   for c in '/':
...     parser.feed(c)

>>> with Parser(path_abempty) as parser:
...   for c in '':
...    parser.feed(c)

"""

path_absolute = And("/", Optional(segment_nz(),  path_abempty()), name='path_absolute')
__test__['path_absolute'] ="""
Except path's that start with /

>>> with Parser(path_absolute) as parser:
...   for c in '/blah/fooey':
...    parser.feed(c)

But not //

>>> try:
...   with Parser(path_absolute) as parser:
...     for c in '//':
...       parser.feed(c)
...   assert False, 'should throw parse error'
... except ParseError:
...   pass

"""

path_noscheme =  And(segment_nz_nc(),  path_abempty(), name='path_noscheme')
path_rootless = And(segment_nz(), path_abempty(), name='path_rootless')

path = Or(path_abempty(), path_absolute(), path_noscheme, path_rootless)

__test__['path'] ="""
>>> with Parser(path) as parser:
...   for c in '/blah/fooey':
...    parser.feed(c)


>>> "".join(path.value)
'/blah/fooey'


>>> with Parser(path) as parser:
...   for c in '/':
...    parser.feed(c)

>>> "".join(path.value)
'/'

 
"""

reg_name      = ZeroOrMore(Or(Octet(unreserved, sub_delims), PctEncoded()), name='reg_name')
Number        = Word(string.digits, name='number')
IPv4address   = And(Number(), '.', Number(), '.', Number(), '.', Number(), name='IPv4address')
__test__['IPv4address'] ="""
>>> with Parser(IPv4address) as parser:
...   for c in '192.168.0.1':
...     parser.feed(c)

>>> "".join(IPv4address.value)
'192.168.0.1'
"""

# TODO: Figure out how to implement greedy state to use this more exact rule
# dec_octet     = Or(
#   And(Literal("25"), Octet("0-5"), name="250-255"),     # 250 -255
#   And(Octet("2"), Octet("0-4"), DIGIT, name="200-249"), # 200-249
#   And(Octet("1"), DIGIT, DIGIT, name="100-199"),        # 100-199
#   And(Octet('1-9'), DIGIT, name="10-99"),             #   10-99
#   DIGIT(name="0-9"))                              #     0-9
# 
# __test__['dec_octet'] ="""
# >>> with Parser(dec_octet, debug=True) as parser:
# ...  for c in '255':
# ...    parser.feed(c)
# 
# >>> dec_octet.value
# 
# """

port          = Optional(':', Number(), name='optional_port')
host          = Or(IPv4address, reg_name, name='host')
userinfo      = ZeroOrMore(Or(Octet(unreserved, sub_delims, ':'), PctEncoded()))
authority     = And(Optional(And(userinfo, '@')), host, port)
__test__['authority']="""
>>> with Parser(authority) as parser:
...   for c in "user@example.com":
...     parser.feed(c)

>>> "".join(authority.value)
'user@example.com'

>>> with Parser(authority) as parser:
...   for c in "example.com":
...     parser.feed(c)

>>> "".join(authority.value)
'example.com'


"""

scheme        = Word(string.letters, string.letters + string.digits + "+-.", name='scheme')
# todo add path-empty
relative_part = Or(And('//', path_abempty), path_absolute(), path_noscheme())
relative_ref  = And(relative_part, Optional(And("?", query)), Optional("#", fragment))

hier_part     = Or(And("//", authority, path_abempty(name='authority_path_abempty')),
                 path_absolute(),
                 path_rootless(),
                 )#/ path-empty

absolute_URI  = And(scheme, ":", hier_part(), Optional("?", query)) 
__test__['absolute_URI'] = """

>>> with Parser(absolute_URI) as parser:
...   for c in 'http://example.com':
...     parser.feed(c)


>>> ''.join(absolute_URI.value) #1
'http://example.com'

>>> with Parser(absolute_URI) as parser:
...   for c in 'http://user@example.com:80':
...     parser.feed(c)

>>> ''.join(absolute_URI.value) #2
'http://user@example.com:80'


>>> with Parser(absolute_URI) as parser:
...   for c in 'http://user@example.com:80/a?':
...     parser.feed(c)

>>> ''.join(absolute_URI.value) #2
'http://user@example.com/a?'



"""




if __name__ == '__main__':
   import doctest
   doctest.testmod()
   