class URLCredential(object):
  __slots__=('principal', 'secret')
  
  def __init__(self):
    self.principal = None
    self.secret = None
  
  # user and password are aliases for principal and secret
  def user(self):
    return self.principal
    
  def set_user(self, value):
    self.principal = value
    
  user = property(user, set_user)
    
  def password(self):
    return self.secret

  def set_password(self, value):
    self.secret = value    

  password = property(password, set_password)
