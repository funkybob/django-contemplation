
from .base import TAGS, Node, Variable
from .utils import smart_split

from itertools import cycle

# XXX CycleNode
# XXX FilterNode
# XXX FirstOfNode

class ForNode(Node):
    '''
    Repeating loop.

    {% for a, x, c in iterable %}.... {% endfor %}
    '''
    close_tag = 'endfor'
    raw_token = True
    is_block = True
    def __init__(self, tmpl, token):
        super(ForNode, self).__init__(tmpl)
        self.tmpl = tmpl
        bits = smart_split(token)
        bits.pop(0)

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

TAGS['for'] = ForNode

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
        context[self.name.resolve(context)] = cycle([
            value.resolve(context)
            for value in values
        ])

