from rambler.net.controllers.URLProtocol import URLProtocol
from rambler.net.URLResponse import URLResponse

class URLDataProtocol(URLProtocol):
  """Implments URLProtocolClient for data urls
  
  Format: data:[<MIME-type>][;charset="<encoding>"][;base64],<data>
    
  Example: 
  
  More info:
  http://en.wikipedia.org/wiki/Data_URI_scheme
  data:text/plain,hi+mom
  
  """
  
  @classmethod
  def canInitWithRequest(cls, request):
    if request.url.scheme == 'data':
      return True
      
  def startLoading(self):
    mime_type, data = self.request.url.path.split(',', 1)
    
    response = URLResponse(self.request.url, mime_type, len(data), '?')
  
    self.client.didReceiveResponse(self, response, self.request.cachePolicy)
    self.client.didLoadData(self, data)
    self.client.didFinishLoading(self)
   
  def stopLoading(self):
    pass

