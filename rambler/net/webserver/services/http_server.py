import sys
import traceback

from StringIO import StringIO

from webob import Request, Response
from webob.exc import HTTPServerError, HTTPNotFound

from Rambler import outlet, option

class HTTPServer(object):
  """Listens on a port for HTTP Request and dispatches them to WSGI
  compliant callable objecs.
  
  This object relies on another compoent called the
  HTTPRequestMapper which provides finhHandlerFor() method which is
  responsible for returning the appropriat WSGI object that will
  handle the request.

  """
  portFactory  = outlet('PortFactory')
  configService    = outlet('ConfigService')
  lineProtocol     = outlet('LineReceiverProtocol')
  log      = outlet('LogService')
  requestHandler = outlet('HTTPRequestMapper')
  scheduler = outlet('Scheduler')

  listenAddress    = option('http', 'listenAddress', '') # defaults to all addresses
  listenPortNum    = option('http', 'listenPortNum', 8080)
  maxContentLength = option('http', 'maxContentLength', 1048576) # default max is 1MB


  delimiter = '\r\n'
    

  def __init__(self):
    self.requests = {}

  def _testSetup(self):
    """Preforms components binding for test purposes. This method should
    only be called during testing."""
    class DummyRequestMapper:
      def findHandlerFor(self,request):
        return self
      def __call__(self, headers, startResponse):
        status = '200 OK'
        responseHeaders = [('Content-type', 'text/plain')]
        startResponse(status, responseHeaders)
        return "Handeled"


    self.requestHandler = DummyRequestMapper()


  def assembled(self):
    # setup the web stack if we're not testing

    if self.configService.get('RAMBLER_ENV', 'develop') != 'test':
      port = self.portFactory((self.listenAddress, self.listenPortNum))
      lrp = self.lineProtocol()
      lrp.delimiter = self.delimiter

      lrp.delegate = self
      port.delegate = lrp
      port.listen(128) # Start listening for connections

  def onLineFrom(self, line, port):
    """Converts lines of text read from a port with the help of the
    LineRequestProtocol into HTTPRequest objects.

    Here's a raw HTTP/1.1 request as posted by firefox

    >>> rawRequest = ('GET /dialer?phoneNumber=55555 HTTP/1.1\\r\\n'
    ... 'Host: localhost:8080\\r\\n'
    ... 'User-Agent: FakeAgent\\r\\n'
    ... 'Accept: text/xml,application/xml,application/xhtml+xml,text/html;q=0.9,text/plain;q=0.8,image/png,*/*;q=0.5\\r\\n'
    ... 'Accept-Language: en-us,en;q=0.5\\r\\n'
    ... 'Accept-Encoding: gzip,deflate\\r\\nAccept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7\\r\\n'
    ... 'Keep-Alive: 300\\r\\n'
    ... 'Connection: keep-alive\\r\\n'
    ... '\\r\\n')

    We'll fake a port using the handy StreamTransport object.

    >>> httpServer = HTTPServer()
    >>> httpServer._testSetup() # preform component binding for test purposes
    >>> from StringIO import StringIO
    >>> port = StringIO(rawRequest)
    >>> for line in port:
    ...     line = line[:-2] # stringio doesn't strip the trailing \\r\\n
    ...     httpServer.onLineFrom(line, port)

    
    """


    if not self.requests.has_key(port):
      # hmm, port objects don't always have a socket
      #self.log.info(line)
      request_method, uri, server_protocol = line.split(' ')
      try:
        server_name, server_port = port._socket.getsockname()
      except AttributeError:
        server_name, server_port = "", None
        
      environ = {
             'REMOTE_ADDR': str(port._socket.getpeername()[0]),
          'REQUEST_METHOD': request_method,
             'SERVER_NAME': server_name,
             'SERVER_PORT': str(server_port),
         'SERVER_PROTOCOL': server_protocol,
         'rambler.port' : port
            } 
      self.requests[port] = Request.blank(uri, environ=environ)
      return

    request = self.requests[port]
    if line:
      header, value = line.split(':',1)
      request.headers[header] =  value.lstrip()
    else:
      # client is done sending headers, we should look at the
      # content type and do the right thing, such as switch the
      # lrp to raw mode and keep reading.

      #request.endHeaders()
      
      if request.content_length:
        # There's raw data to be read. We'll return how much
        # to the invoker of this method and then we we receive
        # it in onDataFrom we'll handle the request.

        # In the future we might need some sort of limit on
        # contentLength to avoid reading it all intor memory
        # at once. We may have to read the data in chunks and
        # stream it to a file... Right now I don't need large
        # files so no big deal.
        if request.content_length > self.maxContentLength:
          # replace me with proper HTTP Error handling, I
          # think in this case we shoul return a 413
          raise ValueError

        return request.content_length
      else:
        # There's no body, so handle the request
        self.handleRequest(request,port)
        return None # Keep us in line receive mode
      

  def onRawDataFrom(self, stream, port):
    # We got the data we were waiting for, which means we can now handle it
    request = self.requests[port]
    request.environ['wsgi.input'] = StringIO(stream)
    self.handleRequest(request,port)
    
    
  def handleRequest(self, request, port):
    # This is a an experimental integration with the coroutine scheduler, now wsgi
    # apps can return data or a method they need running
    del self.requests[port]
    self.scheduler.call(self._handleRequest, request, port)

  def _handleRequest(self, request, port):
    """Called by onLineFrom or onRawDataFrom to notify us that the Request
    has been fully read and we can begin processing it."""

    try:
      response = self.requestHandler.findHandlerFor(request)        
    except:

      # We got an error while trying to to find a wsgi
      # application to handle the request, log it and try to
      # report something useful to the user.
      exc_info = sys.exc_info()
      self.log.exception('Unexpected Exception encountered while attempting to locate a handler for %s', request.path_info)
      #request.startResponse('500 Unexpeted',(('Content-type', 'text/plain'),),exc_info)
      response = HTTPServerError(detail="".join(traceback.format_exception(*exc_info)), request=request)
      response.text = response.html_body(request.environ)
      

    # Valid responses are either WSGI Apps, Tuples or of instances Responses
    if isinstance(response,tuple):
      try:
        response = yield (self.scheduler.call,)  + response
      except Exception, e:
        exc_info = sys.exc_info()
        self.log.exception('Unexpected Exception encountered in coroutine %s', request.path_info)
        response = HTTPServerError(detail="<br/>\n".join(traceback.format_exception(*exc_info)), request=request)
        response.text = response.html_body(request.environ)

          
    elif not isinstance(response, Response):
      response = request.get_response(response)
      
    if not response.headers.has_key('Connection'): 
      response.headers['Connection'] = request.environ.get('HTTP_CONNECTION')
      
    try:
      port.write('%s %s\r\n' % (request.environ['SERVER_PROTOCOL'], response.status))

      for header in response.headerlist:
        port.write('%s: %s\r\n' % header)
      #port.write('Connection: close\r\n')
      port.write('\r\n')

      for data in response.app_iter:
        port.write(data)
    finally:
      if hasattr(response.app_iter, 'close'):
        response.app_iter.close()

      # Todo: Honor keepalive headers, and calculate content
      # length so that we can keep the connection open
      # TODO: Add better method for closing the port
      info = request.environ.copy()
      info['STATUS'] = response.status_int
      self.log.info('%(REMOTE_ADDR)s %(REQUEST_METHOD)s %(HTTP_HOST)s%(PATH_INFO)s %(STATUS)s' % info)
      
      if request.environ['SERVER_PROTOCOL'] == 'HTTP/1.0':
        default_keep_alive = 'close'
      else:
        default_keep_alive = 'Keep-Alive'
      
      if (request.environ.get('HTTP_CONNECTION', default_keep_alive) == 'close' or
          response.content_length==None): 
        port.close()
      #else:
        #del self.requests[port]

  def onClose(self, port):
    self.log.debug('%s closed' % port)
    if self.requests.has_key(port):
      del self.requests[port]
      
  def onError(self, port, error):
    self.log.error(error)
    if self.requests.has_key(port):
      del self.requests[port]
    


if __name__ == "__main__":
  import doctest,sys
  doctest.testmod(sys.modules[__name__])
