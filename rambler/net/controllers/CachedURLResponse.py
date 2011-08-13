class CachedURLResponse(object):
  __slots__ = ('response','data', 'storage_policy', 'user_info')
  @classmethod
  def init_with(cls, response, data):
    instance = cls()
    instance.data = data
    instance.response = response
    
  def __init__(self):
    self.data = None
    self.response = None
    self.storage_policy = None
    self.user_info = None
    