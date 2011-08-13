import base64

from Rambler import outlet

class URLAuthMethodBasic(object):
  URLCredentialStorage = outlet('URLCredentialStorage')
  
  def assembled(self):
    self.URLCredentialStorage.addAuthMethod('Basic', self)
  
  def will_disassemble(self):
    self.URLCredentialStorage.removeAuthMethod('Basic')
  
  def authorize(self, request, credentials):
    '''Adds a Base64 encoded Auth header to outgoing requests.'''

    if "Authorization" not in  request.HTTPHeaders:
      base64string = base64.encodestring(
                      '%s:%s' % (credentials.principal, credentials.secret))[:-1]
      authheader =  "Basic %s" % base64string
      request.HTTPHeaders["Authorization"] =  authheader
