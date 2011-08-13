import unittest

from rambler.net import webserver
from rambler.net.webserver import routing

class TestRouting(unittest.TestCase):
  def test_segments(self):
    segments = routing.connect('/', controller='api', action='foo').segments
    self.assertEqual(type(segments[0]), webserver.DividerSegment)
    self.assertEqual(len(segments),1)
    
    segments = routing.connect('/:controller/:action').segments
    self.assertEqual(type(segments[0]), webserver.DividerSegment)
    self.assertEqual(type(segments[1]), webserver.ControllerSegment)
    self.assertEqual(type(segments[2]), webserver.DividerSegment)
    self.assertTrue(type(segments[3]), webserver.DynamicSegment)

    self.assertEqual(len(segments),4)
    
  def test_regexp(self):
    route = routing.connect('/', controller='api', action='foo')
    
    #self.assertEqual(route.regexp.pattern, r'\A\/?\Z')
    
    self.assertTrue(route.match('/'))
    self.assertTrue(route.match(''))
    self.assertFalse(route.match('/foo'))
    
    route = routing.connect('/:controller/:action')
    print route.regexp.pattern
    self.assertFalse(route.match('/'))
    self.assertTrue(route.match('/blah/foo'))
    
    
    
    
    
if __name__=="__main__":
  unittest.main()