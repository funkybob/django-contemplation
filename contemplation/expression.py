'''
Expression parsing.

    literal_or_name : (NUMBER | STRING | NAME)
    key : (NUMBER | NAME)
    lookup : literal_or_name[.key]*
    filter : NAME[:lookup]
    filter_chain: [|filter]+
    lookup : literal_or_name[filter_chain]?
'''

from io import StringIO
import tokenize


class ExprNode(object):
    '''Common code for Expression/FilterExpr'''
    def resolve(self, key, context):
        '''
        Resolve a supplied value.
        '''
        if isinstance(key, ExprNode):
            return key(context)
        if key.exact_type == tokenize.NUMBER:
            try:
                return int(key.string)
            except ValueError:
                return float(key.string)
        if key.exact_type == tokenize.NAME:
            return context[key.string]
        else:
            # String
            return key.string[1:-1]

class Lookup(ExprNode):
    '''
    Affects a dotted lookup
    '''
    def __init__(self, steps):
        self.steps = steps

    def __call__(self, context):
        steps = iter(self.steps)
        current = self.resolve(next(steps), context)
        current = context[current]
        for bit in steps:
            bit = self.resolve(bit, context)
            try:
                current = current[bit]
            except KeyError:
                try:
                    current = getattr(current, bit)
                except (AttributeError, TypeError):
                    try:
                        current = current[int(bit)]
                    except (IndexError, ValueError, KeyError, TypeError):
                        raise ValueError("Can't get %r from %r" % (bit, current))
            if callable(current):
                try:
                    current = current()
                except TypeError:
                    return context.invalid
        return current

class Filter(ExprNode):
    '''
    Applies a filter, with optional argument
    '''
    def __init__(self, root, filter_name, arg):
        self.root = root
        self.filter = filter_name
        self.arg = arg

    def __call__(self, context):
        # Retrieve the filter function
        filter_func = lambda x, y: x
        root = self.resolve(self.root, context)
        # Resolve the arg, if we have one
        args = []
        if self.arg is not None:
            args.append(self.resolve(self.arg, context))
        # Yield the value...
        return filter_func(root, *args)

class Expression(ExprNode):
    '''
    Combination of a Lookup and 0 or more Filters
    '''
    def __init__(self, root, filters):
        self.root = root
        self.filters = filters or []

    def __call__(self, context):
        root = self.resolve(self.root, context)
        for filt in self.filters:
            root = filt(root, context)
        return root


class FilterExpression(object):
    '''
    Parse a variable followed by an optional list of filters and their
    arguments.
    '''
    def __init__(self, token):

        io = StringIO(token)
        self.tokens = tokenize.generate_tokens(io.readline)
        self._queue = []

        root, tok = self.parse_lookup()

        if tok.exact_type == tokenize.ENDMARKER:
            self.root = root
            return

        if tok.exact_type != tokenize.VBAR:
            raise SyntaxError('Invalid syntax: %r' % (tok.string,))

        while tok.exact_type == tokenize.VBAR:
            root, tok = self.parse_filter(root)
            if tok.exact_type not in (tokenize.VBAR, tokenize.ENDMARKER):
                raise SyntaxError('Unexpected token: %r' % (tok.string,))

        self.root = root

    def __call__(self, context):
        return self.root(context)

    def next(self):
        try:
            tok = self._queue.pop()
        except IndexError:
            tok = next(self.tokens)
            # foo.1 will be split into NAME(foo), NUMBER(.1)
            # We need to re-work this to yield NAME(foo), OP(.), NUMBER(1)
            if tok.exact_type == tokenize.NUMBER and tok.string.startswith('.'):
                # Split into two tokens
                self._queue.append(
                    tokenize.TokenInfo(
                        type=tokenize.NUMBER,
                        string=tok.string,
                        start=tok.start,
                        end=tok.end,
                        line=tok.line,
                    )
                )
                tok = tokenize.TokenInfo(
                    type=tokenize.DOT,
                    string='.',
                    start=tok.start,
                    end=tok.end,
                    line=tok.line,
                )
                return tok
        return tok

    def parse_lookup(self):
        '''
        LOOKUP:  literal_or_key[.key]+
        '''
        steps = []
        tok = self.next()
        if not tok.exact_type in [tokenize.STRING, tokenize.NAME, tokenize.NUMBER]:
            raise SyntaxError('Expression lookups must start with name or literal [%r]' % tok.string)

        steps.append(tok)
        tok = self.next()
        while tok.exact_type == tokenize.DOT:
            tok = self.next()
            if tok.exact_type not in (tokenize.NAME, tokenize.NUMBER):
                break
            steps.append(tok)
            tok = self.next()

        return Lookup(steps), tok

    def parse_filter(self, root):
        '''
        '''
        filter_name = self.next()
        if filter_name.exact_type != tokenize.NAME:
            raise SyntaxError('Invalid filter syntax: %r' % (tok.string,))

        tok = self.next()
        if tok.exact_type == tokenize.COLON:
            arg, tok = self.parse_lookup()
        else:
            arg = None
        return Filter(filter_name.string, root, arg), tok
