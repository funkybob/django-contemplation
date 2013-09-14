
try:
    from collections import ChainMap
except ImportError: # Py < 3
    from chainmap import ChainMap

BUILTINS = {'True': True, 'False': False, 'None': None}

class ContextDict(dict):
    def __init__(self, context, *args, **kwargs):
        super(ContextDict, self).__init__(*args, **kwargs)
        context.maps.insert(0, self)
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.context.pop()

class Context(ChainMap):
    def __init__(self, default=None):
        super(Context, self).__init__(dict(BUILTINS), default or {})

    def push(self, *args, **kwargs):
        return ContextDict(self, *args, **kwargs)

    def pop(self):
        if len(self.maps) < 2:
            raise IndexError
        return self.maps.pop(0)

