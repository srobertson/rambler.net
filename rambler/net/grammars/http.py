from __future__ import with_statement
import string
import sys
from collections import deque

from Rambler import outlet

from Rambler.grammar import (And, Enclosure, Literal, Octet, Octets, Optional, OneOrMore, 
Or, Parser, ParseError, State, Word, ZeroOrMore,
ALPHA, DIGIT, HEXDIG
)
import uri
__test__={}
# Sec 2.2

# todo: maybe use/share what's definde in url?
CHAR    = Octet((0,127))
DIGIT   = Octet('0-9')
CTL     = Octet((0,31),(127,127))
CR      = Octet('\r')
LF      = Octet('\n')
SP      = Octet(' ')
HT      = Octet('\t')
QUOTE   = Octet('"')
CRLF    = Literal('\r\n')

LWS     = And(CRLF, OneOrMore(Or(SP,HT)))
TEXT           = Octet((32,126),(128, 255), '\t', ' ', name='TEXT')#<any OCTET except CTLs,but including LWS>)


quoted_pair = And(Literal("\\"), CHAR)

# Todo: implement recursive gramars, i.e. comments can contain comments
comment = Enclosure(Literal('('), Or(quoted_pair, Octet),Literal(')'))
#comment        = "(" *( ctext | quoted-pair | comment ) ")"
#ctext          = <any TEXT excluding "(" and ")">

quoted_string = Enclosure(Literal('"'), Or(quoted_pair, Octet))
#quoted-string  = ( <"> *(qdtext | quoted-pair ) <"> )
#qdtext         = <any TEXT except <">>

separators     = Octet(SP, HT, *list('()<>@,;:\"/]?={}') )

# should be not CTL or not separators, todo implement ability to exclude ranges in an octet
token  = Word(string.letters+string.digits+'-.')

# Sec 3.1

HTTP_Version = And(Literal("HTTP/"), OneOrMore(DIGIT), Literal('.'), OneOrMore(DIGIT))

# Sec 3.2


#http_URL = "http:" "//" host [ ":" port ] [ abs_path [ "?" query ]]

# Sec 3.6.1 Chunked Transfer Coding
#Chunked-Body   = *chunk
#                       last-chunk
#                       trailer
#                       CRLF
#

chunk_size     = OneOrMore(HEXDIG, name='chunk_size')
#chunk          = And(chunk_size, CRLF, Body(name='chunk_data'), CRLF)


class Chunked_Body(State):
  def __init__(self):
    pass
#      last-chunk     = 1*("0") [ chunk-extension ] CRLF
#
#      chunk-extension= *( ";" chunk-ext-name [ "=" chunk-ext-val ] )
#      chunk-ext-name = token
#      chunk-ext-val  = token | quoted-string
#      chunk-data     = chunk-size(OCTET)
#      trailer        = *(entity-header CRLF)


#Sec 4.2
field_name = token(name='field_name')

#<the OCTETs making up the field-value
#and consisting of either *TEXT or combinations
#of token, separators, and quoted-string>

field_value = And(ZeroOrMore(SP), token(name='field_value'))
message_header = And(field_name, ':', field_value, CRLF, name='message_header')
__test__['message_header']="""
>>> with Parser(message_header) as parser:
...   for c in 'Content-length: 10\\r\\n':
...     parser.feed(c)
"""

class HTTPHeaders(ZeroOrMore):
  def __init__(self, name='http.headers', **kw):
    super(HTTPHeaders,self).__init__(message_header, name=name, **kw)
    self.headers = {}
    
  def enter(self):
    self.headers = {}
    super(HTTPHeaders, self).enter()
    
  def reduced(self, state, accepted, parser):
    '''Called when measseg_header reduces'''    
    self.headers[state.states[0].value.lower()] = "".join(state.states[2].states[1].value)
    super(HTTPHeaders, self).reduced(state, accepted, parser)

# Sec 5 Request

Method = Or(Literal("OPTIONS"),  # Section 9.2
            Literal("GET"),      # Section 9.3
            Literal("HEAD"),     # Section 9.4
            Literal("POST"),     # Section 9.5
            Literal("PUT"),      # Section 9.6
            Literal("DELETE"),   # Section 9.7
            Literal("TRACE"),    # Section 9.8
            Literal("CONNECT"),  # Section 9.9
            Word(name="extension-method"), name='http.method')
            
Request_URI = Or(Literal('*'), uri.absolute_URI(name='absolute_URI'), uri.path_absolute(name='path_absolute'))
Request_URI = Word(string.letters + string.digits + '/:.-?+%_=&', name='http.path')
Request_Line = And(Method, SP, Request_URI, SP, HTTP_Version, CRLF, name='http.request_line')
__test__['Request_Line'] = """
>>> with Parser(Request_Line()) as parser:
...   stream = "GET / HTTP/1.1\\r\\n"
...   for c in stream:
...     parser.feed(c)

>>> with Parser(Request_Line()) as parser:
...   stream = "GET /foo/blah HTTP/1.1\\r\\n"
...   for c in stream:
...     parser.feed(c)


>>> with Parser(Request_Line()) as parser:
...   stream = "GET http://example.com/foo/blah HTTP/1.1\\r\\n"
...   for c in stream:
...     parser.feed(c)

"""




class Body(State):
  """Reads a stream of text ocasional invoking on_data with the bytes accumulated
  
  >>> class Delegate(object):
  ...  def __init__(self):
  ...    self.data = []
  ...  def on_data(self, state):
  ...    self.data.append(state.value)
  
  >>> delegate = Delegate()
  >>> body = Body(content_length=None, chunk_size=4).add_delegate(delegate)
  >>> with Parser(body) as parser:
  ...   parser.add_callback(delegate.on_data, 'http.data')
  ...   for c in "ABCDEFGHIJKLM":
  ...     parser.feed(c)
  
  >>> delegate.data
  ['ABCD', 'EFGH', 'IJKL', 'M']
  """
  def __init__(self,  content_length=4096, chunk_size=4096, **kw):
    super(Body, self).__init__(**kw)
  
    try:
      self.content_length = int(content_length) # num bytes to accept before invoking on_data
      self.chunk_size = self.content_length
    except TypeError:
      self.content_length = None
      self.chunk_size = chunk_size
      
    self.chunk = Octets(name='http.data')
    
    
  def feed(self, char, parser):

    if not parser.end_of_input:
      self.chunk.content_length = self.chunk_size
      parser.shift(self.chunk)
    else:
      parser.reduce(False)
      
  def reduced(self, state, accepted, parser):
    """Keep reading chunks until we hit the end of our input"""
    # todo: introduce a size that also stops us.
    
    if parser.end_of_input:
      if isinstance(self.content_length,int) and  self.content_length != state.length():
        raise ParseError(self, 'expected to read %s octets' % self.content_length)
      parser.reduce(accepted)
    elif self.content_length is None: 
      # no content_length specified and more to come keep reading
      parser.accept()
    elif self.content_length == state.length():
        parser.reduce(accepted)
      
      
    #if parser.end_of_input:
    #  parser.reduce(accepted)
    #elif accepted:
    #  


class Request(And):
  """
  >>> request = Request()
  >>> with Parser(request) as parser:
  ...   stream = "POST /blah/fooey/ HTTP/1.1\\r\\nHost: localhost\\r\\ncontent-length:3000\\r\\n\\r\\n"
  ...   for c in stream:
  ...     parser.feed(c)
  ...   for c in 'a' * 3000:
  ...     parser.feed(c)


  >>> with Parser(request) as parser:
  ...   stream = "GET http://google.com/ HTTP/1.1\\r\\nHost: google.com\\r\\n\\r\\n"
  ...   for c in stream:
  ...     parser.feed(c)
  """
  
  def __init__(self,**kw):
    self.headers = None
    super(Request,self).__init__(Request_Line(name='http.request_line'), 
              HTTPHeaders(), CRLF(name='content_start'), 
              name='http.request', **kw)
              
  def enter(self):
    if isinstance(self.states[-1], Body):
      del self.states[-1]
    super(Request, self).enter()
    
  def reduced(self, state, accepted, parser):
    if state.name == 'content_start':
      self.method = self.states[0].states[0].value
      if self.method != 'GET':
        content_length = int(self.states[1].headers['content-length'])
        if content_length > 0:
          self.states.append(Body(content_length = content_length))
            
    super(Request, self).reduced(state, accepted, parser)
        
Requests = ZeroOrMore(Request())
    
__test__['Requests']="""

>>> import time
>>> start = time.time()

>>> class Delegate(object):
...   def __init__(self):
...     self.count = 0
...   def on_http_request_line(self, state):
...     self.count += 1
>>> delegate = Delegate()

>>> stream = "POST /blah/fooey/ HTTP/1.1\\r\\nHost: localhost\\r\\ncontent-length:3000\\r\\n\\r\\n" +  ('b'*3000)
>>> stream += "GET http://google.com/ HTTP/1.1\\r\\nHost: google.com\\r\\n\\r\\n"
>>> with Parser(Requests) as parser:
...   parser.add_callback(delegate.on_http_request_line, 'http.request_line')
...   for c in stream:
...     parser.feed(c)


>>> delegate.count
2

#>>> time.time() - start

"""

      
if __name__ == "__main__":
  import doctest
  doctest.testmod()
