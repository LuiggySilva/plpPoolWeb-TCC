from django.template.defaultfilters import register
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from django.utils.safestring import mark_safe

@register.filter(name='highlight_code')
def highlight_code(codigo, linguagem):
    lexer = get_lexer_by_name(linguagem.nome.lower())
    return mark_safe(highlight(codigo, lexer, HtmlFormatter(style='monokai')))
