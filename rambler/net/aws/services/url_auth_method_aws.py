import base64
import hmac
import time
from hashlib import md5, sha1 as sha

from wsgiref.handlers import format_date_time

from Rambler import outlet
class URLAuthMethodAWS(object):
  URLCredentialStorage = outlet('URLCredentialStorage')
  
  def assembled(self):
    self.URLCredentialStorage.addAuthMethod('AWS', self)
  
  def will_disassemble(self):
    self.URLCredentialStorage.removeAuthMethod('AWS')
  
  def authorize(self, request, credentials):
    '''Adds the key Signature to the passed in params Dictionary. The value of which is
    a properly computed AWS Authentication Signature
     '''
     
    if request.url.host.endswith('.s3.amazonaws.com'):
      bucket = '/' + request.url.host[:-len('.s3.amazonaws.com')]
      
    path = bucket + (request.url.path or '/')
    sig_parts = [request.HTTPMethod,
                request.HTTPHeaders.get('content-md5', ''),
                request.HTTPHeaders.get('content-type', ''),
                # note this set's Date if not present
                request.HTTPHeaders.setdefault('date',format_date_time(time.time())),
                path
                ]

    sig = hmac.new(credentials.secret, digestmod=sha)
    sig.update('\n'.join(sig_parts))

    request.HTTPHeaders['Authorization'] = "AWS %s:%s" % (credentials.principal, base64.encodestring(sig.digest()).strip())
    #request.HTTPHeaders['Authorization'] = "AWS %s:%s" % ('0PN5J17HBGZHT7JJ3X82', base64.encodestring(sig.digest()).strip())
    
