from django import template
from django.utils import timezone
from canteen_settings.models import MealPickupTime

register = template.Library()

@register.filter
def current_items(items):
    """Vrátí pouze nevydané položky s aktuálním výdejním časem"""
    now = timezone.localtime(timezone.now()).time()
    
    # Získej ID druhů jídel s aktuálním výdejním časem
    current_meal_type_ids = MealPickupTime.objects.filter(
        pickup_from__lte=now,
        pickup_to__gte=now
    ).values_list('druh_jidla_id', flat=True)
    
    # Filtruj položky
    return items.filter(
        vydano=False,
        menu_item__druh_jidla_id__in=current_meal_type_ids
    )


@register.filter
def issued_items(items):
    """Vrátí pouze vydané položky"""
    return items.filter(vydano=True)


@register.filter
def pending_items(items):
    """Vrátí pouze nevydané položky"""
    return items.filter(vydano=False)


@register.filter
def exclude(items, **kwargs):
    """Generic exclude filter"""
    return items.exclude(**kwargs)
