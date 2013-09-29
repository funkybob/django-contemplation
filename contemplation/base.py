
'''
Simple template engine inspired by Django.

Major differences:
- allows line breaks in tags
- unified tag syntax

TODO:
- filters as chains of partials
'''

from .utils import smart_split, unescape_string_literal

import ast
import re

tag_re = re.compile(r'{%\s*(?P<tag>.+?)\s*%}|{{\s*(?P<var>.+?)\s*}}|{#\s*(?P<comment>.+?)\s*#}')

TOKEN_TEXT = 0
TOKEN_VAR = 1
TOKEN_BLOCK = 2
TOKEN_COMMENT = 3
TOKEN_MAPPING = {
    TOKEN_TEXT: 'Text',
    TOKEN_VAR: 'Var',
    TOKEN_BLOCK: 'Block',
    TOKEN_COMMENT: 'Comment',
}

TAGS = {}
FILTERS = {}

class TemplateSyntaxError(Exception):
    pass

class VariableDoesNotExist(Exception):
    pass

class Template(object):
    def __init__(self, source):
        self.source = source
        self.root = parse(self)

    def render(self, context):
        return self.root.nodelist.render(context)


def tokenise(template):
    '''A generator which yields (type, content) pairs'''
    upto = 0
    for m in tag_re.finditer(template):
        start, end = m.span()
        if upto < start:
            yield (TOKEN_TEXT, template[upto:start])
        upto = end
        tag, var, comment = m.groups()
        if tag is not None:
            yield (TOKEN_BLOCK, tag)
            # If it was a verbatim tag, scan to the end and yield as a Text node
            if tag[:9] in ('verbatim', 'verbatim '):
                marker = 'end%s' % tag
                while 1:
                    m = stream.next()
                    if m.group('tag') == marker:
                        break
                yield (TOKEN_TEXT, template[upto:m.start()])
                yield (TOKEN_BLOCK, m.group('tag'))
                upto = m.end()
            # XXX Handle verbatim tag and translations
        elif var is not None:
            yield (TOKEN_VAR, var)
        else:
            yield (TOKEN_COMMENT, comment)
    if upto < len(template):
        yield (TOKEN_TEXT, template[upto:])

class Nodelist(list):
    '''A list that can render as a node.'''
    def render(self, context):
        return ''.join(
            node.render(context)
            for node in self
        )

class Node(object):
    close_tag = None
    raw_token = False
    def __init__(self):
        self.nodelist = Nodelist()

class VarNode(Node):
    def __init__(self, token):
        # XXX Expression
        super(VarNode, self).__init__()
        self.token = Variable(token)

    def render(self, context):
        try:
            value = self.token.resolve(context)
        except VariableDoesNotExist:
            value = context.invalid
        return unicode(value)

class TextNode(Node):
    def __init__(self, content):
        super(TextNode, self).__init__()
        self.content = content

    def render(self, context):
        return self.content

var_re = re.compile(r'''
    ^(?:
    (?P<int>\d+)|
    (?P<float>\d+\.\d+)|
    (?P<var>\w+(?:\.\w+)*)|
    (?P<string>"[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')
    )$
''', re.VERBOSE)
class Variable(object):
    '''
    Wrapper to hold a variable from parsing, awaiting resolution at
    render time.
    '''
    def __init__(self, raw):
        self.raw = raw
        self.literal = None
        self.variable = None

        match = var_re.match(raw)
        if not match:
            raise TemplateSyntaxError('Could not parse variable: %r' % raw)
        # XXX Need to ensure we parsed it _all_
        if match.end() != len(raw):
            raise TemplateSyntaxError('Could not parse variable: %r' % raw)
        num, fnum, var, string = match.groups()
        if num is not None:
            self.literal = num
        elif fnum is not None:
            self.literal = fnum
        elif string:
            self.literal = unescape_string_literal(string)
        elif var:
            self.variable = var

    def resolve(self, context):
        if self.literal is not None:
            return self.literal
        # dotted lookup
        bits = self.variable.split('.')
        current = context
        try: # catch for silent failure
            for bit in bits:
                try: # dict lookup
                    current = current[bit]
                except (TypeError, AttributeError, KeyError, ValueError):
                    try: # attr lookup
                        # Add check for base level
                        current = getattr(current, bit)
                    except (TypeError, AttributeError):
                        try: # list lookup
                            current = current[int(bit)]
                        except (IndexError, ValueError, KeyError, TypeError):
                            raise VariableDoesNotExist(
                                "Failed lookup for [%r] in %r" % (bit, current)
                            )
                if callable(current):
                    try:
                        current = current()
                    except TypeError:
                        return context.invalid
        except Exception as e:
            if getattr(e, 'silent_variable_failure', False):
                current = context.invalid
            else:
                raise
        return current


class FilterExpression(object):
    '''
    Parse a variable followed by an optional list of filters and their
    arguments.
    '''
    def __init__(self, token):
        self.token = token
        self.variable = None
        self.constant = None
        self.filters = None

        code = ast.parse(token, mode='eval')

        if isinstance(code.body, ast.Name):
            self.variable = code.body.id
        elif isinstance(code.body, ast.Str):
            self.constant = code.body.s
        elif isinstance(code.body, ast.Num):
            self.constant = code.body.n
        elif isinstance(code.body, ast.BinOp) and isinstance(code.body.op, ast.BitOr):
            self.filters = self._resolve_binops(code.body)

    def _resolve_binops(self, node):
        '''
        Translate Python AST into what we want it to mean.
        - BinOp(BitOr) become calls

        Expression(body=BinOp(
            left=BinOp(
                left=BinOp(
                    left=Name(id='a', ctx=Load()),
                    op=BitOr(),
                    right=Name(id='b', ctx=Load())
                ),
                op=BitOr(),
                right=Name(id='c', ctx=Load())
            ),
            op=BitOr(),
            right=Name(id='d', ctx=Load())
        ))

        Would become:
        Expression(body=Call(
            func=Name(id='d', ctx=Load()), args=[
                Call(func=Name(id='c', ctx=Load()), args=[
                    Call(func=Name(id='b', ctx=Load()), args=[
                        Name(id='a', ctx=Load()),
                    ], keywords=[], starargs=None, kwargs=None),
                ], keywords=[], starargs=None, kwargs=None),
            ], keywords=[], starargs=None, kwargs=None)
        )
        '''
        # right is always "simple"
        # left could be compound OR
        if isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.BitOr):
            filters.append(self._resolve_binops(node.left))
        else:
            pass

kwarg_re = re.compile(r"(?:(\w+)=)?(.+)")

def parse_bits(bits):
    '''
    Take a list of smart-split values, and convert to a list of args and kwargs.
    Returns (args, kwargs, varname) where varname is the "as foo" name, or None.
    '''
    if len(bits) > 2 and bits[-2] == 'as':
        varname = bits[-1]
        del bits[-2:]
    else:
        varname = None
    args = []
    while bits:
        m = kwarg_re.match(bits[0])
        # If there was a foo= part, end args parsing
        if m.group(1):
            break
        val = Variable(m.group(2))
        # See if it's a constant we can resolve now
        try:
            val = val.resolve({})
        except VariableDoesNotExist:
            pass
        args.append(val)
        del bits[:1]

    kwargs = {}
    while bits:
        m = kwarg_re.match(bits[0])
        if not m.group(1):
            raise TemplateSyntaxError("Found positional arguments after keyword arguments!")
        key, val = m.groups()
        if key in kwargs:
            raise TemplateSyntaxError("Duplicate keyword values passed: %s" % key)
        val = Variable(val)
        #try:
        #    val = val.resolve({})
        #except VariableDoesNotExist:
        #    pass
        kwargs[key] = val
        del bits[:1]

    return args, kwargs, varname

def parse(tmpl):
    stream = tokenise(tmpl.source)
    stack = [
        Node()
    ]

    for mode, tok in stream:
        if mode == TOKEN_TEXT:
            stack[-1].nodelist.append(TextNode(tok))

        elif mode == TOKEN_VAR:
            stack[-1].nodelist.append(VarNode(tok))

        elif mode == TOKEN_BLOCK:
            bits = smart_split(tok)
            tag_name = bits.pop(0)
            # Does this match the close tag name of the current Top of Stack?
            if tag_name == stack[-1].close_tag:
                stack.pop()
                continue
            tag_class = TAGS[tag_name]
            if tag_class.raw_token:
                tag = tag_class(tok)
            else:
                # Parse bits for args, kwargs
                args, kwargs, varname = parse_bits(bits)
                tag = tag_class(*args, **kwargs)
            stack[-1].nodelist.append(tag)
            if tag_class.close_tag:
                stack.append(tag)

    assert len(stack) == 1, "Unbalanced block nodes: %r" % stack
    return stack[0]

class Registry(object):
    def tag(self, name, tag_class=None):
        def _register_tag(tag_class):
            TAGS[name] = tag_class
            return tag_class
        if tag_class is None:
            return _register_tag
        else:
            return _registre_tag(tag_class)

    def filter(self, name, filter_func):
        FILTERS[name] = filter_func

register = Registry()

from . import defaulttags
#from . import defaultfilters
