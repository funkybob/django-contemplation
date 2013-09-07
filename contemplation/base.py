
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


def parse(tmpl):
    tmpl = tmpl
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
    tmpl.root = stack[0]
