import sys
import unittest


from Rambler.RunLoop import RunLoop, Port
from Rambler.LoggingExtensions import LogService

from rambler.net.controllers.LineReceiverProtocol import LineReceiverProtocol
from rambler.net.controllers.URLConnection import URLConnection
from rambler.net.controllers.URLRequest import URLRequest
from rambler.net.controllers.URLProtocol import URLProtocol

from rambler.net.url_protocols.URLDataProtocol import URLDataProtocol
from rambler.net.url_protocols.URLHTTPProtocol import URLHTTPProtocol
from components.delegate import Delegate



class TestHTTPChannel(unittest.TestCase):
    
    def setUp(self):
        self.delegate = Delegate()
        super(self.__class__,self).setUp()
        self.runLoop = RunLoop.currentRunLoop()
        # Wire URLHTTPProtocol
        URLHTTPProtocol.LRProtocol = LineReceiverProtocol
        URLHTTPProtocol.portFactory = Port
        
        
        # Wire URLProtocol
        URLProtocol.registerClass(URLDataProtocol)
        URLProtocol.registerClass(URLHTTPProtocol)
        URLConnection.URLProtocol = URLProtocol
        URLConnection.runLoop = RunLoop
        
        # Wire RunLoop
        ls = LogService()
        ls.useStreamHandler(sys.stderr)
        RunLoop.log = ls.__binding__('RunLoop', RunLoop)
    
    def testDataURL(self):
        request = URLRequest('data:text/html,<html><body>Hi mom!</body></html>')                           
        connection = URLConnection.connectionWithRequest(request, self.delegate)
      
        self.runLoop.run()
        self.assertEqual(3, len(self.delegate.log))
        
        response  = self.delegate.log[0][2]
        self.assertEqual('text/html', response.MIMEType)
        
        data = self.delegate.log[1][2]
        self.assertEqual('<html><body>Hi mom!</body></html>', data)
          
    def testHTTPURL(self):
      request = URLRequest('http://google.com')
      # tell the server to close the connection, if not the run loop won't quit until the socket
      # timesout
      request.HTTPHeaders['connection'] = 'close'
      connection = URLConnection.connectionWithRequest(request, self.delegate)
      self.runLoop.run()
      self.assertEqual(3, len(self.delegate.log))
        

if __name__ == "__main__":
  unittest.main()
        
