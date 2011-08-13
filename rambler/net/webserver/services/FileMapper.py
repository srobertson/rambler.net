import os
import mimetypes

from webob import Response

from Rambler import outlet
import pkg_resources

class FileMapper(object):
  app               = outlet('Application')
  httpRequestMapper = outlet('HTTPRequestMapper')
   
  def assembled(self):
    self.httpRequestMapper.registerLocationHandler(self, priority=self.httpRequestMapper.HIGHEST)
    self.mod_names = ['Rambler', self.app.name] + [ext.name for ext in self.app.config.extensions]
    
  def dispatch(self, request):
    """Returns a response if a file can be found in the public directory of one of the rambler extension 
    otherwise it returns None"""
    
    path =  'public/' + request.path_info
    if path.endswith('/'):
      path += 'index.html'
    path = os.path.normpath(path)

    for module in self.mod_names:
      try:
        stream = pkg_resources.resource_stream(module + '.web_controllers', path )
        response = Response(request=request, app_iter = stream)
        response.content_type = mimetypes.guess_type(stream.name)[0]
        response.content_length = os.path.getsize(stream.name)
              
        return response
      except (IOError, ImportError):
        pass
  