import os
import stat
import mimetypes

import pkg_resources

from Rambler import outlet
from rambler.net.controllers.URLProtocol import URLProtocol
from rambler.net.URLResponse import URLResponse

class URLRamblerProtocol(URLProtocol):
  """Implments URLProtocolClient for rambler urls.
  
  Rambler urls are like file urls but they're located relative to
  the rambler app or extension they may be in.
  
  """
  
  runLoop = outlet('RunLoop')
  chunkSize = 4096
  
  @classmethod
  def canInitWithRequest(cls, request):
    if request.url.scheme == 'rambler':
      return True
      
  def startLoading(self):
    # note, URL uses python's urlparse which only recognizes the host/netloc fields
    # in protocols it knows about


    # TODO: Bug in url returns path as //<modname>/some_path so we need to skip the first
    # two slashes
    path = self.request.url.path
    if path.startswith('//'):
      path = path[2:]
  
    app_or_ext, path = path.split('/',1)#[2:]
    mime_type, encoding = mimetypes.guess_type(path)

    path = pkg_resources.resource_filename(app_or_ext, path)
      
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

