import sys
import unittest
import time

from Rambler.TestCase import TestCase
import uuid
import json


class TestSQSMonitor(TestCase):
  extra_extensions =  ['rambler.net']
    
  def setUp(self):
    super(self.__class__,self).setUp()
    self.sqsMonitor = self.comp
    self.uuid = str(uuid.uuid1())
    
  def test_micro_threaded_receive(self):
    self.count = 10
    
    self.sqsMonitor.monitor_queue('blah', .5, self)
    self.wait(60)
    self.assertEqual(self.count, 0)
    
  def test_dlq(self):
    pass
    
  def send_messages(self, queue_name, count):
    # Send a 200 byte long message 
    
    for x in range(count):
      self.sqsMonitor.send_message(queue_name, json.dumps({'uuid': self.uuid, 'time':time.time()}))

  def on_sqs_connect(self):
    # Called when the SQS  is ready to start sending or receiving messages
    self.send_messages('blah', self.count)
    
  def on_sqs_message(self, queue_name, sqs_message):

    def invocation(sqs_message):
      message = json.loads(sqs_message.Body)
      return message

    x = yield(self.InvocationOperation.new, invocation, sqs_message)
    
    # Ignore messages not placed in the queue by us, might be nice to signal that they should not
    # be deleted
    if x['uuid'] == self.uuid:
      self.count -= 1    
      print  "%6.2fms" % ((time.time() - x['time']) * 1000)
      if self.count == 0:
        self.quit()
    else:
      print "Ignoring"

    
  def onSQSErrorResponse(self, queue_name, error):
    self.runLoop.stop()

        
if __name__ == "__main__":
  unittest.main()

