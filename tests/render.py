
import unittest

from contemplation import Template, Context, TemplateSyntaxError

class RenderTests(unittest.TestCase):

    GOOD_CASES = (
        # Raw text
        ('Hello!', {}, 'Hello!'),
        # Basic variable
        ('{{ i }}', {'i': 'Hello!'}, 'Hello!'),
        ('Hello, {{ foo }}!', {'foo': 'World'}, 'Hello, World!'),
        ('{{ a }} -- {{ b }}', {'a': 1, 'b': 'b'}, '1 -- b'),
        # Variable lookups
        ('{{ foo.bar }}', {'foo': {'bar': 'baz'}}, 'baz'),
        ('{{ foo.1 }}', {'foo': ['a', 'b']}, 'b'),
        ('{{ foo.title }}', {'foo': 'something'}, 'Something'),
        ('{{ foo }}', {'foo': lambda : 'bar'}, 'bar'),
        # XXX multi-level lookups
        # Comments
        ('abc{# comment #}def', {}, 'abcdef'),
        # Invalid syntax
        ('{% foo }}', {}, '{% foo }}'),

        # For tag
        ('{% for x in y %}{{ x }}{% endfor %}', {'x': 'BAD', 'y': range(3)}, '012'),
        ('{% for a b in z %}{{ a }} {{ b }}{% endfor %}', {'z': ['AB', 'CD']}, 'A BC D'),

        # With tag
        ('{% with a=7 %}{{ a }}{% endwith %}', {'a': 'BAD'}, '7'),

        # Nested tags
        ('{% for x in y %}{% with b=x %}{{ b }}{% endwith %}{% endfor %}', {'y': '123'}, '123'),

        # Literal strings are permitted inside variables
        (r'{{ "fred" }}', {}, "fred"),
        #(r'{{ "\"fred\"" }}', {}, "\"fred\""),

        # Something that starts like a number but has an extra lookup works as a lookup.
        ("{{ 1.2.3 }}", {"1": {"2": {"3": "d"}}}, "d"),
        ("{{ 1.2.3 }}", {"1": {"2": ("a", "b", "c", "d")}}, "d"),
        ("{{ 1.2.3 }}", {"1": (("x", "x", "x", "x"), ("y", "y", "y", "y"), ("a", "b", "c", "d"))}, "d"),
        ("{{ 1.2.3 }}", {"1": ("xxxx", "yyyy", "abcd")}, "d"),
        ("{{ 1.2.3 }}", {"1": ({"x": "x"}, {"y": "y"}, {"z": "z", "3": "d"})}, "d"),

    )

    def test_good(self):
        for tmpl, ctx, output in self.GOOD_CASES:
            t = Template(tmpl)
            c = Context(ctx)
            o = t.render(c)
            self.assertEqual(o, output)

    BAD_CASES = (
        ("{{ va>r }}", TemplateSyntaxError),
        ("{{ (var.r) }}", TemplateSyntaxError),
        ("{{ sp%am }}", TemplateSyntaxError),
        ("{{ eggs! }}", TemplateSyntaxError),
        ("{{ moo? }}", TemplateSyntaxError),
    )

    def test_bad(self):
        for tmpl, exc in self.BAD_CASES:
            with self.assertRaises(exc):
                t = Template(tmpl)

if __name__ == '__main__':
    unittest.main()
