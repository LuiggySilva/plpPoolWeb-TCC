from django.template.defaultfilters import register
import re

@register.filter(name='verify_url')
def verify_url(url):
    out = re.search("^.*\/admin\/plpPool\/questao\/[0-9]*\/change\/$", url)
    return out
