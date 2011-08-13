from rambler.net.URLResponse import URLResponse

class URLHTTPResponse(URLResponse):
  
  def __init__(self, *args, **kw):
    super(URLHTTPResponse, self).__init__(*args, **kw)
    
    self.statusCode = None
    self.headers = {}
    self._contentLength = None
    
  def expectedContentLength(self):
    if self._contentLength is None:
      cl = self.headers.get('content-length')
      if cl is not None:
        cl = int(cl)
      self._contentLength = cl
    return self._contentLength
    
  def setExpectedContentLength(self, value):
    pass
    
  expectedContentLength = property(expectedContentLength, setExpectedContentLength)
  

  def MIMEType(self):
    return self.headers.get('content-type')
    
  def setMIMEType(self, value):
    # Ignore this and always use the header.
    # TODO: Consider removing MIMEType from URLResponse init method
    pass
  MIMEType = property(MIMEType, setMIMEType)
  
  
  def textEncodingName(self):
    # todo: verify the real encoding here
    return self.headers.get('content-encoding')
  
  def setTextEncodingName(self, value):
    pass
  textEncodingName = property(textEncodingName, setTextEncodingName)
