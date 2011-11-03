import base64
import cgi
import os
import hmac
import urllib
import time

import traceback
import yaml

from collections import defaultdict

from hashlib import sha1 as sha

import xml.sax
from datetime import datetime

from Rambler import outlet, option,nil
from Rambler.LRU import LRU

class SQSMonitor(object):
  """This service is used to monitor one or more SQS queues.
  
  To use define a delegate with a on_sqs_message(queue_name, message) method.
  
  >>> class SQSDelegate:
  ...   def on_sqs_message(queue_name, message):
  ...     print queue_name, message
  
  Then register it with this service by calling monitor_queue with the name of the 
  queue and how often in seconds the queue should be polled
  
  >>> SQSMonitor.monitor_queue('work', 5, SQSDelegate)
  
  The monitor will invoke the delegate's on_sqs_message once for each message in
  the queue. The message will be removed from the queue if on_sqs_message returns
  with no errors. Otherwise if an exception is thrown, the message will be moved to
  the DLQ
   
  
  """
  runLoop = outlet('RunLoop')
  URLRequest = outlet('URLRequest')
  URLConnection = outlet('URLConnection')
  log = outlet('LogService')
  configService = outlet('ConfigService')
  Stat = outlet('Stat')
  scheduler = outlet('Scheduler')
  TimeSeries = outlet('TimeSeries') 
  
  XMLSchemaFactory = outlet('XMLSchemaFactory')
  
  intervalInSeconds = option('aws','sqs_check_interval', 15)
  
  sqs_url_prefix = option('aws', 'sqs_url_prefix', 'http://queue.amazonaws.com')
  create_missing_queues = option('aws', 'create_missing_queues', True)
  lru_size = option('aws','sqs_lru_size', 100)
  
  # Todo: allow for checking of multiple queues with configurable timeouts
  dl_queue_name = option('aws', 'dl_queue_name' )
  
  
  aws_access_key = option('aws', 'access_key')
  aws_secret_key = option('aws', 'secret_key')
  
  SQSSchemaURL = "rambler://rambler.net.aws/schemas/QueueService.xsd"
  
  def assembled(self):
    self.sqs_lru = LRU(self.lru_size)
    self.queues = {}
    self.stats_by_queue = {}
    self.proc_time_by_queue = {}
    
    self.poll_count_by_queue = {}
    
    self.other_counts =  self.TimeSeries("SQS Stats")#defaultdict(int)
    
    # Log stats to starndard output every 10 minute
    # can verify that everything is running ok
    #self.runLoop.currentRunLoop().intervalBetweenCalling('FREQ=MINUTELY;INTERVAL=1', self.log_stats)
    self.sqs_schema = None
    self.log.info('Loading SQS Schema from %s', self.SQSSchemaURL)
    self.XMLSchemaFactory.loadSchema(self.SQSSchemaURL, self)
    
    
  def log_stats(self):   
    #for queue_name, count in self.poll_count_by_queue.items():
    #  # update the stats
    #  stats = self.stats_by_queue[queue_name]
    #  stats.tally(count)
    #  self.log.info("Last count %s - Overall %s", count ,stats)
    #  self.poll_count_by_queue[queue_name] = 0
      
    for queue_name, proc_stats in self.proc_time_by_queue.items():
      self.log.info('Proc length for %s %s ', queue_name, proc_stats)
      
    #for key, count in sorted(self.other_counts.items()):
    #  self.log.info("%s: %s", key, count)
    
  def collectProcTime(self, queue_name, message):
    # Collects elapsed time from receiving to deleting or returning the message to
    # the queue
    stats = self.proc_time_by_queue[queue_name] 
    stats.tally(time.time() - message.__recved_time)
        
  def monitor_queue(self, name, interval, delegate):
    self.log.info("Monitoring queue %s", name)
    self.queues[name] = (interval, delegate)
    self.stats_by_queue[name] = self.Stat('%s poll count' % name)
    self.proc_time_by_queue[name] = self.Stat('%s process times' % name)
    self.poll_count_by_queue[name] = 0

    if self.sqs_schema:
      # if we have a the  SQS schema loaded we can poll the queue imediatly,
      # if not.. didLoadSchema will poll all the monitored queues after the schema
      # has finished loading
      self.runLoop.currentRunLoop().waitBeforeCalling(0, self.poll, name)
  
  def didLoadSchema(self, URL, schema):
    self.log.info('Loaded SQS Schema, polling queues')
    self.sqs_schema = schema
    
    for delegate in set([delegate for i, delegate in self.queues.values()]):
      if hasattr(delegate, 'on_sqs_connect'):
        delegate.on_sqs_connect()
      
    
    for queue_name in self.queues:
      self.runLoop.currentRunLoop().waitBeforeCalling(0, self.poll, queue_name)
    
    
  def poll(self, queue_name):
    """Internal call to Schedule an SQS request in the run loop. """

    #self.log.info('Checking %s', queue_name)
    #self.poll_count_by_queue[queue_name] += 1
    
    self.other_counts.count('poll_count_' + queue_name)
    
    params = self.build_receive_message()    
    url = "%s/%s?%s" %  (self.sqs_url_prefix, queue_name, urllib.urlencode(params))
    request = self.URLRequest(url, cachePolicy=self.URLRequest.ReloadIgnoringLocalCacheData )

    connection = self.URLConnection.connectionWithRequest(url, self)
    connection.userInfo['queue_name'] = queue_name
    connection.userInfo['parser'] = self.sqs_schema.newParser()
    # Incase we have an error, onSQSErrorResponse needs to know to
    # repoll the specified queue.
    connection.userInfo['sqs_action'] = 'ReceiveMessage'

  def did_receive_response(self, connection, response):
    connection.user_info['code'] = getattr(response, 'statusCode', 200)
  
  def did_receive_data(self, connection, data):
    connection.userInfo['parser'].feed(data)
   
  def dlq_message(self, queue_name, sqs_message, **errors):
    # Places the message into the dlq along with diagnostic information
    body = sqs_message.Body

    errors['queue_name'] = queue_name
    errors['sqs_id'] = sqs_message.MessageId
    
    self.other_counts.count('dlq_messages')
    
    self.send_message(self.dl_queue_name, body + '\n---\n' + yaml.dump(errors,default_flow_style=False))
    
  def will_cache_response(self, connection, cached_response):
    # don't cache SQS Responses
    return None
    
  def did_finish_loading(self, connection):
    code = connection.user_info.pop('code')
    if not str(code).startswith('2'):
      self.log.warn("SQS Returned status code %s", code)
    
    try:
      result = connection.userInfo.pop('parser').finish()
    except xml.sax.SAXParseException,e:
      # this seems to happen if the SQS connection is closed w/o
      # sending us any xml. Not sure why this is happening. Timeout possibly?
      return self.did_fail_with_error(connection, e)
    
    queue_name = connection.userInfo.pop('queue_name')
    # dispatch the response to the appropriate callback
    method_name = 'onSQS%s' % result.name
    
    method = getattr(self, method_name)
    method(queue_name, result, **connection.userInfo)
        
  def did_fail_with_error(self, connection, error):
    queue_name = connection.userInfo['queue_name']
    interval, delegate = self.queues[queue_name]
    # hopefully it's temporary, poll again
    self.other_counts.count('connection_errors_' + connection.userInfo.get('sqs_action',''))
    self.log.error('Error "%s" while communicating with SQS Queue %s.', error, queue_name)
    
    if connection.userInfo.pop('sqs_action','') == 'ReceiveMessage':
      self.runLoop.currentRunLoop().waitBeforeCalling(interval, self.poll, queue_name)
    # TODO: Consider counting how many comm errors we receive and notifying the admin
    # after a threshold has been hit
  
  def on_sqs_receive(self, queue_name, messages):
    interval, delegate = self.queues[queue_name]
    
    count = 0
    for message in messages:
      message_id = message.MessageId
      count += 1
      self.other_counts.count('received_messages')
      if message_id not in self.sqs_lru:
        self.sqs_lru[message_id] = None
        message.__recved_time = time.time()
        try:
          yield (self.scheduler.call, delegate.on_sqs_message, queue_name, message)
        except Exception, e:
          self.log.exception('Exception encountered with %s', message_id)
          self.dlq_message(queue_name, message, traceback=str(traceback.format_exc()), 
                                 exception=e.__class__.__name__)
          
        self.delete_message(queue_name, message)
      else:
        self.log.warn("Ignoring previously seen message %s", message_id)
      
    if count == 0:
      # No messages sleep for the designated time then recheck
      #self.log.info('Delaying %s before checking  %s', interval, queue_name)
      self.runLoop.currentRunLoop().waitBeforeCalling(interval, self.poll, queue_name)
    else:
      # We had messages, poll immediatly
      self.runLoop.currentRunLoop().waitBeforeCalling(0, self.poll, queue_name)
  
  def onSQSReceiveMessageResponse(self, queue_name, sqs_response, sqs_action=None):
    """Called when polling finishes."""
    interval, delegate = self.queues[queue_name]
    messages = getattr(sqs_response.ReceiveMessageResult, 'Message', [])
    if messages:
      self.log.info("Received %s in %s", len(messages), queue_name)
    
    self.scheduler.call(self.on_sqs_receive, queue_name, messages)
      
  def onSQSCreateQueueResponse(self, queue_name, sqs_response):
    """Called on a succesful CreateQueue request. If we're monitoring the queueu
    we'll start polling it."""
    
    if queue_name in self.queues:
      self.runLoop.currentRunLoop().waitBeforeCalling(0, self.poll, queue_name)
      
  def onSQSDeleteMessageResponse(self, queue_name, sqs_response, message):
    """Called when a message has been sucesfully deleted.  AWS docs 
    say this request will only fail if the request was malformed. It does not 
    gurantee the message is deleted."""
    self.other_counts.count('delete_success')
    self.log.info('Deleted Message %s', message.MessageId)
      
  def onSQSSendMessageResponse(self, queue_name, sqs_response, message_body, callback, queue_time):
    """Called when a message has been sucessfully sent to an sqs queue."""
    
    self.other_counts.count('sent_message_success_%s' % queue_name)
    elapsed = (time.time() - queue_time) * 1000
    self.log.info('Message %s:%s queue in %6.2fms', sqs_response.SendMessageResult.MessageId, 
      queue_name, elapsed)
    if callback:
      callback(message_body)
      
  def onSQSErrorResponse(self, queue_name, sqs_response, sqs_action=None, *args, **kw):
    self.other_counts.count('sqs_errors_%s' % sqs_action)
    if (self.create_missing_queues and 
        sqs_response.Error[0].Code ==  'AWS.SimpleQueueService.NonExistentQueue'):
      self.log.info('Creating missing queue %s', queue_name)
      self.create_queue(queue_name, 30)
    else:
      for error in sqs_response.Error:
        self.log.error('Q:%s -- %s\n%s', queue_name, error.Code, error.Message)
      if sqs_action == 'ReceiveMessage':
        self.runLoop.currentRunLoop().waitBeforeCalling(0, self.poll, queue_name)
          
  def create_queue(self, queue_name, default_visibility_timeout=None):
    params = self.build_create_queue(queue_name, 
      DefaultVisibilityTimeout=default_visibility_timeout)
    url = "%s?%s" %  (self.sqs_url_prefix,  urllib.urlencode(params))
    connection = self.URLConnection.connectionWithRequest(url, self)
    connection.userInfo['queue_name'] = queue_name
    connection.userInfo['parser'] = self.sqs_schema.newParser()

              
  def delete_message(self, queue_name, message):
    # TODO: check outstanding when we go to delete, If the message is not there
    # either delete was called twice for the same message ..or... more likely
    # we took to long to process it
    self.collectProcTime(queue_name, message)

    params = self.build_delete_message(message)

    url = "%s/%s?%s" %  (self.sqs_url_prefix, queue_name, urllib.urlencode(params))
    
    connection = self.URLConnection.connectionWithRequest(url, self)
    connection.userInfo['queue_name'] = queue_name
    connection.userInfo['parser'] = self.sqs_schema.newParser()
    connection.userInfo['message'] = message
    self.other_counts.count('delete_message')
    
    
  def sign_request(self, params):
    '''Adds the key Signature to the passed in params Dictionary. The value of which is
    a properly computed AWS Authentication Signature
     '''
    sig = hmac.new(self.aws_secret_key, digestmod=sha)
    
    keys = params.keys()
    keys.sort(key=str.lower)
    
    for key in keys:
      sig.update(key)
      value = str(params[key])
      sig.update(value)

    params['Signature'] = base64.encodestring(sig.digest()).strip()
          
  def send_message(self, queue_name, message_body, callback=None):
    """Sends the specifierd queue name the given message. If callback is specified
    it will be invoked when sending is complete. You do not need to be monitoring
    a queue in order to send a message to it...
    
    """
    
    params = self.build_send_message(message_body)
    
    url = "%s/%s?%s" %  (self.sqs_url_prefix, queue_name, urllib.urlencode(params))
    
    connection = self.URLConnection.connectionWithRequest(url, self)
    connection.userInfo['queue_name'] = queue_name
    connection.userInfo['parser'] = self.sqs_schema.newParser()
    connection.userInfo['message_body'] = message_body
    connection.userInfo['callback'] = callback
    connection.userInfo['queue_time'] = time.time()
    self.other_counts.count('sent_message_%s' % queue_name)
  
  def build_request(self, action, **kw):
    """Given an action name returns a dictionary with the appropriate values for SQS
    including a properly calculated signature.
    
    """
    params = {'AWSAccessKeyId': self.aws_access_key,
      'Action': action,
      'SignatureVersion': '1',
      'Version': '2008-01-01',
      'Timestamp': datetime.utcnow().isoformat()
    }
    
    for k,v in kw.items():
      if v is not None:
        params[k] = v
    
    self.sign_request(params)
    return params
    
  def build_delete_message(self, message):
    return self.build_request('DeleteMessage',
       ReceiptHandle = message.ReceiptHandle
    )
    
  def build_receive_message(self, MaxNumberOfMessages=10, VisibilityTimeout=None):
    return self.build_request('ReceiveMessage', 
      MaxNumberOfMessages=MaxNumberOfMessages, 
      VisibilityTimeout=VisibilityTimeout)
    
  def build_send_message(self, message_body):
    return self.build_request('SendMessage',
      MessageBody = message_body)
  
  def build_create_queue(self, QueueName, DefaultVisibilityTimeout=None):
    return self.build_request('CreateQueue', 
      QueueName=QueueName, 
      DefaultVisibilityTimeout=DefaultVisibilityTimeout)
