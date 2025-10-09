# restaurant/templatetags/text_extras.py
import re
from django import template

register = template.Library()
ALPHA_RE = re.compile(r'[A-Za-z]')

@register.filter(name='first_alpha')
def first_alpha(value, count=10):
    """
    Return the first `count` alphabetic characters from `value`.
    Non-alpha characters are skipped. If there are more alphabetic characters
    than `count`, append an ellipsis.
    Example: "12ab-cd!efghij" with count=5 -> "abcde..."
    """
    if value is None:
        return ''
    s = str(value)
    result_chars = []
    alpha_seen = 0
    try:
        count = int(count)
    except (TypeError, ValueError):
        count = 10

    for ch in s:
        if ch.isalpha():
            result_chars.append(ch)
            alpha_seen += 1
            if alpha_seen >= count:
                break

    truncated = ''.join(result_chars)
    total_alpha = len(ALPHA_RE.findall(s))
    if total_alpha > count:
        return truncated + '...'
    return truncated
