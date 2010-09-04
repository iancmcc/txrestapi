import re
from twisted.internet.defer import inlineCallbacks
from twisted.web.server import Request
from twisted.trial import unittest
from .service import APIResource, Resource

class FakeChannel(object):
    transport = None

class APIResourceTest(unittest.TestCase):

    def test_returns_normal_resources(self):
        r = APIResource()
        a = Resource()
        r.putChild('a', a)
        a_ = r.getChild('a', None)
        self.assertEqual(a, a_)

    def test_registry(self):
        compiled = re.compile('regex')
        r = APIResource()
        r.register('GET', 'regex', None)
        self.assertEqual(r._registry.keys(), ['GET'])
        self.assertEqual(r._registry['GET'], [(compiled, None)])

    def test_regex_matching(self):
        r = APIResource()
        r.register('GET', 'regex', 1)
        r.register('PUT', 'regex', 2)
        r.register('GET', 'another', 3)
        req = Request(FakeChannel(), None)
        req.method = 'GET'
        req.path = 'regex'
        result = r._get_callback(req)
        self.assert_(result)
        self.assertEqual(result[0], 1)
        req.method = 'PUT'
        req.path = 'regex'
        result = r._get_callback(req)
        self.assert_(result)
        self.assertEqual(result[0], 2)
        req.method = 'GET'
        req.path = 'another'
        result = r._get_callback(req)
        self.assert_(result)
        self.assertEqual(result[0], 3)
        req.method = 'PUT'
        req.path = 'another'
        result = r._get_callback(req)
        self.assertEqual(result, (None, None))

    def test_callback(self):
        marker = object()
        def cb(request):
            return marker
        r = APIResource()
        r.register('GET', 'regex', cb)
        req = Request(FakeChannel(), None)
        req.method = 'GET'
        req.path = 'regex'
        result = r.getChild('regex', req)
        self.assertEqual(result, marker)
