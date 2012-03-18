import cgi
import mimetypes
import types

import pkg_resources
import kid

from webob import Response
from webob.multidict import MultiDict, NestedMultiDict

try:
  import json
except ImportError:
  import simplejson as json

from rambler.net.webserver import erbtemplate
from Rambler import outlet


    
serializer=kid.HTMLSerializer()
serializer.doctype = None
class WebController(object):
  scheduler = outlet('Scheduler')
  Session = outlet('Session')
  
  templates = {}
  filter_chain = []
  rendered = False
  def __init__(self,request):
    #self.response = HTTPResponse()
    self.request = request
    self.response = Response(request=request)
    # Action is set by MVCMapper prior to calling process
    self.action = None
    self.response_started = False
    
    # Need to retain a ref to the templates during rendering..
    # retaining it in the instance var disables caching. Hacky
    self.templates = {}
    self.routing = None
    self._params = None
    
    
  def __getitem__(self, item):
    """Used by the eval call in render_template to interpret names"""
    return self.__dict__.get(item)
    
  @classmethod
  def before_filter(cls, filter):
    # Every web controller class caries it's own filter chain
    if not cls.__dict__.has_key('filter_chain'):
      cls.filter_chain = []
      
    if not callable(filter):
      filter = filter.filter
    cls.filter_chain.append(filter)
    
  def process(self):
    for filter in self.filter_chain:
      cont = yield (self.scheduler.call, filter, self)
      # Note filters must return the False 'object' not a false value, to stop filtering.
      if cont is False or self.rendered:
        raise StopIteration(self.response)
    
    action = self.action
    actionMethod = getattr(self, action)
    if(actionMethod):
      yield self.scheduler.call, actionMethod      
      
      if not self.rendered:
        self.render()
        
    if self.rendered:
      raise StopIteration(self.response)
      

  def render(self, **kw):
    # Find the template in the views directory and render it
    if 'template' in kw:
      self.render_template(kw['template'])
    elif 'text' in kw:
      self.response.content_type = 'text/plain'
      self.response.body = kw['text']
    elif 'json' in kw:
      self.response.content_type = 'application/json'
      self.response.body = json.dumps(kw['json'])
    elif 'generator' in kw:
      self.response.app_iter = kw['generator']
    elif 'file' in kw:
      f = kw['file']
      if not self.response.content_type:
        content_type, content_encoding = mimetypes.guess_type(f.name)
        if content_type:
          self.response.content_type = content_type
        else:
          self.response.content_type = 'application/octet-stream'
        
      self.response.app_iter = f #self.render_file(f)
    else:
      self.render_template(self.action)
    self.rendered = True
    
  def redirect_to(self, url):
    self.response.status ='302 Moved'
    self.response.headers['content-type'] ='text/html'
    self.response.headers['location'] =  url
    self.render(text='<html><body>moved to %s</body><html>' % url)
    
    
  def get_template(self, name):
    controller = self.__class__.__name__.lower()
    if controller.endswith('controller'):
      controller = controller[:-10]
      
    template = self.templates.get((controller, name))
    if template:
      return template
    else:
      try:
        resources = pkg_resources.resource_listdir(self.__class__.__module__, './views/%s/' % controller)
        for resource in resources:
          if resource.startswith(name):
            resource_name = resource
            break

        stream = pkg_resources.resource_stream(self.__class__.__module__, 
                                           './views/%s/%s' % (controller,resource_name))
        # Todo: Cache these templates
        if resource_name.endswith('kid'):
          t = kid.load_template(stream, ns={'template': self.get_template})
        else:
          t = erbtemplate.ERBTemplate()
          t.loadFromFile(stream)
        self.templates[(controller,name)] = t
        return t
      except IOError:
        return None

  def render_template(self, name):
    # Locate a view template for this controller and action
    self.response.headers['content-type'] = 'text/html'

    template = self.get_template(name)
    
    if template is None:
      self.render_missing_template() 
    elif type(template) == types.ModuleType:
      # kid template
      template = template.Template(**self.__dict__)
      self.response.app_iter = template.serialize(output=serializer)
    else:
      self.response.app_iter = template.render(self)

  def render_missing_template(self):
    self.response.body = 'Missing template for action %s' % self.action
    
  def session(self):
    session_id = self.request.cookies.get('session-id')

    if session_id:
      try:
        session = yield(self.Session.find,session_id)
        raise StopIteration(session)
      except KeyError:
        # Missing session provide a new one
        pass

    session  = yield self.Session.create()

    #yield session.save

    self.response.set_cookie('session-id',session.id)
      
    raise StopIteration(session)
        
  @property
  def params(self):
    """Returns params built with get, post and routing information."""
    if not self._params:
      self._params = NestedMultiDict(MultiDict(self.routing), self.request.params)
    return self._params

