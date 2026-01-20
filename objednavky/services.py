from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, F, Q
from django.utils import timezone
from collections import defaultdict

from .models import Order, OrderItem, PriceRecalculationLog, PriceRecalculationDetail
from jidelnicek.services import get_user_price_for_item


def recalculate_order_prices(date_from, date_to, user, dry_run=False):
    """
    Přepočítá ceny všech objednávek v daném období podle aktuálních cen a dotací.
    
    Args:
        date_from: První datum období
        date_to: Poslední datum období
        user: Uživatel, který přepočet provádí (pro audit log)
        dry_run: Pokud True, pouze simuluje a vrací preview změn
    
    Returns:
        dict: Statistiky přepočtu + případně preview změn
    """
    
    # Najdi všechny položky objednávek v daném období
    order_items = OrderItem.objects.filter(
        order__datum_vydeje__gte=date_from,
        order__datum_vydeje__lte=date_to
    ).select_related(
        'order__user',
        'menu_item__jidlo',
        'menu_item__druh_jidla'
    ).order_by('order__datum_vydeje', 'order__user__username')
    
    total_items = order_items.count()
    
    if total_items == 0:
        return {
            'success': False,
            'message': 'Žádné objednávky v daném období',
            'items_affected': 0,
            'orders_affected': 0,
            'total_price_diff': Decimal('0')
        }
    
    # Připrav statistiky
    changes = []
    affected_orders = set()
    total_price_diff = Decimal('0')
    items_changed = 0
    items_unchanged = 0
    
    # Projdi všechny položky
    for item in order_items:
        old_price = item.cena
        new_price = get_user_price_for_item(item.order.user, item.menu_item)
        
        # Zaokrouhli na 2 desetinná místa
        new_price = Decimal(str(new_price)).quantize(Decimal('0.01'))
        price_diff = new_price - old_price
        
        if abs(price_diff) >= Decimal('0.01'):  # Změna alespoň 1 haléř
            items_changed += 1
            affected_orders.add(item.order.id)
            total_price_diff += price_diff * item.quantity
            
            changes.append({
                'order_item': item,
                'old_price': old_price,
                'new_price': new_price,
                'price_diff': price_diff,
                'quantity': item.quantity,
                'total_diff': price_diff * item.quantity,
                'user': item.order.user,
                'date': item.order.datum_vydeje,
                'menu_item_name': item.menu_item.jidlo.nazev,
            })
        else:
            items_unchanged += 1
    
    # Pokud je dry_run, vrať pouze preview
    if dry_run:
        return {
            'success': True,
            'dry_run': True,
            'items_total': total_items,
            'items_changed': items_changed,
            'items_unchanged': items_unchanged,
            'orders_affected': len(affected_orders),
            'total_price_diff': total_price_diff,
            'changes': changes,  # Seznam všech změn pro preview
        }
    
    # Proveď skutečný přepočet v transakci
    with transaction.atomic():
        # Vytvoř audit log
        log = PriceRecalculationLog.objects.create(
            created_by=user,
            date_from=date_from,
            date_to=date_to,
            orders_affected=len(affected_orders),
            items_affected=items_changed,
            total_price_diff=total_price_diff,
            note=f"Přepočet cen pro období {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}"
        )
        
        # Ulož detaily změn a aplikuj nové ceny
        for change in changes:
            item = change['order_item']
            
            # Ulož detail do audit logu
            PriceRecalculationDetail.objects.create(
                log=log,
                order_item=item,
                old_price=change['old_price'],
                new_price=change['new_price'],
                price_diff=change['price_diff']
            )
            
            # Aktualizuj cenu v OrderItem
            item.cena = change['new_price']
            item.save(update_fields=['cena'])
            
            # Aktualizuj zůstatek uživatele
            user_obj = item.order.user
            balance_change = change['total_diff']
            
            try:
                current_balance = getattr(user_obj, 'aktualni_zustatek', Decimal('0'))
                new_balance = current_balance - balance_change
                user_obj.aktualni_zustatek = new_balance
                user_obj.save(update_fields=['aktualni_zustatek'])
            except Exception as e:
                print(f"⚠️ Chyba aktualizace zůstatku pro {user_obj.username}: {e}")
    
    return {
        'success': True,
        'dry_run': False,
        'log_id': log.id,
        'items_total': total_items,
        'items_changed': items_changed,
        'items_unchanged': items_unchanged,
        'orders_affected': len(affected_orders),
        'total_price_diff': total_price_diff,
        'message': f'Úspěšně přepočteno {items_changed} položek v {len(affected_orders)} objednávkách'
    }


def get_recalculation_summary_by_user(changes):
    """Seskupí změny podle uživatelů pro přehlednější zobrazení"""
    by_user = defaultdict(lambda: {
        'items': [],
        'total_diff': Decimal('0'),
        'items_count': 0
    })
    
    for change in changes:
        user = change['user']
        by_user[user]['items'].append(change)
        by_user[user]['total_diff'] += change['total_diff']
        by_user[user]['items_count'] += 1
    
    return dict(by_user)
