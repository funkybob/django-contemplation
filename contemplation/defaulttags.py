
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

        # XXX use smarter parsing -- commas
        sp = bits.index('in')
        self.args = bits[:sp]
        self.source = Variable(bits[sp+1])
        assert len(bits) == sp + 2

    def render(self, context):
        source = self.source.resolve(context)
        output = []
        with context.push():
            for values in source:
                if len(self.args) == 1:
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

