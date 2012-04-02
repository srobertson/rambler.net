import bisect
from webob.exc import HTTPNotFound

from Rambler import coroutine
from Rambler.LRU import LRU

class  HTTPRequestMapper(object):
  HIGHEST = 0
  NORMAL  = 1
  LOWEST  = 2
   
  def assembled(self):
    self.handlers = []
    self.handler_cache = LRU(10)
  
  def registerLocationHandler(self, handler, priority=NORMAL):
    bisect.insort(self.handlers, (priority, handler))
  
  @coroutine  
  def findHandlerFor(self, request):
    handler = self.handler_cache.get(request.path_info)
    if handler:
      response = yield handler.dispatch(request)
      return #response
      
    for priority, handler in self.handlers:
      response = yield handler.dispatch(request)
      if response is not None:
        self.handler_cache[request.path_info] = handler
        return #response
    
    # TODO: Ask the location handlers for /404.html
    yield HTTPNotFound(request=request)