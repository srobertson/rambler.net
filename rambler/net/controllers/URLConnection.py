import copy

from Rambler import outlet

from cStringIO import StringIO

class URLConnection(object):
  runLoop = outlet('RunLoop')
  URLRequest = outlet('URLRequest')
  URLProtocol = outlet('URLProtocol')
  URLCache = outlet('URLCache')
  CachedURLResponse = outlet('CachedURLResponse')
  
  URLCacheStorageAllowed = 0
  URLCacheStorageAllowedInMemoryOnly = 1
  URLCacheStorageNotAllowed = None
  
  log = outlet('LogService')
  
    
  @classmethod
  def connectionWithRequest(cls, request, delegate):
    if isinstance(request, basestring):
      request = cls.URLRequest(request)

    connection = cls(request)
    connection.delegate = delegate
    connection.start()
    return connection
        
  def __init__(self, request):
    cached_response = self.URLCache.shared_url_cache().cached_response_for(request)
    #cached_response = None
    self.protocol = self.URLProtocol.protocolForRequest(request, cached_response, self)
   
    if not self.protocol:
      raise RuntimeError, "No protocol for request"
      
    self.request = copy.deepcopy(request)
    self.user_info = {}
    # Set in did_receive_response if the protocol indicates 
    # thet response should be cached
    self.cached_response = None
    
    # Deprecate
    self.userInfo = self.user_info
    
    
  def start(self):
    # call in the next pass of the runLoop
    self.runLoop.currentRunLoop().waitBeforeCalling(0,self.protocol.startLoading)
    
  def send(self, method_name, *args, **kw):
    method =  getattr(self.delegate, method_name, None)
    if method is None: # see if it has a deprecated camelCase
      method_name = ''.join([w.capitalize() for w in method_name.split('_')])
      method_name = method_name[0].lower() + method_name[1:]
      method =  getattr(self.delegate, method_name, None)
    
    if method is not None:
      try:
        return method(self, *args, **kw)
      except:
        self.log.exception('error executing delegate method %s', method_name)
      
        
  # Delegated methods
  def didReceiveResponse(self, protocol, response, cachePolicy):
    """Called when the protocol receives enough data to construct a response object.
    
    The connection object will then invoke didReceiveResponse on it's delegate
    """
    self.send('did_receive_response', response)
    
    if cachePolicy != self.URLCacheStorageNotAllowed:
      self.cached_response = self.CachedURLResponse()
      self.cached_response.response = response
      self.cached_response.data = StringIO()
      self.cached_response.storage_policy = cachePolicy
    #self.delegate.didReceiveResponse(self, response)
    
  def didLoadData(self, protocol, data):
    """Called one or more times as data is received by the protocol."""
    self.send('did_receive_data', data)
    # TODO: after a certain size we should dump to disk
    if self.cached_response:
      self.cached_response.data.write(data)
    #self.delegate.didReceiveData(self, data)
    
  def didFailWithError(self, protocol, error):
    """Called when the protocol deteceted an error"""
    self.send('did_fail_with_error', error)
    if self.cached_response:
      self.cached_response.data.close()
      del self.cached_response.data 
      del self.cached_response
    #self.delegate.didFailWithError(self, error)
    
  def didFinishLoading(self, protocol):
    """Called by the protocol when the request has finished loading"""
    
    if self.cached_response:
      # The protocl will instruct us to cache the response, we give the delegate
      # the oprotunity to overide it before it's actually stored in the cache
      cached_response = self.cached_response
      del self.cached_response
      if hasattr(self.delegate, 'will_cache_response'):
        cached_response = self.delegate.will_cache_response(self, cached_response)
        
      if cached_response is not None:
        self.URLCache.shared_url_cache().store(cached_response, self.request)
        
    #self.delegate.didFinishLoading(self)
    self.send('did_finish_loading')
    
