import base64
import cgi
from datetime import datetime
import hmac
import hashlib
import urllib
from hashlib import md5, sha1 as sha

import sys

from Rambler import outlet

class URLAuthMethodSQS(object):
  URLCredentialStorage = outlet('URLCredentialStorage')
  
  def assembled(self):
    self.URLCredentialStorage.addAuthMethod('SQS', self)
  
  def will_disassemble(self):
    self.URLCredentialStorage.removeAuthMethod('SQS')
  
  def authorize(self, request, credentials):
    '''Adds the key Signature to the passed in params Dictionary. The value of which is
    a properly computed AWS Authentication Signature'''
    
    params = {'AWSAccessKeyId': credentials.principal,
            'SignatureVersion': '1',
            #'SignatureMethod': 'HmacSHA256',
            'Version': '2008-01-01',
            'Timestamp':  datetime.utcnow().isoformat()
            } 
    if request.HTTPMethod == 'GET':
      # user the
      params.update(cgi.parse_qsl(request.url.query))
      if params.has_key('Signature'):
        return

    sig = hmac.new(credentials.secret, digestmod=hashlib.sha1)
    
    # Version 2 sigs...
    #sig.update(request.HTTPMethod + '\n')
    #sig.update(request.HTTPHeaders['Host'].lower() + '\n')
    #sig.update(request.url.path + '\n')
    
    keys = params.keys()
    keys.sort(key=str.lower)
    
    for key in keys:
      sig.update(key)
      value = str(params[key])
      sig.update(value)
    
    params['Signature'] = base64.encodestring(sig.digest()).strip()
    request.url.query = urllib.urlencode(params)

    
       
