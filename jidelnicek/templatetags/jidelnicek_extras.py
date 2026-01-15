from django import template

register = template.Library()

@register.filter
def dictsum(dictionary, key):
    """Součet délek všech hodnot v dict"""
    return sum(len(items) for items in dictionary.values())

from django import template

register = template.Library()

@register.filter
def sum_lengths(value):
    """Sečte délky všech seznamů ve slovníku"""
    try:
        return sum(len(v) for v in value)
    except:
        return 0

