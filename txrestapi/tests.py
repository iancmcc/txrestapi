import txrestapi
__package__="txrestapi"
import re
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.resource import Resource
from twisted.web.server import Request, Site
from twisted.web.client import getPage
from twisted.web.error import NoResource
from twisted.trial import unittest
from .resource import APIResource
from .methods import GET, PUT

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

    def test_method_matching(self):
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

    def test_no_resource(self):
        r = APIResource()
        r.register('GET', '^/(?P<a>[^/]*)/a/(?P<b>[^/]*)$', None)
        req = Request(FakeChannel(), None)
        req.method = 'GET'
        req.path = '/definitely/not/a/match'
        result = r.getChild('regex', req)
        self.assert_(isinstance(result, NoResource))


class TestResource(Resource):
    isLeaf = True
    def render(self, request):
        return 'aresource'


class TestAPI(APIResource):

    @GET('^/(?P<a>test[^/]*)/?')
    def on_test_get(self, request, a):
        return 'GET %s' % a

    @PUT('^/(?P<a>test[^/]*)/?')
    def on_test_put(self, request, a):
        return 'PUT %s' % a

    @GET('^/gettest')
    def on_gettest(self, request):
        return TestResource()


class DecoratorsTest(unittest.TestCase):
    def _listen(self, site):
        return reactor.listenTCP(0, site, interface="127.0.0.1")

    def setUp(self):
        r = TestAPI()
        site = Site(r, timeout=None)
        self.port = self._listen(site)
        self.portno = self.port.getHost().port

    def tearDown(self):
        return self.port.stopListening()

    def getURL(self, path):
        return "http://127.0.0.1:%d/%s" % (self.portno, path)

    @inlineCallbacks
    def test_get(self):
        url = self.getURL('test_thing/')
        result = yield getPage(url, method='GET')
        self.assertEqual(result, 'GET test_thing')

    @inlineCallbacks
    def test_put(self):
        url = self.getURL('test_thing/')
        result = yield getPage(url, method='PUT')
        self.assertEqual(result, 'PUT test_thing')

    @inlineCallbacks
    def test_resource_wrapper(self):
        url = self.getURL('gettest')
        result = yield getPage(url, method='GET')
        self.assertEqual(result, 'aresource')

