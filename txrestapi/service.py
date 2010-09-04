import re
from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.web.error import NoResource


class APIResource(Resource):

    _registry = None

    def __init__(self, *args, **kwargs):
        Resource.__init__(self, *args, **kwargs)
        self._registry = {}

    def _get_callback(self, request):
        for r, cb in self._registry.get(request.method, ()):
            result = r.search(request.path)
            if result:
                return cb, result.groupdict()
        return None, None

    def register(self, method, regex, callback):
        l = self._registry.setdefault(method, [])
        l.append((re.compile(regex), callback))

    def getChild(self, name, request):
        r = Resource.getChild(self, name, request)
        if isinstance(r, NoResource):
            # Go into the thing
            callback, args = self._get_callback(request)
            if callback is None:
                return r
            else:
                return callback(request, **args)
        else:
            return r


class RESTfulService(Site):
    def __init__(self, port=8080):
        self.root = APIResource()
