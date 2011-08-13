
class URLProtectionSpace(object):
 """Represents a server or area on a server, sometimes refered to as a realm, that requires
 that requires authentication. URLProtectionSpace's credentials will be sent along with
 any requset that falls within the protection space.""" 
 
 __slots__ = ('authenticationMethod', 'host', 'port', 'protocol', 'realm')
 
 def __init__(self):
   self.authenticationMethod = None
   self.host = None
   self.port = None
   self.realm = None