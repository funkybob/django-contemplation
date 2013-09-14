
'''
Simple template engine inspired by Django.

Major differences:
- allows line breaks in tags
- unified tag syntax

TODO:
- filters as chains of partials
- tags marked with takes_context, is_block, etc...
'''
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


class VariableDoesNotExist(Exception):
    pass

# From django's smart_split
split_re = re.compile(r"""
    ((?:
        [^\s'"]*
        (?:
            (?:"(?:[^"\\]|\\.)*" | '(?:[^'\\]|\\.)*')
            [^\s'"]*
        )+
    ) | \S+)
""", re.VERBOSE)
def smart_split(string):
    return split_re.finditer(string)

class Template(object):
    def __init__(self, source):
        self.source = source
        self.root = parse(self)

    def render(self, context):
        return ''.join(
            node.render(context)
            for node in self.root.nodelist
        )

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

class Node(object):
    def __init__(self, tmpl):
        self.tmpl = tmpl

class BlockNode(Node):
    def __init__(self, *args, **kwargs):
        super(BlockNode, self).__init__(*args, **kwargs)
        self.nodelist = []

    def render(self, context):
        return ''.join([
            node.render(context)
            for node in self.nodelise
        ])

class RootNode(BlockNode):
    '''A special block node to be the root of the template.'''
    pass

class VarNode(Node):
    def __init__(self, tmpl, token):
        # XXX Expression
        self.token = Variable(token)
        super(VarNode, self).__init__(tmpl)

    def render(self, context):
        return unicode(self.token.resolve(context))

class TextNode(Node):
    def __init__(self, tmpl, content):
        super(TextNode, self).__init__(tmpl)
        self.content = content

    def render(self, context):
        return self.content

var_re = re.compile(r'''
    ^
    (?P<int>\d+)|
    (?P<float>\d+\.\d+)|
    (?P<var>[\w\.]+)|
    (?P<string>"[^"\\]*(?:\\.[^"\\]*)*"|'[^'\\]*(?:\\.[^'\\]*)*')
    $
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
        num, fnum, var, string = match.groups()
        if num is not None:
            self.literal = num
        elif fnum is not None:
            self.literal = fnum
        elif string:
            self.literal = string[1:-1]
        elif var:
            self.variable = var

    def resolve(self, context):
        if self.literal is not None:
            return self.literal
        # dotted lookup
        bits = self.variable.split('.')
        current = context
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
                current = current()
        return current

class FilterExpression(object):
    '''
    Parse a filter expression in either a VarNode or a BlockNode's tokens.
    '''
    def __init__(self, token):
        pass

class Parser(object):
    '''Django-style recursive, stateful Parser'''
    def __init__(self, tmpl):
        self.tmpl = tmpl
        self.stream = tokenise(tmpl.source)
        self.buffer = []

    def next(self):
        try:
            return self.buffer.pop()
        except IndexError:
            return self.stream.next()

    def push(self, token):
        '''Push a token back into the stream'''
        self.buffer.append(token)

    def parse(self, parse_until=None):
        nodelist = []
        if parse_until is None:
            parse_until = []

        for mode, tok in self:
            if mode == TOKEN_TEXT:
                nodelist.append(TextNode(self.tmpl, tok))

            elif mode == TOKEN_VAR:
                nodelist.append(VarNode(self.tmpl, tok))

            elif mode == TOKEN_BLOCK:
                tag_name = tok.split()[0]

                if tag_name in parse_until:
                    self.push((mode, tok))
                    return nodelist

                # XXX We could insert a check here for Django-style tags?

                # XXX Parse args/kwargs
                tag_class = TAGS[tag_name]
                tag = tag_class(self.tmpl, *args, **kwargs)
                if tag.is_block:
                    tag.nodelist = self.parse([tag.close_tag])
            # last case is comment, which we ignore

        if parse_until:
            raise ValueError('Unbalanced tags: %r' % parse_until)
        return nodelist

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
        try:
            val = val.resolve({})
        except VariableDoesNotExist:
            pass
        kwargs[key] = val
        del bits[:1]

    return args, kwargs, varname

def parse(tmpl):
    stream = tokenise(tmpl.source)
    stack = [
        RootNode(tmpl),
    ]

    for mode, tok in stream:
        if mode == TOKEN_TEXT:
            stack[-1].nodelist.append(TextNode(tmpl, tok))

        elif mode == TOKEN_VAR:
            stack[-1].nodelist.append(VarNode(tmpl, tok))

        elif mode == TOKEN_BLOCK:
            bits = smart_split(tok)
            tag_name = bits.pop(0)
            # Does this match the close tag name of the current Top of Stack?
            if tag_name == stack[-1].close_tag:
                stack.pop()
                continue
            tag_class = TAGS[tag_name]
            if tag_class.raw_token:
                tag = tag_class(tmpl, tok)
            else:
                # Parse bits for args, kwargs
                args, kwargs, varname = parse_bits(bits)
                tag = tag_class(tmpl, *args, **kwargs)
            if tag_class.is_block:
                stack.append(tag)

    assert len(stack) == 1, "Unbalanced block nodes: %r" % stack
    return stack[0]
