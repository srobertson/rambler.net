from Rambler import nil,outlet,option
from rambler.net.URL import URL


# TODO: Consider making URLCredentials and URLProtectionSpace models so they can be serialized
class URLCredentialStorage(object):
  """URLCredentialStorage manages credentials and authorization methods
    used by the URL Loading System.
  """
  log = outlet('LogService')
  URLCredential = outlet('URLCredential')
  URLProtectionSpace = outlet('URLProtectionSpace')
  
  # HACK: Delay assembling URLCredentialStorage until appconfig is ready..., 
  # the other alternative is waiting to do this until Initializing has published
  appConfigService = outlet('AppConfigSource')
  
  url_credentials = option('rambler.net', 'url_credentials', {})  
  
  def __init__(self):
    # auth method name to URLAuthMethod objects
    self.auth_methods={}
    
    self.credentials_by_protection_space = {}
    
  def assembled(self):
    for url, creds in self.url_credentials.items():
      url = URL.urlFromString(url)
      
      protectionSpace = self.protectionSpaceFrom(url)
      protectionSpace.authenticationMethod = creds.get('auth_method')
      
      credential = self.URLCredential()
      credential.principal = creds['principal']
      credential.secret = creds['secret']
      
      self.setCredentialsFor(protectionSpace, credential)
  
  def authorize(self, request):
    """Authorize the given request using the appropriate authorization method
    if the Credential Storage has credentials for the ProtecionSpace."""
    
    protectionSpace = self.protectionSpaceFrom(request.url)
    matches = self.findCredentials(protectionSpace)
    if matches:
      score, protectionSpace, credentials = matches[0]
      self.authMethodFor(protectionSpace).authorize(request, credentials)
    
  def credentialsFor(self, protectionSpace):
    """Returns the credentials with the closest match to the given protectionSpace."""
    # TODO: Search the 
    return self.credentials_by_protection_space.get(protectionSpace)

    
  def setCredentialsFor(self, protectionSpace, credential):
    self.credentials_by_protection_space[protectionSpace] = credential
    
  def addAuthMethod(self, method_type, method):
    """Called by components implmenting the URLAuthMethod interface"""
    self.auth_methods[method_type] = method
  
  def removeAuthMethod(self, method_type):
    """Remove the specified auth method.
    
    Well behaved AuthMethod componets should call this from their 
    will_dissamble() methods
    """
    del self.auth_methods[method_type] 
  
    
  def authMethodFor(self, protectionSpace):
    """Returns the auth method for the given protection space or nil."""
    authMethod = protectionSpace.authenticationMethod
    method = self.auth_methods.get(authMethod, nil)
    
    if method is nil:
      self.log.warn('No AuthMethod registered for %s', authMethod)
      
    return method
  
  def protectionSpaceFrom(self, url):
    protectionSpace = self.URLProtectionSpace()
    protectionSpace.protocol = url.scheme
    protectionSpace.host = url.host
    protectionSpace.port = url.port
    return protectionSpace
    
  def findCredentials(self, protectionSpace):
    """Returns a list of credentials that match given protectionSpace.
    
    More than one Credentials may have been specified with various restrictions for any 
    combination of  server,  port, realm and auth method. This method will score each stored
    credentials based on how closesly it matches the given protection space. Those with a higher 
    score have a closer match should be tried prior to other credentials.
    
    Note if a credential was stored with an attribute, such as host, that does not match the given
    protection space it will be ignored.
    
    Returns credentials that match the given protectionSpace with the most restrictive first.
    
    """
    
    matches = []    
    for canidate, creds in self.credentials_by_protection_space.items():
      score = 0
      for attr in ('host', 'port', 'protocol', 'authenticationMethod'):
        canidate_value = getattr(canidate, attr)
        space_value = getattr(protectionSpace, attr)
        if None in (canidate_value, space_value):
          # no value specified, keep computing the score
          continue
        elif canidate_value != space_value:
          # this is not a canidate for the protection space
          score = -1
          break
        else:
          # an exact match on this attribute give this canidate higher consideration
          score += 1
      if score > -1:
        matches.append((score, canidate, creds))
        
    return sorted(matches, reverse=True)
        
    
  