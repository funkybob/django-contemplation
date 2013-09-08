
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

class Token(object):
    def __init__(self, content):
        self.content = content

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
        self.nodelist = parse(self)


def tokenise(template):
    '''A generator which yields (type, content) pairs'''
    upto = 0
    for m in tag_re.finditer(template):
        start, end = m.span()
        if last < start:
            yield (TOKEN_TEXT, template[last:start])
        last = end
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
                yield (TOKEN_TEXT, template[last:m.start()])
                yield (TOKEN_BLOCK, m.group('tag'))
                last = m.end()
            # XXX Handle verbatim tag and translations
        elif var is not None:
            yield (TOKEN_VAR, var)
        else:
            yield Comment(comment)
    if last < len(template):
        yield (TOKEN_TEXT, template[last:])

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

class TextNode(Node):
    def __init__(self, tmpl, content):
        super(TextNode, self).__init__(tmpl)
        self.content = content

    def render(self, context):
        return self.content


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

        if parse_until:
            raise ValueError('Unbalanced tags: %r' % parse_until)
        return nodelist

def parse(tmpl):
    stream = tokenise(tmpl.source)
    stack = [
        RootNode(),
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
            # Parse bits for kwargs
            tag_class = TAGS[tag_name]
            tag = tag_class(tmpl, *args, **kwargs)
            if tag_class.is_block:
                stack.append(tag)

    assert len(stack) == 1, "Unbalanced block nodes: %r" % stack
    return stack[0]
