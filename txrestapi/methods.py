from functools import wraps
from twisted.web.resource import Resource
from zope.interface.advice import addClassAdvisor

class _FakeResource(Resource):
    _result = ''
    isLeaf = True
    def __init__(self, result):
        Resource.__init__(self)
        self._result = result
    def render(self, request):
        return self._result


def maybeResource(f):
    @wraps(f)
    def inner(*args, **kwargs):
        result = f(*args, **kwargs)
        if not isinstance(result, Resource):
            result = _FakeResource(result)
        return result
    return inner


def method_factory_factory(method):
    def factory(regex):
        _f = {}
        def decorator(f):
            _f[f.__name__] = f
            return f
        def advisor(cls):
            def wrapped(f):
                def __init__(self, *args, **kwargs):
                    f(self, *args, **kwargs)
                    for func_name in _f:
                        orig = _f[func_name]
                        func = getattr(self, func_name)
                    if func.im_func==orig:
                        self.register(method, regex, maybeResource(func))
                return __init__
            cls.__init__ = wrapped(cls.__init__)
            return cls
        addClassAdvisor(advisor)
        return decorator
    return factory

ALL    = method_factory_factory('ALL')
GET    = method_factory_factory('GET')
POST   = method_factory_factory('POST')
PUT    = method_factory_factory('PUT')
DELETE = method_factory_factory('DELETE')
