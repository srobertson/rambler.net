import xml.sax

from Rambler import outlet
from rambler.net.xsd import XSDSchemaHandler

class XMLSchemaFactory(object):
  """Constructs parsers for XML defined by schema's at a given URL.
  
  Usage: Create a delegate with a didLoadSchema(url, schema) method. This method will
  be invoked by the service when the schema has been loaded from the network and is
  ready to start parsing documents
  
  Example:
  
  >>> class SchemaDelegate(object):
  ...   def didLoadSchema(self, url, schema):
  ...     self.schema = schema
  ...
  

  To get a parser that can parse XML documents based on the schema you must first load the
  schema
  >>> delegate = SchemaDelegate()
  >>> parser = XMLSechemaService.loadSchema('http://examlp.com/some_schema.xsd', delegate)
  >>> # RunLoop.currentRunLoop().run()
  
  >>> parser = delegate.schema.newParser()
  
  >>> data = '''\
  ... <DeleteMessageResponse>
  ...   <ResponseMetadata>
  ...    <RequestId>cb919c0a-9bce-4afe-9b48-9bdf2412bb67</RequestId>
  ...   </ResponseMetadata>
  ...</DeleteMessageResponse>'''
  
  >>> parser.feed(data)
  >>> delete_message_response = parser.finish()
  >>> delete_message_response.ResponseMetadata.RequestId
  cb919c0a-9bce-4afe-9b48-9bdf2412bb67
  
  """
  
  log = outlet("LogService")
  URLConnection = outlet('URLConnection')
  schemasByURL = {}
  
  
  @classmethod
  def loadSchema(cls, url, delegate):
    schema = cls.schemasByURL.get(url)
    if schema is None:
      # First time someone has asked for this schema, fetch it
      schema = cls(url)
      cls.schemasByURL[url] = schema
      
    # Schema object will notify it's delegates when it's ready to begin
    # parsing by invoking delegate.didLoadSchema(schema)
    schema.addDelegate(delegate)

  def __init__(self, url):
    self.url = url
    self.loaded = False
    self.delegates = []
    # Start loading the URLs
    self.URLConnection.connectionWithRequest(url, self)
    
    self.schema_parser = xml.sax.make_parser()
    self.schema_handler = XSDSchemaHandler()
    self.schema_parser.setContentHandler(self.schema_handler)
    self.bytes = 0
    
  def didReceiveResponse(self, connection, response):
    # http url's will have a status code
    self.waitingFor = response.expectedContentLength
    
    if hasattr(response, 'statusCode') and response.statusCode != 200:
      # if it's not 200, the server reported an error
      self.notifyFailure(response)
        
  def didReceiveData(self, connection, data):
    self.bytes += len(data)
    self.schema_parser.feed(data)

    
  def didFinishLoading(self, connection):
    self.schema_parser.close()
    self.loaded = True
    # notify our delegates that the schema is ready for use
    while self.delegates:
      delegate = self.delegates.pop()
      delegate.didLoadSchema(self.url, self)
      
  
  def did_fail_with_error(self, connection, error):
    self.log.warn("Error loading schema @ %s", connection.request.url)
    self.notifyFailure(connection, error)
      
  def addDelegate(self, delegate):
    """Add delegate will only keep a ref to the delegate until the schema is fully loaded
    or had an error loading"""
    if self.loaded:
      delegate.didLoadSchema(self.url, self)
    else:
      self.delegates.append(delegate)
    
  def notifyFailure(self, response, error):
    for delegate in self.delegates:
      delegate.didFailToLoadSchema(self.url, response, error)
      
  def newParser(self):
    """Returns a parser capable of parsing XML for the given Schema."""
    if self.loaded:
      return self.schema_handler.newHandler()
    else:
      raise RuntimeError('newParser can not be invoked until the Schema is loaded')
