from django.template.defaultfilters import register

@register.filter(name='str_lines')
def str_lines(string):
    return string.split('\n')

@register.filter(name='str_lines_strip')
def str_lines_strip(string):
    return string.strip().split('\n')
