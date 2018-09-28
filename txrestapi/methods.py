from six import PY2, b
from zope.interface.advice import addClassAdvisor

def method_factory_factory(method):
    def factory_py2(regex):
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
                        self.register(method, regex, func)
                return __init__
            cls.__init__ = wrapped(cls.__init__)
            return cls
        addClassAdvisor(advisor)
        return decorator

    def factory_py3(regex):

        def decorator(f):
            current_methods = getattr(f, '__txrestapi__', [])
            current_methods.append((method, regex, ))
            f.__txrestapi__ = current_methods
            return f

        return decorator

    factory = factory_py2 if PY2 else factory_py3
    return factory

ALL    = method_factory_factory(b('ALL'))
GET    = method_factory_factory(b('GET'))
POST   = method_factory_factory(b('POST'))
PUT    = method_factory_factory(b('PUT'))
DELETE = method_factory_factory(b('DELETE'))
