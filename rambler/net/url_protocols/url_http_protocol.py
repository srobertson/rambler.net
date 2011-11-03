from cStringIO import StringIO
from rambler.net.controllers.URLProtocol import URLProtocol
from rambler.net.URLHTTPResponse import URLHTTPResponse

import pycurl

from Rambler import outlet, option

class URLHTTPProtocol(URLProtocol):
  """Implments URLProtocolClient for data urls
  
  """

  verbose = option('pycurl', 'verbose',0)
  run_loop = outlet('RunLoop')
  urlCredentialStorage = outlet('URLCredentialStorage')
  log = outlet('LogService')
  
  method_map = {"GET": pycurl.HTTPGET,
               "POST": pycurl.POST,
                "PUT": pycurl.UPLOAD}
      
  
  @classmethod
  def assembled(cls):
    cls.needs_registration = True
    cls.needs_perform = False
    pycurl.global_init(pycurl.GLOBAL_ALL)
    cls.multi = pycurl.CurlMulti()
    cls.multi.setopt(pycurl.M_TIMERFUNCTION, cls.curl_timeout)
    cls.multi.setopt(pycurl.M_SOCKETFUNCTION, cls.on_socket)
    cls.instances = {}

  @classmethod
  def on_socket(cls, event, fd, multi, data):
    import pdb; pdb.set_trace()
    print 'on_socket ============', event, fd, multi, data
    if event == pycurl.POLL_REMOVE:
      pass
    else:
      pass
      
  @classmethod
  def curl_timeout(cls, msecs):
    cls.run_loop.currentRunLoop().waitBeforeCalling(msecs/100.0, cls.perform)

    
  @classmethod
  def canInitWithRequest(cls, request):
    if request.url.scheme in ('http', 'https', 'ftp'):
      return True

  @classmethod
  def queue(cls, instance, handle):
    cls.instances[handle] = instance
    cls.multi.add_handle(handle)
    #cls.multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
    cls.perform()

    
  @classmethod
  def perform_if_needed(cls):
    if cls.needs_perform:
      cls.needs_perform = False
      cls.run_loop.currentRunLoop().callFromThread(URLHTTPProtocol.perform)
      
  @classmethod
  def perform(cls):
    m = cls.multi
    cls.needs_perform = True

    while 1:
      ret, num_handles = m.perform()
      if ret != pycurl.E_CALL_MULTI_PERFORM: break

    cont = 1
    while cont:
      cont, success, errors = m.info_read()
      for handle in success:
        
        i = cls.instances.pop(handle)
        m.remove_handle(handle)
        if i.response is not None:
          handle.close()
          i.client.didFinishLoading(i)
        else:
          # Handle had sucess w/o response, seems to happen after a server returns a non 200 like a 405
          # (invalid method). If the next attempt is before the connection timeout this method
          # returns immediatly w/o any data. Re-queueing get's the desired behavior
          cls.queue(i, handle)
      
      for handle, err_number, error in errors:
        i = cls.instances.pop(handle)
        m.remove_handle(handle)
        handle.close()
        i.client.didFailWithError(i, error)
            
    cls.register_if_needed()

  @classmethod
  def register_if_needed(cls):
    if cls.needs_registration:
      cls.needs_registration = False
      cls.run_loop.currentRunLoop().callFromThread(cls.register_with_run_loop)
  
  @classmethod
  def register_with_run_loop(cls):
    cls.needs_registration = True
    cls.needs_perform = True
    run_loop = cls.run_loop.currentRunLoop()
    
    readers, writers, errors = cls.multi.fdset()
    
    for r in readers:
      run_loop.addReader(Source(r))
      
    for w in writers:
      run_loop.addWriter(Source(w))
    
      
  def __init__(self, request, cached_response, client):
    super(URLHTTPProtocol, self).__init__(request, cached_response, client)
    self.cached_response = cached_response

    self.urlCredentialStorage.authorize(request)
    self.handle = None
    self.response = None

  
  def on_header(self, line):
    if line == '\r\n':
      if self.response.statusCode == 100:
        # Reset response and wait for the request to finish
        self.response = None
      else:        
        self.client.didReceiveResponse(self, self.response, self.client.URLCacheStorageNotAllowed)
      return len(line)
        
    if self.response is None:
      protocol, code, response = line.split(' ',2)
      self.response = URLHTTPResponse(self.request.url)
      self.response.statusCode = int(code)
    else:
      header, value = line.split(':',1)
      self.response.headers[header.lower()] = value.strip()

    
  def on_data(self, data):
    self.client.didLoadData(self, data)
    
  def on_debug(self, code, error):
    self.log.info("%s -%s", code, error)

    
  def startLoading(self):
    #import pdb; pdb.set_trace()
    if self.cached_response is None:
      c = pycurl.Curl()
      c.setopt(pycurl.NOSIGNAL, 1) 
      c.setopt(pycurl.URL, str(self.request.url))
      #c.setopt(pycurl.DNS_USE_GLOBAL_CACHE, 1)
      #c.setopt(pycurl.DNS_CACHE_TIMEOUT, -1)
      #c.setopt(c.FOLLOWLOCATION, 1)


      c.setopt(pycurl.HEADERFUNCTION, self.on_header)
      c.setopt(pycurl.WRITEFUNCTION, self.on_data)
      c.setopt(pycurl.VERBOSE, int(self.verbose))
      c.setopt(pycurl.DEBUGFUNCTION, self.on_debug)
      
      request = self.request
      c.setopt(self.method_map[request.HTTPMethod],1)
            
      headers = []
      for header, value in request.HTTPHeaders.items():
        headers.append('%s:%s' % (header, value))
      headers.append("Expect:")
      
      c.setopt(pycurl.HTTPHEADER, headers)

      if request.HTTPBody:
        c.setopt(pycurl.READFUNCTION, StringIO(request.HTTPBody).read)
      elif request.HTTPBodyStream:
        c.setopt(pycurl.READFUNCTION, request.HTTPBodyStream.read)
        
        
      
      if request.HTTPHeaders.has_key('content-length'):
        c.setopt(pycurl.INFILESIZE, request.HTTPHeaders['content-length'])
      
      self.queue(self, c)

    else: # use the cached response
      self.client.didReceiveResponse(self, self.cached_response.response,  self.client.URLCacheStorageNotAllowed)
      self.client.didLoadData(self, self.cached_response.data.getvalue())
      self.client.didFinishLoading(self)
    
  def stopLoading(self):
    pass
  
  
class Source():
  """Class used to monitor file descriptors created by pyCurl in the RunLoop """
  def __init__(self,fileno):
    self._fileno = fileno
    
  def fileno(self):
    return self._fileno
    
  @classmethod
  def perform(cls, source):
    URLHTTPProtocol.perform_if_needed()
    
  canRead=canWrite=onError=perform
  
  