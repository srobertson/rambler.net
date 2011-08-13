import unittest
from Rambler.TestCase import TestCase

from rambler.net.URLHTTPResponse import URLHTTPResponse


class TestURLCache(TestCase):
  
  def setUp(self):
    super(TestURLCache, self).setUp()
    self.CachedURLResponse = self.componentFor('CachedURLResponse')
    self.URLRequest = self.componentFor('URLRequest')
    self.cache = self.comp.shared_url_cache()

    
  def test_cache(self):
    
    cached_response = self.CachedURLResponse()
    request = self.URLRequest("http://himom.example.com")
    response = URLHTTPResponse(request.url)
    response.statusCode = 200
    response.headers['content-type'] = 'text/html'
    cached_response.data = "<html><body>Hi Mom!</body></html>"
    response.headers['content-length'] = len(cached_response.data)
    cached_response.response=response
    
    self.cache.store(cached_response, request)
    
    request2 = self.URLRequest("http://himom.example.com")
  
    cached_response_b = self.cache.cached_response_for(request2)
    
    self.assertEqual(cached_response,cached_response_b)

    cached_response_c = self.cache.cached_response_for(self.URLRequest("http://himom.example.com/missing"))
    self.assertEqual(cached_response_c, None )

    
    
if __name__ == "__main__":
  unittest.main()