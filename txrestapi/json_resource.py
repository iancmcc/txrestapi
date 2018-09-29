import re
import json
import time
import six

from six import PY2

from functools import wraps

from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET
from twisted.internet.defer import Deferred
from twisted.python import log as twlog


def _to_json(output_object):
    return (json.dumps(
        output_object,
        indent=2,
        separators=(',', ': '),
        sort_keys=True,
    ) + '\n').encode()


class _JsonResource(Resource):
    _result = ''
    isLeaf = True

    def __init__(self, result, executed):
        Resource.__init__(self)
        self._result = result
        self._executed = executed

    def _setHeaders(self, request):
        """
        Those headers will allow you to call API methods from web browsers, they require CORS:
            https://en.wikipedia.org/wiki/Cross-origin_resource_sharing
        """
        request.responseHeaders.addRawHeader(b'content-type', b'application/json')
        request.responseHeaders.addRawHeader(b'Access-Control-Allow-Origin', b'*')
        request.responseHeaders.addRawHeader(b'Access-Control-Allow-Methods', b'GET, POST, PUT, DELETE')
        request.responseHeaders.addRawHeader(b'Access-Control-Allow-Headers', b'x-prototype-version,x-requested-with')
        request.responseHeaders.addRawHeader(b'Access-Control-Max-Age', 2520)
        return request

    def render(self, request):
        self._setHeaders(request)
        # this will just add one extra field to the response to populate how fast that API call was processed
        self._result['execution'] = '%3.6f' % (time.time() - self._executed)
        return _to_json(self._result)


class _DelayedJsonResource(_JsonResource):
    """
    If your API method returned `Deferred` object instead of final result
    we can wait for the result and then return it in API response.
    """

    def _cb(self, result, request):
        self._setHeaders(request)
        result['execution'] = '%3.6f' % (time.time() - self._executed)
        raw = _to_json(result)
        if request.channel:
            request.write(raw)
            request.finish()
        else:
            twlog.err('REST API connection channel already closed')

    def _eb(self, err, request):
        self._setHeaders(request)
        execution = '%3.6f' % (time.time() - self._executed)
        raw = _to_json(dict(status='ERROR', execution=execution, errors=[str(err), ]))
        if request.channel:
            request.write(raw)
            request.finish()
        else:
            twlog.err('REST API connection channel already closed')

    def render(self, request):
        self._result.addCallback(self._cb, request)
        self._result.addErrback(self._eb, request)
        return NOT_DONE_YET


def maybeResource(f):
    @wraps(f)
    def inner(*args, **kwargs):
        _executed = time.time()
        try:
            result = f(*args, **kwargs)

        except Exception as exc:
            return _JsonResource(dict(status='ERROR', errors=[str(exc), ]), _executed)

        if isinstance(result, Deferred):
            return _DelayedJsonResource(result, _executed)

        if not isinstance(result, Resource):
            result = _JsonResource(result, _executed)

        return result
    return inner


class JsonAPIResource(Resource):

    _registry = None

    def __new__(cls, *args, **kwds):
        instance = super().__new__(cls, *args, **kwds)
        instance._registry = []
        for name in dir(instance):
            attribute = getattr(instance, name)
            annotations = getattr(attribute, "__txrestapi__", [])
            for annotation in annotations:
                method, regex = annotation
                instance.register(method, regex, attribute)
        return instance

    def __init__(self, *args, **kwargs):
        Resource.__init__(self, *args, **kwargs)
        if PY2:
            self._registry = []

    def _get_callback(self, request):
        request_method = request.method
        path_to_check = getattr(request, '_remaining_path', request.path)
        if not isinstance(path_to_check, six.text_type):
            path_to_check = path_to_check.decode()
        for m, r, cb in self._registry:
            if m == request_method or m == b'ALL':
                result = r.search(path_to_check)
                if result:
                    request._remaining_path = path_to_check[result.span()[1]:]
                    return cb, result.groupdict()
        return None, None

    def register(self, method, regex, callback):
        if not isinstance(regex, six.text_type):
            regex = regex.decode()
        self._registry.append((method, re.compile(regex), callback))

    def unregister(self, method=None, regex=None, callback=None):
        if regex is not None:
            if not isinstance(regex, six.text_type):
                regex = regex.decode()
            regex = re.compile(regex)
        for m, r, cb in self._registry[:]:
            if not method or (method and m == method):
                if not regex or (regex and r == regex):
                    if not callback or (callback and cb == callback):
                        self._registry.remove((m, r, cb))

    def getChild(self, name, request):
        r = self.children.get(name, None)
        if r is None:
            # Go into the thing
            callback, args = self._get_callback(request)
            if callback is None:
                return _JsonResource(dict(status='ERROR', errors=['path %r not found' % name, ]), time.time())
            else:
                return maybeResource(callback)(request, **args)
        else:
            return r
