"""Module contains code classes needed by the XMLSchemaService.

Developers/Components should not imort this code directly.
"""
import copy
import xml.sax
import xml.sax.handler


class XSDResult(object):
  def __init__(self, name):
    self.name = name

    
  def __repr__(self):
    return "<%s(%s) instance at (%s) >" % (self.__class__.__name__, self.name, id(self))
    
  def __getitem__(self, key):
    if not key.startswith('__'):
      return getattr(self, key)
      
class XSDAny(object):
  defaults = {'name': None,
              'ref': None,
              'maxOccurs': 1,
              'minOccurs': 1,
              'type': None}
              

  def __init__(self, attributes):
    
    self.attributes = attributes
    for attr, default in self.defaults.items(): 
      try:
        v = attributes.getValue(attr)
        setattr(self, attr, v)
      except KeyError:
        setattr(self, attr, default)

  def canBuild(self, name):
    """We can build anything!"""
    return True
    
  def addChild(self, child):
    # We don't handle children... yet
    pass
    
  def newNode(self, attributes):
    self.data = []
    return self.data
    
  def characters(self, content):
    self.data.append(content)
    
  def endElement(self, nodes):
    value = "".join(nodes[-1])
    nodes[-1] = value
    self.data = None
    
class XSDElement(object):
  defaults = {'name': None,
              'ref': None,
              'maxOccurs': 1,
              'minOccurs': 1,
              'type': None}
    
  def __init__(self, attributes):
    self.attributes = []
    
    for attr, default in self.defaults.items(): 
      try:
        v = attributes.getValue(attr)
        setattr(self, attr, v)
      except KeyError:
        setattr(self, attr, default)
        
    if self.ref:
      name = self.ref.split(':')[1]
      self.name = self.name or name

  def __repr__(self):
    return "<name: %s  ref: %s type: %s >" % (self.name, self.ref, self.type)
        
  def addChild(self, child):
    self.attributes.append(child)
    
  def canBuild(self, name):
    return self.name == name
    
  def newNode(self, attributes):    
    if self.type in ('xs:string', 'xs:integer'):
      self.data = []
      return self.data
    else:
      return XSDResult(self.name)
      
  def characters(self, content):
    if self.type in ('xs:string', 'xs:integer'):
      self.data.append(content)
    
  def endElement(self, nodes):
    if self.type in ('xs:string', 'xs:integer'):
      value = "".join(nodes[-1])
      if self.type == 'xs:integer':
        value = int(value)
      nodes[-1] = value
      self.data = None

class SchemaBasedParser(xml.sax.ContentHandler):
  def __init__(self, types):
    self.types = types
    self.parser = xml.sax.make_parser()
    # Todo: clean up this cicrular dependency when the object is destroyed
    self.parser.setContentHandler(self)
    self.root = None
    
  def setParser(self, parser):
    parser.setContentHandler(self)
    self.parser = parser
    
  def feed(self, data):
    self.parser.feed(data)
    
  def finish(self):
    """Called to inform the parser that no more data will be coming and it's ok to return
    the root object."""
    self.parser.close()
    return self.root
  
  def startDocument(self):
    self.nodes = []
    self.builders = None
    self.next_handler = None
    
  def startElement(self, name, attributes):
    # note the copying is important since we use that to track which
    # child elments will be next
    
    if self.builders is None:
      # root element
      #builder = copy.deepcopy(self.types[name])
      builder = self.types[name]
      self.builders= [builder]
    elif self.builders[-1] == None:
      # We're ignoring the parent so we ignore the child
      builder = None
      self.builders.append(builder)
    else:
      # ignore order, 
      builder = None
      for attr in self.builders[-1].attributes:
        if attr.canBuild(name):
          builder = attr
          break
                              
      if builder  and builder.ref is not None:
        # cheesey
        ref = builder
        builder = copy.deepcopy(self.types[builder.name])
        builder.minOccurs = ref.minOccurs
        builder.maxOccurs = ref.maxOccurs
      #else:
      #  builder = copy.deepcopy(builder)
      self.builders.append(builder)

    if builder:
      self.nodes.append(builder.newNode(attributes))
    
  def characters(self,content):
    # if builder is None, we ignore everything
    builder = self.builders[-1]
    
    if builder and hasattr(builder, 'characters'):
      builder.characters(content)
    
  def endElement(self, name):
    builder = self.builders.pop()
    if builder:
      builder.endElement(self.nodes)
    
      node = self.nodes.pop()
      if len(self.nodes) == 0:
        self.root = node
        return
    
      # if maxOcurrs is 1, don't wait for any more
      if builder.maxOccurs == 1:
        setattr(self.nodes[-1], name, node)
      else:
        if not hasattr(self.nodes[-1], name):
          setattr(self.nodes[-1], name, [])
        getattr(self.nodes[-1], name).append(node)
  

class XSDSchemaHandler(xml.sax.ContentHandler):
  schema_handlers = {'xs:element': XSDElement, 'xs:any': XSDAny}
  
  def __init__(self):
    self.types = {}
  
  def startDocument(self):
    self.parents = [self]
    
  def startElement(self, name, attrs): 
      
    cls = self.schema_handlers.get(name)
    if cls:
      instance = cls(attrs)
        
      self.parents[-1].addChild(instance)
      self.parents.append(instance)
       
  def endElement(self, name):
    if name in self.schema_handlers:
      self.parents.pop()
    
  def addChild(self, builder):
    self.types[builder.name] = builder
  
  def newHandler(self):
    """Returns an new SAXHandler that can read XML based on the schema read"""

    # Create a parser based on schema
    return SchemaBasedParser(self.types)
    
