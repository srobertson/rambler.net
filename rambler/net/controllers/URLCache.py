import hashlib

from Rambler import outlet
from Rambler.LRU import LRU


class URLCache(object):
  log = outlet('LogService')
  
  @classmethod
  def assembled(cls):
    cls._shared_url_cache = cls()
    
  @classmethod
  def shared_url_cache(cls):
    """Return the shared URL Cache for the app"""
    return cls._shared_url_cache
  
  @classmethod
  def set_shared_url_cache(cls, shared_cache):
    """Sets the shared url cache for the app.
    
    Discussion: You only need to call this method if you wish to overide
    the default shared cache. 
    """
    cls._shared_url_cache = shared_cache
  
  def __init__(self):
    self.lru = LRU(10)
    
  def cached_response_for(self, request):
    """Returns the cached response for the given request or None."""
    key = self._hash_url(request).digest()
    return self.lru.get(key)
    
  def store(self, cached_response, request):
    """Stores a cached URL for a specified request"""
    self.log.info('Caching %s', request.url)
    key = self._hash_url(request).digest()
    self.lru[key] = cached_response
  
  def remove_cached_response_for(self, request):
    """Removes a cached response for the request if it exists."""
    key = self._hash_url(request).digest()
    try:
      del self.lru[key]
    except KeyError:
      #wonder if this is caused by a hash conflict?
      self.log.warn('Key does not exist %s for url %s', key, request.url)
  def _hash_url(self, request):
      h = hashlib.new('sha1')
      h.update(str(request.url))
      return h
    
    
    