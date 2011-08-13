from Rambler import outlet, load_classes

class URLProtocol(object):
  protocol_classes = []
  componentRegistry = outlet('ComponentRegistry')
  app = outlet('Application')
  @classmethod
  def assembled(cls):
    if cls is URLProtocol: # Don't run this method for components who inherit from URLProtocol
      mod_names = ['Rambler', cls.app.name] + [ext.name for ext in cls.app.config.extensions]
      classes = []
      for mod_name in mod_names:
        mod_full_name = mod_name + ".url_protocols"
        classes = list(load_classes(mod_full_name,cls))
        for protocol_class in classes:
          cls.componentRegistry.addComponent(
              protocol_class.__name__,
              protocol_class)
          cls.registerClass(protocol_class)
                
  @classmethod
  def registerClass(cls, protocolClass):
    if issubclass(protocolClass, object):
      cls.protocol_classes.insert(0, protocolClass)
    else:
      raise ValueError("Must be a subclass of %s" % cls.__name__)
      
  @classmethod
  def canInitWithRequest(cls, request):
    raise NotImplmented, "Subclass must implement this class method"

  @classmethod
  def protocolForRequest(cls, request, cachedResponse, client):
    """ Returns an instance of the first protocol class that can handle the request """
    for protocol_cls in cls.protocol_classes:
      if protocol_cls.canInitWithRequest(request):
        return protocol_cls(request, cachedResponse, client)

    
  def __init__(self, request, cachedResponse, client):
    self.request = request
    self.cachedResponse = cachedResponse
    self.client = client
  