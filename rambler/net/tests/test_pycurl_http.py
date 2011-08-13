import sys
import unittest

from Rambler.RunLoop import RunLoop, Port
from Rambler.LoggingExtensions import LogService


from rambler.net.controllers.URLConnection import URLConnection
from rambler.net.controllers.URLCache import URLCache
from rambler.net.controllers.URLRequest import URLRequest
from rambler.net.controllers.URLProtocol import URLProtocol
from components.delegate import Delegate


from rambler.net.url_protocols.url_http_protocol import URLHTTPProtocol


class TestPyCurl(unittest.TestCase):
  def setUp(self):
    self.delegate = Delegate()
    super(self.__class__,self).setUp()
    self.runLoop = RunLoop.currentRunLoop()

    # Wire URLProtocol
    URLHTTPProtocol.run_loop = RunLoop
    URLHTTPProtocol.assembled()
    URLProtocol.registerClass(URLHTTPProtocol)
    URLConnection.URLProtocol = URLProtocol
    URLCache.assembled()
    URLConnection.URLCache = URLCache
    URLConnection.runLoop = RunLoop
        
    # Wire RunLoop
    ls = LogService()
    ls.useStreamHandler(sys.stderr)
    RunLoop.log = ls.__binding__('RunLoop', RunLoop)
    
  def testHTTPURL(self):
    request = URLRequest('http://www.google.com')
    # tell the server to close the connection, if not the run loop won't quit until the socket
    # timesout
    request.HTTPHeaders['connection'] = 'close'
    connection = URLConnection.connectionWithRequest(request, self.delegate)
    self.runLoop.run()

    self.assertEqual('didReceiveResponse', self.delegate.log[0][0])
    self.assertEqual('didFinishLoading', self.delegate.log[-1][0])
    
  def testHTTPErr(self):
    request = URLRequest('http://badhost.local')
    # tell the server to close the connection, if not the run loop won't quit until the socket
    # timesout

    connection = URLConnection.connectionWithRequest(request, self.delegate)
    self.runLoop.run()
    self.assertEqual('didFailWithError', self.delegate.log[0][0])


if __name__ == "__main__":
  unittest.main()
