from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_code_highlighted(name, code):

    try:
        lexer = get_lexer_by_name(name, stripall=True)
    except Exception:
        lexer = get_lexer_by_name("text", stripall=True)

    formatter = HtmlFormatter(style="monokai", linenos=True)
    highlighted_code = highlight(code, lexer, formatter)
    return mark_safe(highlighted_code)


@register.simple_tag
def pygments_css():
    formatter = HtmlFormatter(style="monokai")
    return mark_safe(formatter.get_style_defs(".highlight"))
