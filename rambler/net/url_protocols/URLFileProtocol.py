import os
import stat
import mimetypes

from Rambler import outlet
from rambler.net.controllers.URLProtocol import URLProtocol
from rambler.net.URLResponse import URLResponse

class URLFileProtocol(URLProtocol):
  """Implments URLProtocolClient for data urls
  
  """
  
  runLoop = outlet('RunLoop')
  chunkSize = 4096
  
  @classmethod
  def canInitWithRequest(cls, request):
    if request.url.scheme == 'file':
      return True
      
  def startLoading(self):
    path = self.request.url.path
    mime_type, encoding = mimetypes.guess_type(path)
    
    try:
      self.file = open(path)
      contentLength = os.stat(path)[stat.ST_SIZE]
    except Exception, e:
      self.client.didFailWithError(self, e)
      return

    response = URLResponse(self.request.url, mime_type, contentLength, encoding)
    self.client.didReceiveResponse(self, response, self.request.cachePolicy)
    
    self.runLoop.currentRunLoop().waitBeforeCalling(0, self.loadData)
    
  def loadData(self):
    data = self.file.read(self.chunkSize)
    if data:    
      self.client.didLoadData(self, data)
      self.runLoop.currentRunLoop().waitBeforeCalling(0, self.loadData)
    else:
      self.file.close()
      self.client.didFinishLoading(self)
   
  def stopLoading(self):
    pass

