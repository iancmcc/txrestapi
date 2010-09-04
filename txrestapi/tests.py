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
        req = Request(FakeChannel(), None)
        a_ = r.getChild('a', req)
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

    def test_longerpath(self):
        marker = object()
        r = APIResource()
        def cb(request):
            return marker
        r.register('GET', '/regex/a/b/c', cb)
        req = Request(FakeChannel(), None)
        req.method = 'GET'
        req.path = '/regex/a/b/c'
        result = r.getChild('regex', req)
        self.assertEqual(result, marker)

    def test_args(self):
        r = APIResource()
        def cb(request, **kwargs):
            return kwargs
        r.register('GET', '/(?P<a>[^/]*)/a/(?P<b>[^/]*)/c', cb)
        req = Request(FakeChannel(), None)
        req.method = 'GET'
        req.path = '/regex/a/b/c'
        result = r.getChild('regex', req)
        self.assertEqual(sorted(result.keys()), ['a', 'b'])

    def test_order(self):
        r = APIResource()
        def cb1(request, **kwargs):
            kwargs.update({'cb1':True})
            return kwargs
        def cb(request, **kwargs):
            return kwargs
        # Register two regexes that will match
        r.register('GET', '/(?P<a>[^/]*)/a/(?P<b>[^/]*)/c', cb1)
        r.register('GET', '/(?P<a>[^/]*)/a/(?P<b>[^/]*)', cb)
        req = Request(FakeChannel(), None)
        req.method = 'GET'
        req.path = '/regex/a/b/c'
        result = r.getChild('regex', req)
        # Make sure the first one got it
        self.assert_('cb1' in result)

