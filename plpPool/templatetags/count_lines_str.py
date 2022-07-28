from django.template.defaultfilters import register


@register.filter(name='count_lines_str')
def count_lines_str(string):
    return len(string.split('\n')) * 18

@register.filter(name='count_lines_str_monitor')
def count_lines_str(string):
    return len(string.split('\n')) * 24
