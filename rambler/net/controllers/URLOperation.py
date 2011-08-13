from __future__ import with_statement

from Rambler import component, outlet,option
import tempfile


class URLOperation(component('Operation')):
  """Fetches a URL automatically retrying on errors."""
  
  log            = outlet('LogService')
  URLConnection  = outlet('URLConnection')
  URLRequest     = outlet('URLRequest') 
  run_loop       = outlet('RunLoop')
  
  retry_delay = 60

  is_concurrent = True
  
  @classmethod
  def assembled(cls):
    cls.rebase()  
    
  def __init__(self, url_pattern, *args, **kw):
    self.tempfile = None
    self.substitutions = {}
    self.url_pattern = url_pattern
    super(URLOperation, self).__init__()
    
  @property
  def body(self):
    if not self.finished:
      raise RuntimeError('Operation still in progress')
    else:
      if not hasattr(self, '_body'):
        self._body = self.tempfile.read()
      return self._body

  @property
  def result(self):
    return self
    
  @property
  def url(self):
    substitutions = self.substitutions
    url = self.url_pattern % substitutions
    return url
    
  def start(self):
    if self.is_cancelled:
      with self.changing('is_finished'):
        self.finished = True
      return
      
    with self.changing('is_executing'):
      self.executing = True
    assert self.tempfile == None
    self.tempfile = tempfile.SpooledTemporaryFile(max_size=1024)
    
    try:
      request = self.URLRequest(self.url)
      self.URLConnection.connectionWithRequest(request, self)
    except Exception, e:
      self.did_fail_with_error(None, e)
      
  def retry(self):
    """Attempt the download in XX seconds."""
    if self.is_cancelled:
      self.log.warn("Operation cancelled retry aborted")
      with self.changing('is_finished', 'is_executing'):
        self.finished = True
        self.executing = False
      return
    
    
    self.log.warn('Retrying download %s in %s seconds', self.url, self.retry_delay )
    self.tempfile.close()
    self.tempfile = None
    self.run_loop.currentRunLoop().waitBeforeCalling(self.retry_delay, self.start)
    
  def index(self):
    """Called by the AuctionService when all download operations are complete and the data should
    be indexed."""
    raise NotImplmented

    
  def did_receive_response(self, connection, response):
    connection.user_info['code'] = getattr(response, 'statusCode', 200)
    self.code = connection.user_info['code']

  def did_receive_data(self, connection, data):
    self.tempfile.write(data)
  
  def did_finish_loading(self, connection):
    
    code = connection.user_info.pop('code')
    
    self.log.info('%s %s', connection.request.url, code)    
    if not self.is_cancelled and code != 200:
      self.tempfile.seek(0)
      self.log.info(self.tempfile.read())
      # Retry in xx minutes
      self.retry()
    else:
      with self.changing('is_finished', 'is_executing'):
        self.finished = True
        self.executing = False
        self.tempfile.seek(0)
            
  def did_fail_with_error(self, connection, error):
    self.log.error("%s while fetching %s ", error, self.url)
    self.retry()
