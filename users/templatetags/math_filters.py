from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Násobí value * arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
