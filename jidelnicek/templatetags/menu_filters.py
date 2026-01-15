from django import template

register = template.Library()

@register.filter
def sum_lengths(value):
    """Sečte délky všech seznamů ve slovníku"""
    try:
        return sum(len(v) for v in value)
    except:
        return 0
