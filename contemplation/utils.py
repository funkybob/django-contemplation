
import re

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
    return [
        m.group(0)
        for m in split_re.finditer(string)
    ]

