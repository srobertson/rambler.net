import urlparse
class URL(object):
  @classmethod
  def urlFromString(cls, urlString):

    url = URL()
    url.initWithString(urlString)
    return url
  
  def __init__(self):
    pass
    
  def __str__(self):
    url = "%s://%s%s" % (self.scheme, self.netloc, self.path)
    if self.query:
      url += '?' + self.query
    return url
     
  def initWithString(self, urlString):
    # Note this initWithString seems very upython like. I must have been following Apple's
    # objective C guideline when I was first developing.. sorry
    
    (self.scheme, self.netloc, self.path, self.parameters,
     self.query, self.fragment)  =  urlparse.urlparse(urlString)

    parts = self.netloc.split(':')
    

    self.host = parts[0]
    if len(parts) == 1:
      # todo, replace this with the default port found in /etc/services for the specified
      # scheme
      self.port = 80
    elif len(parts) == 2:
      self.port = int(parts[1])
      

