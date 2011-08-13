from rambler.net.URL import URL
class URLRequest(object):
  UseProtocolCachePolicy = 0
  ReloadIgnoringLocalCacheData = 1
  ReloadIgnoringLocalAndRemoteCacheData = 4
  ReloadIgnoringCacheData = ReloadIgnoringLocalCacheData
  ReturnCacheDataElseLoad = 2
  ReturnCacheDataDontLoad = 3
  ReloadRevalidatingCacheData = 5
  
  
  def __init__(self, url, cachePolicy=0, timeout=60):  
    if isinstance(url, URL):
      self.url = url
    else: # assume it a string url
      self.url = URL()
      self.url.initWithString(url)
    
    self.timeout = timeout
    # Default is 0, UseProtocolCachePolicy
    self.cachePolicy = cachePolicy
    
    # HTTP specific request variables, wonder if it be better to only init these
    # when 
    # Requests can have one ore the other
    

    self.HTTPMethod = 'GET'
    # todo: keys need to be case insensitive
    self.HTTPHeaders = {}
    self._body = None
    self._bodyStream = None    

  def _get_HTTPBody(self):
    return self._body

  def _set_HTTPBody(self, body):
    if self._bodyStream is None:
      self._body = body
      self.HTTPHeaders['Content-length'] = len(body)
    else:
      raise RuntimeError('HTTPBodyStream has already been set.')
      
  HTTPBody = property(_get_HTTPBody, _set_HTTPBody)
    
  def _get_HTTPBodyStream(self):
    return self._bodyStream
    
  def _set_HTTPBodyStream(self, stream):
    if self._body is None:
      self._bodyStream = stream
    else:
      raise RuntimeError('HTTPBody has already been set.')
  HTTPBodyStream = property(_get_HTTPBodyStream, _set_HTTPBodyStream)

  @property
  def mainDocumentURL(self):
    """Returns the main document URL associated with the request.
    
    This URL is used for the cookie "same domain as main document" policy.    
    """
    # not implemented yet
    return self.url