
from .base import register, Node, Variable
from .utils import smart_split

from datetime import datetime
from itertools import cycle

# XXX class AutoEscapeControlNode(Node):
# XXX class CommentNode(Node):
# XXX class CsrfTokenNode(Node):
# XXX class CycleNode(Node):
# XXX class DebugNode(Node):
# XXX class FilterNode(Node):
# XXX class FirstOfNode(Node):

@register.tag('for')
class ForNode(Node):
    '''
    Repeating loop.

    {% for a, x, c in iterable %}.... {% endfor %}
    '''
    close_tag = 'endfor'
    raw_token = True
    def __init__(self, token):
        super(ForNode, self).__init__()
        bits = smart_split(token)
        bits.pop(0)

        if len(bits) < 3:
            raise TemplateSyntaxError("'for' statement should have at least four words: %s" % token)

        self.is_reversed = bits[-1] == 'reversed'
        if self.is_reversed:
            bits.pop()

        source = Variable(bits.pop())
        if bits.pop() != 'in':
            raise TemplateSyntaxError("'for' statement should use the format 'for x in y': %s" % token)

        loop_vars = re.split(r' *, *', ' '.join(bits))
        for var in loop_vars:
            if not var or ' ' in var:
                raise TemplateSyntaxError("'for' tag received an invalid argument: %s" % token)

        self.args = loop_vars

    def render(self, context):
        source = self.source.resolve(context)
        if self.is_reversed():
            source = reversed(source)
        output = []
        unpack = len(self.args) > 1
        with context.push():
            for values in source:
                if unpack:
                    context.maps[0][self.args[0]] = values
                else:
                    context.maps[0].update(
                        zip(self.args, values)
                    )
                output.append(self.nodelist.render(context))
        return ''.join(output)

# XXX class IfChangedNode(Node):
# XXX class IfEqualNode(Node):
# XXX class IfNode(Node):
# XXX class RegroupNode(Node):
# XXX class SsiNode(Node):
# XXX class LoadNode(Node):
# XXX class NowNode(Node):

@register.tag('now')
class NowNode(Node):
    def __init__(self, format_string):
        self.format_string = format_string

    def render(self, context):
        return datetime.now().strftime(self.format_string.resolve(context))

# XXX class SpacelessNode(Node):
# XXX class TemplateTagNode(Node):
# XXX class URLNode(Node):
# XXX class VerbatimNode(Node):
# XXX class WidthRatioNode(Node):
# XXX class WithNode(Node):

@register.tag('with')
class WithNode(Node):
    close_tag = 'endwith'
    def __init__(self, **kwargs):
        super(WithNode, self).__init__()
        self.kwargs = kwargs

    def render(self, context):
        new_data = {
            key: val.resolve(context)
            for key, val in self.kwargs.items()
        }
        with context.push(**new_data):
            return self.nodelist.render(context)

# XXX class TemplateLiteral(Literal):
# XXX class TemplateIfParser(IfParser):

class LoopObject(object):
    '''
    An object to cycle values under control.
    '''
    def __init__(self, *values):
        self.values = values
        self.index = 0

    def __unicode__(self):
        return self.values[self.index]

    def step(self):
        self.index = (self.index + 1) % len(self.values)

    def next(self):
        self.step()
        return unicode(self)

@register.tag('loop')
class LoopNode(Node):
    '''
    Add a cycle() of values to the context
        {% loop 'first' a b c %}
        {{ first }}

    '''
    def __init__(self, name, *values):
        self.name
        self.values = values

    def render(self, context):
        context[self.name.resolve(context)] = LoopObject(*[
            value.resolve(context)
            for value in values
        ])

