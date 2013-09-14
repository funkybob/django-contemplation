
try:
    from collections import ChainMap
except ImportError: # Py < 3
    from chainmap import ChainMap

BUILTINS = {'True': True, 'False': False, 'None': None}

class Context(ChainMap):
    def __init__(self, default=None):
        super(Context, self).__init__(dict(BUILTINS), default or {})

