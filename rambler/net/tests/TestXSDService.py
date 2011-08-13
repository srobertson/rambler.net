import unittest
import sys

from rambler.net.controllers.XMLSchemaService import XMLSchemaService

from Rambler.RunLoop import RunLoop, Port
from Rambler.LoggingExtensions import LogService

from rambler.net.controllers.LineReceiverProtocol import LineReceiverProtocol
from rambler.net.controllers.URLConnection import URLConnection
from rambler.net.controllers.URLRequest import URLRequest
from rambler.net.controllers.URLProtocol import URLProtocol

from rambler.net.url_protocols.URLDataProtocol import URLDataProtocol
from rambler.net.url_protocols.URLHTTPProtocol import URLHTTPProtocol

delete_message_response = '''
 <DeleteMessageResponse>
   <ResponseMetadata>
    <RequestId>cb919c0a-9bce-4afe-9b48-9bdf2412bb67</RequestId>
   </ResponseMetadata>
</DeleteMessageResponse>'''

receive_message_response='''
 <ReceiveMessageResponse>
   <ReceiveMessageResult>
     <Message>
       <MessageId>11YEJMCHE2DM483NGN40|3H4AA8J7EJKM0DQZR7E1|PT6DRTB278S4MNY77NJ0</MessageId>
       <ReceiptHandle>Z2hlcm1hbi5kZXNrdG9wLmFtYXpvbi5jb20=:AAABFoNJa/AAAAAAAAAANwAAAAAAAAAAAAAAAAAAAAQAAAEXAMPLE</ReceiptHandle>
       <MD5OfBody>acbd18db4cc2f85cedef654fccc4a4d8</MD5OfBody>
       <Body>foo</Body>
     </Message>
     <Message>
       <MessageId>0MKX1FF3JB8VWS8JAV79|3H4AA8J7EJKM0DQZR7E1|PT6DRTB278S4MNY77NJ0</MessageId>
       <ReceiptHandle>X5djmi3uoi2zZ8Vdr5TkmAQtDTwrcd9lx87=:AAABFoNJa/AAAAAAAAAANwAAAAAAAAAAAAAAAAAAAAQAAAEXAMPLE</ReceiptHandle>
       <MD5OfBody>37b51d194a7513e45b56f6524f2d51f2</MD5OfBody>
       <Body>bar</Body>
     </Message>
   </ReceiveMessageResult>
   <ResponseMetadata>
     <RequestId>b5bf2332-e983-4d3e-941a-f64c0d21f00f</RequestId>
   </ResponseMetadata>
 </ReceiveMessageResponse>
 '''
 
error_response='''<ErrorResponse xmlns="http://queue.amazonaws.com/doc/2008-01-01/">
<Error>
<Type>Sender</Type>
<Code>MissingClientTokenId</Code>
<Message>Request must contain AWSAccessKeyId or X.509 certificate.</Message>
<Detail/>
</Error>
<RequestID>aaf9b31b-a59e-4d78-a4a2-6bbc0eed769f</RequestID>
</ErrorResponse>'''

# NOTE: As far as I can tell from AWS 2008-01-01 schema the Metadata attribute 
# is not allowed
message_response_with_uknown_elements='''<?xml version="1.0"?>\n
<ReceiveMessageResponse xmlns="http://queue.amazonaws.com/doc/2008-01-01/">
<ReceiveMessageResult>
<Message>
<MessageId>1f333e51-1029-421e-bf0e-00c15011005a</MessageId>
<ReceiptHandle>MgTT3vrU9PUuMJUrvqCZ3KQ5chwtdm+YsXdn2v3Lwq+8L71SfIVdgQgWBpTvPd1LU0GHoz/YS6uClgoLKONKlr3udPjf6qxbNrn8GA1J+eq33NXi+FUFx9BXpLusicnap1EXRssWYtfMIh0nHPPHrQ==</ReceiptHandle>
<MD5OfBody>8f2770293f9b94ad705d5fd742f5f885</MD5OfBody>
<Body>--- \nsequenceId: !!str 1\ncarrierId: &amp;id1\ndestination: !!str 88147\nguid: *id1\nbody: help\nsource: !!str 7782273859\n</Body>
<Metadata>
<customerId>A20N8VT9EDTK2G</customerId>
<enqueueTime>1227571215130</enqueueTime>
</Metadata>
</Message>
</ReceiveMessageResult>
<ResponseMetadata>
<RequestId>62935dc9-8704-496f-a123-81f73ca3c0a0</RequestId>
</ResponseMetadata>
</ReceiveMessageResponse>
'''
 

class TestXSDService(unittest.TestCase):
  # be cool if testing worked like this
  #XMLSchemaService = outlet('XMLSchemaService')
  # requires('rambler.net')

  def setUp(self):
    super(self.__class__,self).setUp()
    self.runLoop = RunLoop.currentRunLoop()
    # Wire URLHTTPProtocol
    URLHTTPProtocol.LRProtocol = LineReceiverProtocol
    URLHTTPProtocol.portFactory = Port

    # Wire URLProtocol
    URLProtocol.registerClass(URLDataProtocol)
    URLProtocol.registerClass(URLHTTPProtocol)
    
    # Wire URLConnection
    URLConnection.URLProtocol = URLProtocol
    URLConnection.runLoop = RunLoop
    URLConnection.URLRequest = URLRequest
      
    # Wire RunLoop
    ls = LogService()
    ls.useStreamHandler(sys.stderr)
    RunLoop.log = ls.__binding__('RunLoop', RunLoop)
    XMLSchemaService.URLConnection = URLConnection
    
    self.XMLSchemaService = XMLSchemaService
    self.schema = None
      
  def testParseDeleteMessage(self):
    self.XMLSchemaService.loadSchema('http://queue.amazonaws.com/doc/2008-01-01/QueueService.xsd', self)
    self.runLoop.run()
    assert(self.schema)
    parser = self.schema.newParser()
    parser.feed(delete_message_response)
    result = parser.finish()
    self.assertEqual('cb919c0a-9bce-4afe-9b48-9bdf2412bb67', result.ResponseMetadata.RequestId)
    
  def testParseReceiveMessage(self):
    self.XMLSchemaService.loadSchema('http://queue.amazonaws.com/doc/2008-01-01/QueueService.xsd', self)
    self.runLoop.run()
    assert(self.schema)
    
    parser = self.schema.newParser()
    parser.feed(receive_message_response)
    result = parser.finish()
    
    assert(result.ResponseMetadata.RequestId == 'b5bf2332-e983-4d3e-941a-f64c0d21f00f')
    assert(len(result.ReceiveMessageResult.Message))
    assert(result.ReceiveMessageResult.Message[0].Body == 'foo')
    assert(result.ReceiveMessageResult.Message[1].Body == 'bar')
    
  def testParseErrorMessage(self):
    self.XMLSchemaService.loadSchema('http://queue.amazonaws.com/doc/2008-01-01/QueueService.xsd', self)
    self.runLoop.run()
    assert(self.schema)
    parser = self.schema.newParser()
    parser.feed(error_response)
    result = parser.finish()
    self.assertEqual('Request must contain AWSAccessKeyId or X.509 certificate.', result.Error[0].Message)
    
  def testXMLWithUknownData(self):
    """SQS returned some xml with uknown attributes see <Message>...<Metadadat/>, which shouldn'd be allowed. 
    Since we don't control it though I ignore it.
    """
    self.XMLSchemaService.loadSchema('http://queue.amazonaws.com/doc/2008-01-01/QueueService.xsd', self)
    self.runLoop.run()
    assert(self.schema)
    parser = self.schema.newParser()
    parser.feed(message_response_with_uknown_elements)
    result = parser.finish()
    self.assertEqual('8f2770293f9b94ad705d5fd742f5f885', result.ReceiveMessageResult.Message[0].MD5OfBody)
  
      
  def didLoadSchema(self, url, schema):
    self.schema = schema
    self.runLoop.stop()
      
  def didFailToLoadSchema(self, url):
    self.runLoop.stop()
      
      
      
if __name__ == "__main__":
  unittest.main()

        
    