"""Explicit-dollar mathematics shared by Qt text and scientific figures."""
import re

MATH_SPANS=re.compile(r'(?<!\\)\$\$(.+?)(?<!\\)\$\$|(?<!\\)\$([^$\n]+?)(?<!\\)\$',re.S)

def contains_math(text): return bool(MATH_SPANS.search(str(text)))

def figure_text(text):
    return re.sub(r'(?<!\\)\$\$(.+?)(?<!\\)\$\$',lambda match:'$'+match.group(1).strip()+'$',str(text),flags=re.S)
