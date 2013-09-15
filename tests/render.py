# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from contemplation import Template, Context, TemplateSyntaxError

class SomeClass:
    def __init__(self):
        self.otherclass = OtherClass()

    def method(self):
        return "SomeClass.method"

    def method2(self, o):
        return o

    def method3(self):
        raise SomeException

    def method4(self):
        raise SomeOtherException

    def method5(self):
        raise TypeError

    def __getitem__(self, key):
        if key == 'silent_fail_key':
            raise SomeException
        elif key == 'noisy_fail_key':
            raise SomeOtherException
        raise KeyError

    def silent_fail_attribute(self):
        raise SomeException
    silent_fail_attribute = property(silent_fail_attribute)

    def noisy_fail_attribute(self):
        raise SomeOtherException
    noisy_fail_attribute = property(noisy_fail_attribute)

class OtherClass:
    def method(self):
        return "OtherClass.method"

class TestObj(object):
    def is_true(self):
        return True

    def is_false(self):
        return False

    def is_bad(self):
        raise ShouldNotExecuteException()

class SilentGetItemClass(object):
    def __getitem__(self, key):
        raise SomeException

class SilentAttrClass(object):
    def b(self):
        raise SomeException
    b = property(b)

class UTF8Class:
    "Class whose __str__ returns non-ASCII data on Python 2"
    def __str__(self):
        return 'ŠĐĆŽćžšđ'

class RenderTests(unittest.TestCase):

    GOOD_CASES = (
        # Plain text should go through the template parser untouched
        ("something cool", {}, "something cool"),

        # Variables should be replaced with their value in the current
        # context
        ("{{ headline }}", {'headline':'Success'}, "Success"),

        # More than one replacement variable is allowed in a template
        ("{{ first }} --- {{ second }}", {"first" : 1, "second" : 2}, "1 --- 2"),

        # Fail silently when a variable is not found in the current context
        ("as{{ missing }}df", {}, "asINVALIDdf"),

        # Attribute syntax allows a template to call an object's attribute
        ("{{ var.method }}", {"var": SomeClass()}, "SomeClass.method"),

        # Multiple levels of attribute access are allowed
        ("{{ var.otherclass.method }}", {"var": SomeClass()}, "OtherClass.method"),

        # Fail silently when a variable's attribute isn't found
        ("{{ var.blech }}", {"var": SomeClass()}, "INVALID"),

        # Attribute syntax allows a template to call a dictionary key's value
        ("{{ foo.bar }}", {"foo" : {"bar" : "baz"}}, "baz"),

        # Fail silently when a variable's dictionary key isn't found
        ("{{ foo.spam }}", {"foo" : {"bar" : "baz"}}, "INVALID"),

        # Fail silently when accessing a non-simple method
        ("{{ var.method2 }}", {"var": SomeClass()}, "INVALID"),

        # Don't get confused when parsing something that is almost, but not
        # quite, a template tag.
        ("a {{ moo %} b", {}, "a {{ moo %} b"),
        ("{{ moo #}", {}, "{{ moo #}"),

        # Literal strings are permitted inside variables, mostly for i18n
        # purposes.
        ('{{ "fred" }}', {}, "fred"),
        (r'{{ "\"fred\"" }}', {}, "\"fred\""),

        # regression test for ticket #12554
        # make sure a silent_variable_failure Exception is supressed
        # on dictionary and attribute lookup
        ("{{ a.b }}", {'a': SilentGetItemClass()}, ('', 'INVALID')),
        ("{{ a.b }}", {'a': SilentAttrClass()}, ('', 'INVALID')),

        # Something that starts like a number but has an extra lookup works as a lookup.
        ("{{ 1.2.3 }}", {"1": {"2": {"3": "d"}}}, "d"),
        ("{{ 1.2.3 }}", {"1": {"2": ("a", "b", "c", "d")}}, "d"),
        ("{{ 1.2.3 }}", {"1": (("x", "x", "x", "x"), ("y", "y", "y", "y"), ("a", "b", "c", "d"))}, "d"),
        ("{{ 1.2.3 }}", {"1": ("xxxx", "yyyy", "abcd")}, "d"),
        ("{{ 1.2.3 }}", {"1": ({"x": "x"}, {"y": "y"}, {"z": "z", "3": "d"})}, "d"),

        # Numbers are numbers even if their digits are in the context.
        ("{{ 1 }}", {"1": "abc"}, "1"),
        ("{{ 1.2 }}", {"1": "abc"}, "1.2"),

        # Call methods in the top level of the context
        ('{{ callable }}', {"callable": lambda: "foo bar"}, "foo bar"),

        # Call methods returned from dictionary lookups
        ('{{ var.callable }}', {"var": {"callable": lambda: "foo bar"}}, "foo bar"),

        ('{{ True }}', {}, "True"),
        ('{{ False }}', {}, "False"),
        ('{{ None }}', {}, "None"),

        # List-index syntax allows a template to access a certain item of a subscriptable object.
        ("{{ var.1 }}", {"var": ["first item", "second item"]}, "second item"),

        # Fail silently when the list index is out of range.
        ("{{ var.5 }}", {"var": ["first item", "second item"]}, ("", "INVALID")),

        # Fail silently when the variable is not a subscriptable object.
        ("{{ var.1 }}", {"var": None}, ("", "INVALID")),

        # Fail silently when variable is a dict without the specified key.
        ("{{ var.1 }}", {"var": {}}, ("", "INVALID")),

        # Dictionary lookup wins out when dict's key is a string.
        ("{{ var.1 }}", {"var": {'1': "hello"}}, "hello"),

        # But list-index lookup wins out when dict's key is an int, which
        # behind the scenes is really a dictionary lookup (for a dict)
        # after converting the key to an int.
        ("{{ var.1 }}", {"var": {1: "hello"}}, "hello"),

        # Dictionary lookup wins out when there is a string and int version of the key.
        ("{{ var.1 }}", {"var": {'1': "hello", 1: "world"}}, "hello"),

        # Basic filter usage
        ("{{ var|upper }}", {"var": "Django is the greatest!"}, "DJANGO IS THE GREATEST!"),

        # Chained filters
        ("{{ var|upper|lower }}", {"var": "Django is the greatest!"}, "django is the greatest!"),

        # Allow spaces before the filter pipe
        ("{{ var |upper }}", {"var": "Django is the greatest!"}, "DJANGO IS THE GREATEST!"),

        # Allow spaces after the filter pipe
        ("{{ var| upper }}", {"var": "Django is the greatest!"}, "DJANGO IS THE GREATEST!"),

        # Chained filters, with an argument to the first one
        ('{{ var|removetags:"b i"|upper|lower }}', {"var": "<b><i>Yes</i></b>"}, "yes"),

        # Literal string as argument is always "safe" from auto-escaping..
        (r'{{ var|default_if_none:" endquote\" hah" }}',
                {"var": None}, ' endquote" hah'),

        # Variable as argument
        (r'{{ var|default_if_none:var2 }}', {"var": None, "var2": "happy"}, 'happy'),

        # Default argument testing
        (r'{{ var|yesno:"yup,nup,mup" }} {{ var|yesno }}', {"var": True}, 'yup yes'),

        # Fail silently for methods that raise an exception with a
        # "silent_variable_failure" attribute
        (r'1{{ var.method3 }}2', {"var": SomeClass()}, ("12", "1INVALID2")),

        # Escaped backslash in argument
        (r'{{ var|default_if_none:"foo\bar" }}', {"var": None}, r'foo\bar'),

        # Escaped backslash using known escape char
        (r'{{ var|default_if_none:"foo\now" }}', {"var": None}, r'foo\now'),

        # Empty strings can be passed as arguments to filters
        (r'{{ var|join:"" }}', {'var': ['a', 'b', 'c']}, 'abc'),

        # Make sure that any unicode strings are converted to bytestrings
        # in the final output.
        (r'{{ var }}', {'var': UTF8Class()}, '\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'),

        # Numbers as filter arguments should work
        ('{{ var|truncatewords:1 }}', {"var": "hello world"}, "hello ..."),

        #filters should accept empty string constants
        ('{{ ""|default_if_none:"was none" }}', {}, ""),

        # Fail silently for non-callable attribute and dict lookups which
        # raise an exception with a "silent_variable_failure" attribute
        (r'1{{ var.silent_fail_key }}2', {"var": SomeClass()}, ("12", "1INVALID2")),
        (r'1{{ var.silent_fail_attribute }}2', {"var": SomeClass()}, ("12", "1INVALID2")),

        ### COMMENT SYNTAX ########################################################
        ("{# this is hidden #}hello", {}, "hello"),
        ("{# this is hidden #}hello{# foo #}", {}, "hello"),

        # Comments can contain invalid stuff.
        ("foo{#  {% if %}  #}", {}, "foo"),
        ("foo{#  {% endblock %}  #}", {}, "foo"),
        ("foo{#  {% somerandomtag %}  #}", {}, "foo"),
        ("foo{# {% #}", {}, "foo"),
        ("foo{# %} #}", {}, "foo"),
        ("foo{# %} #}bar", {}, "foobar"),
        ("foo{# {{ #}", {}, "foo"),
        ("foo{# }} #}", {}, "foo"),
        ("foo{# { #}", {}, "foo"),
        ("foo{# } #}", {}, "foo"),

        ### COMMENT TAG ###########################################################
        ("{% comment %}this is hidden{% endcomment %}hello", {}, "hello"),
        ("{% comment %}this is hidden{% endcomment %}hello{% comment %}foo{% endcomment %}", {}, "hello"),

        # Comment tag can contain invalid stuff.
        ("foo{% comment %} {% if %} {% endcomment %}", {}, "foo"),
        ("foo{% comment %} {% endblock %} {% endcomment %}", {}, "foo"),
        ("foo{% comment %} {% somerandomtag %} {% endcomment %}", {}, "foo"),


        # XXX ---
        # For tag
        ('{% for x in y %}{{ x }}{% endfor %}', {'x': 'BAD', 'y': range(3)}, '012'),
        ('{% for a b in z %}{{ a }} {{ b }}{% endfor %}', {'z': ['AB', 'CD']}, 'A BC D'),

        # With tag
        ('{% with a=7 %}{{ a }}{% endwith %}', {'a': 'BAD'}, '7'),

        # Nested tags
        ('{% for x in y %}{% with b=x %}{{ b }}{% endwith %}{% endfor %}', {'y': '123'}, '123'),


        ### FOR TAG ###############################################################
        ("{% for val in values %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "123"),
        ("{% for val in values reversed %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "321"),
        ("{% for val in values %}{{ forloop.counter }}{% endfor %}", {"values": [6, 6, 6]}, "123"),
        ("{% for val in values %}{{ forloop.counter0 }}{% endfor %}", {"values": [6, 6, 6]}, "012"),
        ("{% for val in values %}{{ forloop.revcounter }}{% endfor %}", {"values": [6, 6, 6]}, "321"),
        ("{% for val in values %}{{ forloop.revcounter0 }}{% endfor %}", {"values": [6, 6, 6]}, "210"),
        ("{% for val in values %}{% if forloop.first %}f{% else %}x{% endif %}{% endfor %}", {"values": [6, 6, 6]}, "fxx"),
        ("{% for val in values %}{% if forloop.last %}l{% else %}x{% endif %}{% endfor %}", {"values": [6, 6, 6]}, "xxl"),
        ("{% for key,value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
        ("{% for key, value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
        ("{% for key , value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
        ("{% for key ,value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
        # Ensure that a single loopvar doesn't truncate the list in val.
        ("{% for val in items %}{{ val.0 }}:{{ val.1 }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
        # Otherwise, silently truncate if the length of loopvars differs to the length of each set of items.
        ("{% for x,y in items %}{{ x }}:{{ y }}/{% endfor %}", {"items": (('one', 1, 'carrot'), ('two', 2, 'orange'))}, "one:1/two:2/"),
        ("{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, ("one:1,/two:2,/", "one:1,INVALID/two:2,INVALID/")),
        ("{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}", {"items": (('one', 1, 'carrot'), ('two', 2))}, ("one:1,carrot/two:2,/", "one:1,carrot/two:2,INVALID/")),
        ("{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}", {"items": (('one', 1, 'carrot'), ('two', 2, 'cheese'))}, ("one:1,carrot/two:2,cheese/", "one:1,carrot/two:2,cheese/")),
        ("{% for x,y in items %}{{ x }}:{{ y }}/{% endfor %}", {"items": (1, 2)}, (":/:/", "INVALID:INVALID/INVALID:INVALID/")),
        ("{% for val in values %}{{ val }}{% empty %}empty text{% endfor %}", {"values": [1, 2, 3]}, "123"),
        ("{% for val in values %}{{ val }}{% empty %}values array empty{% endfor %}", {"values": []}, "values array empty"),
        ("{% for val in values %}{{ val }}{% empty %}values array not found{% endfor %}", {}, "values array not found"),
        # Ticket 19882
        ("{% load custom %}{% for x in s|noop:'x y' %}{{ x }}{% endfor %}", {'s': 'abc'}, 'abc'),

    )

    def test_good(self):
        for tmpl, ctx, output in self.GOOD_CASES:
            t = Template(tmpl)
            c = Context(ctx, invalid='INVALID')
            o = t.render(c)
            self.assertEqual(o, output)

    BAD_CASES = (
        ("{{ va>r }}", {}, TemplateSyntaxError),
        ("{{ (var.r) }}", {}, TemplateSyntaxError),
        ("{{ sp%am }}", {}, TemplateSyntaxError),
        ("{{ eggs! }}", {}, TemplateSyntaxError),
        ("{{ moo? }}", {}, TemplateSyntaxError),
        ("{% for key value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, TemplateSyntaxError),
        ("{% for key,,value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, TemplateSyntaxError),
        ("{% for key,value, in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, TemplateSyntaxError),
    )

    def test_bad(self):
        for tmpl, ctx, exc in self.BAD_CASES:
            with self.assertRaises(exc):
                t = Template(tmpl)
                c = Context(ctx)
                o = t.render(c)

if __name__ == '__main__':
    unittest.main()
