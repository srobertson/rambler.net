class URLResponse(object):
  def __init__(self, URL, MIMEType=None, expectedContentLength=None, textEncodingName=None):
    self.URL = URL
    self.MIMEType = MIMEType
    self.expectedContentLength = expectedContentLength
    self.textEncodingName = textEncodingName

  @property
  def suggestedFilename(self):
     """Returns a suggested filename
     
     The method tries to create a filename using the following, in order:
     
     1. A filename specified using the content disposition header.
     2. The last path component of the URL.
     3. The host of the URL.
     """
     
     return self.URL.path.split('/')[-1]
     

    