
try:
    from collections import ChainMap
except ImportError: # Py < 3
    from chainmap import ChainMap

class Context(ChainMap):
    pass

