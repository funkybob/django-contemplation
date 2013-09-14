
import unittest

from contemplation import Template, Context

class RenderTests(unittest.TestCase):

    TEST_CASES = (
        # Raw text
        ('Hello!', {}, 'Hello!'),
        # Basic variable
        ('{{ i }}', {'i': 'Hello!'}, 'Hello!'),
        ('Hello, {{ foo }}!', {'foo': 'World'}, 'Hello, World!'),
        ('{{ a }} -- {{ b }}', {'a': 1, 'b': 'b'}, '1 -- b'),
        # Variable lookups
        ('{{ foo.bar }}', {'foo': {'bar': 'baz'}}, 'baz'),
        ('{{ foo.1 }}', {'foo': ['a', 'b']}, 'b'),
    )

    def test_good(self):
        for tmpl, ctx, output in self.TEST_CASES:
            t = Template(tmpl)
            c = Context(ctx)
            o = t.render(c)
            self.assertEqual(o, output)


if __name__ == '__main__':
    unittest.main()
