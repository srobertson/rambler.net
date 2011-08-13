from Rambler import component, nil
from rambler.net.controllers.URLProtocol import URLProtocol
from rambler.net.URLResponse import URLResponse

class URLMockHTTProtocol(URLProtocol):
  """Implements a protocol for urls in the form of  mock-http://<some url path>/
  
  This component is used for testing other components that normaly operate on HTTP urls.
  
  Simply substitute a http:// url for mock-http://...
  
  """
  test = nil
  
  # Q. Why am i using a class variable for this?
  count = 0

    
  @classmethod
  def canInitWithRequest(cls, request):
    if request.url.scheme == 'mock-http':
      return True

  def startLoading(self):
    self.__class__.count = 0
    request = self.request
    #self.test.assertEquals(1024, self.request.HTTPHeaders['content-length'])
    request.HTTPBodyStream.observer = self
    request.HTTPBodyStream.read(100)
    

  def stopLoading(self):
    pass
    
  def end_of_data_for(self, stream):
    stream.delegate = None
    bytes = str(self.__class__.count)
    response = URLResponse(self.request.url, 'text/plain', len(bytes), '?')

    self.client.didReceiveResponse(self, response, self.client.URLCacheStorageNotAllowed)
    self.client.didLoadData(self, bytes)
    self.client.didFinishLoading(self)

    self.test.quit()
    stream.close()
    
    
  def onRead(self, stream, data):
    """Called when bytes from the stream our available. They'll be copied to the Port"""
    self.__class__.count += len(data)
    # keep reading until close
    stream.read(100)
