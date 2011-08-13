import sys
from Rambler import outlet, Interface, Attribute, implements

from StringIO import StringIO

class ILineReceiverDeligate(Interface):
    """This interface sholud be implemented by the LineReceiverProtocal's delegate."""
    

    def onLineFrom(line, port):
        """Invoked by the calling protocol object to notify that a line has
        been read. The port is passed to the delegate so that the
        delegate can support multiple ports at the same
        time. 

        The return value of this method indicates what mode the
        protocol should use for reading data from the port.
        
        If the delegate returns None, then the protocol will remain in
        Line Receive mode.
        
        If the delegate returns a number, the protocol will switch to
        raw data mode and whill inovke onBlobFrom() method of the
        delegate when the returned number of bytes have been read from
        the transport.

        """
        
    def onRawDataFrom(blob, port):
        """Invoked when the requested length of data has been recived.  

        The return value of this method indicates what mode the
        protocol should use for reading data from the port.

        If the delegate returns None, then the protocol will switch to
        Line Receive mode.
        
        If the delegate returns a number, the protocol will remain in
        raw data mode and whill inovke onBlobFrom() method of the
        delegate when the returned number of bytes have been read from
        the transport.
        """

    def onBufferOverflowFrom(port):
        """Invoked when the maximum amount of data the buffer can hold has
        been reached prior to finding the line delimiter"""


        

class LineReceiverProtocol(object):
    """Used for line oriented proctols. Reads a socket buffering the data
    until a line delimeter has been found (normaly the CRLF), once
    found it's delegate.onLineRecivedFrom() method is invoked passing
    the delegate the line that was received and the underlying
    transport object that the data was received from..
    
    Usage:

    You'll need to implement a delegate object for the
    LinceReceiverProtcol that implements the ILineReceiveryDelegate
    interface. Once done simply create an instance of the
    LineReceiveryProtocol object and set the delegate and transoprt
    methods.

    For example here's a delegate that takes lines of text fromated something like this
    
    Line 1: Blah
    Line 2: Foo

    And converts the raw lines into a dictionary like this
    {'Line 1': 'Blah', 'Line 2': 'Foo'}
    

    >>> class MyDelegate(object):
    ...   implements(ILineReceiverDeligate)
    ...   def __init__(self):
    ...     self.data = {}
    ...
    ...   def onLineFrom(self, line, protocol):
    ...     if (line):
    ...       key,value = line.split(':')
    ...       self.data[key.strip()] = value.strip()
    ...     else: # recived empty string,
    ...       self.dictDone()
    ...  
    ...   def onClose(self, protocol):
    ...     self.dictDone()
    ...
    ...   def dictDone(self):
    ...     print self.data
    ...     self.data = {}
        

    Once you delegate is defined, you instantiate it along with the
    transport such as a internet socket, unix port etc and set it on
    an instance of LineReceiverProtocol.

    >>> lrp = LineReceiverProtocol()
    >>> from tests import StreamTransport
    >>> lrp.setTransport(StreamTransport('''Line 1:Bar\\nLine 2:Baz\\n\\nFake: Fop\\n'''))
    >>> lrp.delegate = MyDelegate()

    * Note this may be bunk* 
    Once the appropriate attributes have been set on the instance of
    Line Receiver Protocol we need to tell the protocl to start reading
    lines.

    * Current proccess * 
    
    The LineReriverProtocol object will immediatly start reading from
    the transport once setTransport() is called, and continue  keep reading
    from it until the connection is closed.

    Now that we're all setup, we need to let the RunLoop.run() which
    will handle pumping the data.  For Testing purposes we'll use a
    runLoop which needs us to wire the logging service up for
    reporting errors.
    
    >>> from Rambler.LoggingExtensions import LogService
    >>> logService = LogService()
    >>> import sys
    >>> logService.useStreamHandler(sys.stderr)
    >>> from Rambler.RunLoop import RunLoop
    >>> RunLoop.log = logService.__binding__('LRPTest',None)

    >>> runLoop = RunLoop.currentRunLoop()
    
    Run the runLoop for no more than 5 seconds, this test should quit
    before that, but if something goes wrong this will keep everything
    from being locked up.

    >>> runLoop.runUntil(seconds=5)
    {'Line 1': 'Bar', 'Line 2': 'Baz'}
    {'Fake': 'Fop'}

    The protocol can also be used by ports that are listenting for
    incoming connections. To do this simply create a port, set the
    protocol as it's delegate and then tell the port to listen. We'll
    mimic this behaviour in our tests by creating a test port and
    calling the LRP's onAccept method directly.

    >>> incomingPort = StreamTransport('''Line 3:Look Ma\\nLine 4:More text\\n''')
    >>> lrp.onAccept(incomingPort)
    >>> runLoop.runUntil(seconds=5)
    {'Line 3': 'Look Ma', 'Line 4': 'More text'}

    Many line oriented protocols, such as HTTP, switch back and forth
    between being line oriented and reading a specific number of
    bytes. What we call "raw mode". A delegate can switch the protocol
    to raw mode by returning a number of bytes to be "read raw" from
    the onLineReceivedFrom().

    Here's an example delgate that will receive a bunch of lines from
    the LRP and convert them to a dictionary like we did in the
    previous example. However if after receiving a blank line we find
    the key "Content-length" in the data, we'll return that key's
    value as the number of bytes we want to be read from the transport
    raw.

    
    >>> class MyRawDelegate(object):
    ...   implements(ILineReceiverDeligate)
    ...   def __init__(self):
    ...     self.data = {}
    ...
    ...   def onLineFrom(self, line, port):
    ...     if (line):
    ...       key,value = line.split(':')
    ...       self.data[key.strip()] = value.strip()
    ...     else: # recived empty string,
    ...       return self.dictDone()
    ...
    ...   def onRawDataFrom(self, data, port):
    ...     print data
    ...    
    ...   def onClose(self, protocol):
    ...     self.dictDone()
    ...
    ...   def dictDone(self):
    ...     print self.data
    ...     if self.data.has_key('Content-length'):
    ...       # Content length present tell our protocol to read that many bytes 'raw'
    ...       ret =  int(self.data['Content-length'])
    ...     else:
    ...       # No content length, returning None keeps us in Line Receive Mode
    ...       ret = None
    ...     self.data = {}
    ...     return ret

    >>> incomingPort = StreamTransport('Content-length: 8\\n\\nRaw DataState: Back to line Mode\\n')
    >>> lrp.delegate = MyRawDelegate()
    >>> lrp.onAccept(incomingPort)
    >>> runLoop.runUntil(seconds=5)
    {'Content-length': '8'}
    Raw Data
    {'State': 'Back to line Mode'}

    

    """

    BYTES_TO_READ=4096
    delimiter = '\n'

    def __init__(self):
        self.buffersForPort = {}


    # TODO: consider removing setTransport, instead the user must
    # create the port then, set port.delegate = LRP

    def setTransport(self, transport):
        transport.delegate = self
        self.transport = transport
        
        # this is ugly, mostly cause I haven't made up my mind whether
        # a protocol object sholud be responsible for setting up a
        # port

        if hasattr(transport, 'connect'):
            transport.connect()
        else:
            # it's a stream, start reading imediatly
            self.onConnect(self.transport)
        # start reading lines


    def sendLine(self, line):
        self.transport.write(line)
        self.transport.write(self.delimiter)
    
    def onConnect(self, port):
        self.buffersForPort[port] = (StringIO(), None)
        port.read(self.BYTES_TO_READ)
        if(hasattr(self.delegate,'onConnect')):
            # NOTE: Delegate should not attempt to read from this port
            self.delegate.onConnect(port)

    def onAccept(self, port):
        # our transport is listening for new connecetions
        port.delegate = self
        self.onConnect(port)
            
    def onRead(self, port, data):
        # new data just came in:
        buffer,waitingForBytes = self.buffersForPort[port]
        # set a pointer to the first character in the data
        delimiterLen = len(self.delimiter)
        pos  = buffer.tell() # this should be the end of the buffer
        lpos = 0
        size = len(data) + pos
        if waitingForBytes is None:
          pos -= delimiterLen
          if pos < 0:
            pos = 0
        buffer.write(data)
        buffer.seek(pos)
       
        #  pointer that points to the last terminator read, which
        #  start with is the beginging of the buffer
        while(pos < size):
            # while we haven't reached the last character

            #  if waitigForBytes is greater than 0 attempt to read that
            if waitingForBytes is not None: # We're in raw mode
                if waitingForBytes > (size - pos):
                    # we haven't got all the data that we want, store
                    # what we have and wait for some more
                    buffer.seek(size)
                    waitingForBytes -= (size - pos)
                    pos = size
                    continue
                else:

                    # We've received the number of raw bytes we were
                    # waiting for. So we'll grab it out of the stream
                    # and pass it to our delegate.
                    pos += waitingForBytes
                    buffer.seek(lpos)
                    blob = buffer.read(pos - lpos)
                    lpos = pos
                    
                    # If the delegate wants more raw data it will
                    # return a number of bytes. If not it will return
                    # None, meaning revert to Line Receive mode.
                    waitingForBytes = self.delegate.onRawDataFrom(blob, port)
            else:
                # If waitingForBytes is not a number, then we're in
                # line receive mode so look at the next X bytes in the
                # stream (X = the length of the line delimimeter) and
                # see if it matches the line delimiter.
                
                # achtung, technically we may need to look back into
                # the buffer in case part of the delimiter is hiding
                # in it.
                spos = buffer.tell()
                chars = buffer.read(delimiterLen)
                
                if (chars == self.delimiter):                   
                    #  We've fonud the end of a line, lets reconstruct
                    #  the line and notify our delegate
                    buffer.seek(lpos)
                    line = buffer.read(pos - lpos)
                    # move over the delimiter
                    pos += delimiterLen
                    buffer.seek(pos)
                    lpos = pos
                    
                    waitingForBytes = self.delegate.onLineFrom(line, port)
                else:
                    #  If the line delimeter was not found, we simply advance the
                    #  currentPosition and repeat the loop.
                    
                    pos += 1
                    buffer.seek(pos)

        # We've read through all the incoming data. We're now going to
        # wait for some more before we do that we'll need to decapitatee
        # our buffer (i.e. dump the data that's been sent to our
        # delegate so far)

        buffer.seek(lpos)
        remaining = buffer.read(size - lpos)
        buffer.seek(0)
        buffer.write(remaining)
        buffer.truncate()

        self.buffersForPort[port] = buffer,waitingForBytes

        # and now have the system notify us when more data comes in
        port.read(self.BYTES_TO_READ)



                        
    def onWrite(self, port, bytesWritten):
        pass
            
    def onClose(self, port):
        # there will be no more data, so give the LRP's delegate a chance to deal with any data
        # that may still be in the buffer, not we 0 out waiting for bytes, kind of hacky
        buffer, waitingForBytes = self.buffersForPort[port]
        if waitingForBytes > 0: # in line mode
          buffer.seek(0)
          blob = buffer.read()
          self.delegate.onRawDataFrom(blob, port)
        self.delegate.onClose(port)
        del self.buffersForPort[port]


    def onError(self, port, error):
        self.delegate.onError(port, error)
        




                                
        
        
