class Delegate:
    
    def __init__(self):
        self.log = []
    
    def onCancelAuthenticationChallenge(self, connection, challenge):
        """Sent when a connection cancels an authentication challenge."""
        self.log.append(('onCancelAUthenticationChallenge', connect, challenge))
      
    def didFailWithError(self, connection, error):
        """Sent when a connection fails to load its request successfully."""
        print error
        self.log.append(('didFailWithError', connection, error))
      
    def onReceiveAuthenticationChallenge(self, connection, challenge):
        """Sent when a connection must authenticate a challenge in order to download its request."""
        self.log.append(('onReceiveAuthenticationChallenge', connection, challenge))
      
    def didReceiveData(self, connection, data):
        """Sent as a connection loads data incrementally."""
        self.log.append(('didReceiveData', connection, data))
        
    def didReceiveResponse(self, connection, response):
        """Sent when the connection has received sufficient data to construct the URL response for its request."""
        self.log.append(('didReceiveResponse', connection, response))
      
    def willCacheResponse(self, connection, cachedResponse):
        """Sent before the connection stores a cached response in the cache, to give the delegate an opportunity to alter it."""
        self.log.append(('willCacheResponse', connection, cachedResponse))
        
    def willSendRequest(self, connection,redirectResponse):
        """Sent when the connection determines that it must change URLs 
        in order to continue loading a request."""
        self.log.append(('willSendRequest',connection, redirectResponse))
      
    def didFinishLoading(self, connection):
        """Sent when a connection has finished loading successfully."""
        self.log.append(('didFinishLoading', connection))


