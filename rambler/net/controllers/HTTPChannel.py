import urllib2

from xml.dom import minidom

from Rambler import outlet

class HTTPChannel(object):
  """Preforms Asynchronous HTTP client requests.

  Users of the Javascript XMLHttpRequest object should be
  familliar."""

  READY_STATE_UNINITIALIZED = 0
  READY_STATE_LOADING       = 1
  READY_STATE_LOADED        = 2
  READY_STATE_COMPLETE      = 4

  def __init__(self):
    self.onreadystatechange = None
    self.onerror = None
    self.url = None
    self.readyState = self.READY_STATE_UNINITIALIZED
    self.dom = None
    self._status = None
    self.headers ={}

  def open(self, method, url, async):
    self.method = method
    self.url = url
    
    
  def setRequestHeader(self, header, value):
    self.headers[header] = value

  def send(self, data=None):
    self.req = req = urllib2.Request(self.url, data, self.headers)
    
    self.readyState = self.READY_STATE_LOADING
    self.onreadystatechange(self)
    # gahhh, signals will interupt this call. Need to implement proper async
    
    
    while 1:
      try:
        f=self.response = urllib2.urlopen(self.req)
        break
      except urllib2.URLError, e:
        # if it's not an io error 4, interupted system
        if len(e.args) and e.args[0][0] == 4:
          continue
        else:
          raise

    self.readyState = self.READY_STATE_LOADED
    self.onreadystatechange(self)

    self.headers = f.headers
    self.responseText = f.read()
    self.readyState = self.READY_STATE_COMPLETE
    self.onreadystatechange(self)

  @property
  def responseXML(self):
    if not self.dom:
      self.dom = minidom.parseString(self.responseText)
    return self.dom
  
  @property
  def status(self):
    if self._status is None:
      self._status = self.response.code
    return self._status

if __name__ == "__main__":
  channel = HTTPChannel()
  def handler(request):
    if request.readyState == HTTPChannel.READY_STATE_COMPLETE:
      print request.responseText

  channel.onreadystatechange = handler
  channel.open('GET','http://localhost', True)
  channel.send()
