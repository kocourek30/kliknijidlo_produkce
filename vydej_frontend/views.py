# vydej_frontend/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import date
from decimal import Decimal
import serial
import json
from django.views.decorators.csrf import csrf_exempt

from objednavky.models import Order, OrderItem
from vydej.models import VydejniUctenka, PolozkaUctenky
from canteen_settings.models import MealPickupTime
from jidelnicek.models import PolozkaJidelnicku
from django.db.models import Count, Sum, Q
from django.contrib.auth import get_user_model

from .decorators import obsluha_required

User = get_user_model()


def get_current_meal_type_ids():
    """Vrátí ID druhů jídel s aktuálním výdejním časem"""
    now = timezone.localtime(timezone.now()).time()
    return list(MealPickupTime.objects.filter(
        pickup_from__lte=now,
        pickup_to__gte=now
    ).values_list('druh_jidla_id', flat=True))


def prepare_order_with_items(order, current_meal_type_ids):
    """Připraví objednávku s rozdělením položek"""
    all_items = order.items.select_related('menu_item__jidlo', 'menu_item__druh_jidla').all()
    
    return {
        'order': order,
        'current_items': [item for item in all_items 
                         if not item.vydano and item.menu_item.druh_jidla_id in current_meal_type_ids],
        'issued_items': [item for item in all_items if item.vydano],
        'pending_items': [item for item in all_items if not item.vydano],
        'has_other_items': any(item for item in all_items 
                              if not item.vydano and item.menu_item.druh_jidla_id not in current_meal_type_ids)
    }


def get_current_meal_types_with_counts(today, current_meal_type_ids):
    """Vrátí aktuálně vydávané druhy jídel s počty"""
    now = timezone.localtime(timezone.now()).time()
    
    active_pickup_times = MealPickupTime.objects.filter(
        pickup_from__lte=now,
        pickup_to__gte=now
    ).select_related('druh_jidla')
    
    for pickup in active_pickup_times:
        menu_items = PolozkaJidelnicku.objects.filter(
            druh_jidla=pickup.druh_jidla,
            jidelnicek__platnost_od__lte=today,
            jidelnicek__platnost_do__gte=today
        ).select_related('jidlo')
        
        meals_with_counts = []
        for menu_item in menu_items:
            count = OrderItem.objects.filter(
                order__datum_vydeje=today,
                order__status__in=['objednano', 'zalozena-obsluhou', 'castecne-vydano'],
                menu_item=menu_item,
                vydano=False
            ).aggregate(total=Sum('quantity'))['total'] or 0
            
            if count > 0:
                meals_with_counts.append({
                    'menu_item': menu_item,
                    'count': count
                })
        
        pickup.meals_with_counts = meals_with_counts
    
    return active_pickup_times


@login_required
@obsluha_required
def dashboard(request):
    today = date.today()
    current_meal_type_ids = get_current_meal_type_ids()
    
    # Pending orders (k výdeji)
    pending_orders_qs = Order.objects.filter(
        datum_vydeje=today,
        status__in=['objednano', 'zalozena-obsluhou', 'castecne-vydano']
    ).select_related('user').prefetch_related(
        'items__menu_item__jidlo',
        'items__menu_item__druh_jidla'
    ).order_by('user__last_name', 'user__first_name')
    
    pending_orders = []
    for order in pending_orders_qs:
        prepared = prepare_order_with_items(order, current_meal_type_ids)
        if prepared['current_items']:
            pending_orders.append(prepared)
    
    # Completed orders (vydané dnes)
    completed_orders_qs = Order.objects.filter(
        datum_vydeje=today,
        status__in=['vydano', 'castecne-vydano']
    ).exclude(
        datum_vydani__isnull=True
    ).select_related('user').prefetch_related(
        'items__menu_item__jidlo',
        'items__menu_item__druh_jidla'
    ).order_by('-datum_vydani')[:20]
    
    completed_orders = []
    for order in completed_orders_qs:
        prepared = prepare_order_with_items(order, current_meal_type_ids)
        if prepared['issued_items']:
            completed_orders.append(prepared)
    
    # Aktuální výdejní časy
    meal_types = get_current_meal_types_with_counts(today, current_meal_type_ids)
    
    # Statistiky položek k výdeji POUZE pro aktuální výdejní časy
    pending_items = OrderItem.objects.filter(
        order__datum_vydeje=today,
        order__status__in=['objednano', 'zalozena-obsluhou', 'castecne-vydano'],
        vydano=False,
        menu_item__druh_jidla_id__in=current_meal_type_ids
    ).select_related(
        'menu_item__jidlo', 'menu_item__druh_jidla'
    ).values(
        'menu_item__jidlo__nazev',
        'menu_item__druh_jidla__nazev'
    ).annotate(
        total_quantity=Sum('quantity')
    ).order_by('menu_item__druh_jidla__nazev', 'menu_item__jidlo__nazev')
    
    context = {
        'today': today,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'meal_types': meal_types,
        'current_meal_type_ids': current_meal_type_ids,
        'pending_items': pending_items,
        'pending_count': len(pending_orders),
        'completed_count': len(completed_orders),
    }
    
    return render(request, 'vydej_frontend/dashboard.html', context)


@login_required
@obsluha_required
@require_POST
def issue_order(request, order_id):
    """AJAX endpoint pro vydání AKTUÁLNÍCH položek objednávky"""
    try:
        order = Order.objects.select_related('user').prefetch_related(
            'items__menu_item__jidlo',
            'items__menu_item__druh_jidla'
        ).get(id=order_id)
        
        if order.status not in ['objednano', 'zalozena-obsluhou', 'castecne-vydano']:
            return JsonResponse({
                'success': False,
                'error': 'Objednávka nemůže být vydána (nesprávný stav)'
            }, status=400)
        
        now = timezone.localtime(timezone.now()).time()
        current_meal_type_ids = list(MealPickupTime.objects.filter(
            pickup_from__lte=now,
            pickup_to__gte=now
        ).values_list('druh_jidla_id', flat=True))
        
        if not current_meal_type_ids:
            return JsonResponse({
                'success': False,
                'error': 'Nyní není žádný výdejní čas'
            }, status=400)
        
        items_to_issue = order.items.filter(
            vydano=False,
            menu_item__druh_jidla_id__in=current_meal_type_ids
        )
        
        if not items_to_issue.exists():
            return JsonResponse({
                'success': False,
                'error': 'Žádné položky k vydání v aktuálním čase'
            }, status=400)
        
        uctenka, created = VydejniUctenka.objects.get_or_create(
            order=order,
            defaults={
                'datum_vydeje': timezone.now(),
                'vydal': request.user,
                'celkova_cena': Decimal('0'),
                'celkova_dotace': Decimal('0')
            }
        )
        
        vydane_polozky = []
        for item in items_to_issue:
            cena_za_kus = item.cena
            puvodni_cena = item.menu_item.jidlo.cena
            dotace_za_kus = puvodni_cena - cena_za_kus
            
            PolozkaUctenky.objects.create(
                uctenka=uctenka,
                nazev_jidla=item.menu_item.jidlo.nazev,
                druh_jidla=item.menu_item.druh_jidla.nazev,
                mnozstvi=item.quantity,
                cena_za_kus=cena_za_kus,
                dotace_za_kus=dotace_za_kus
            )
            
            uctenka.celkova_cena += cena_za_kus * item.quantity
            uctenka.celkova_dotace += dotace_za_kus * item.quantity
            
            item.vydano = True
            item.datum_vydani = timezone.now()
            item.save()
            
            vydane_polozky.append(f"{item.quantity}× {item.menu_item.jidlo.nazev}")
        
        uctenka.save()
        
        if order.items.filter(vydano=False).exists():
            order.status = 'castecne-vydano'
        else:
            order.status = 'vydano'
        
        order.datum_vydani = timezone.now()
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Vydáno pro {order.user.get_full_name()}: {", ".join(vydane_polozky)}',
            'uctenka_id': uctenka.id,
            'partial': order.status == 'castecne-vydano'
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Objednávka nenalezena'
        }, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Chyba při vydávání objednávky {order_id}: {str(e)}', exc_info=True)
        
        return JsonResponse({
            'success': False,
            'error': f'Chyba při vytváření účtenky: {str(e)}'
        }, status=500)


@login_required
@obsluha_required
def refresh_data(request):
    """AJAX endpoint pro refresh dashboard dat"""
    today = date.today()
    current_meal_type_ids = get_current_meal_type_ids()
    
    pending_orders_qs = Order.objects.filter(
        datum_vydeje=today,
        status__in=['objednano', 'zalozena-obsluhou', 'castecne-vydano']
    ).select_related('user').prefetch_related(
        'items__menu_item__jidlo',
        'items__menu_item__druh_jidla'
    ).order_by('user__last_name', 'user__first_name')
    
    pending_orders = []
    for order in pending_orders_qs:
        prepared = prepare_order_with_items(order, current_meal_type_ids)
        if prepared['current_items']:
            pending_orders.append(prepared)
    
    completed_orders_qs = Order.objects.filter(
        datum_vydeje=today,
        status__in=['vydano', 'castecne-vydano']
    ).exclude(
        datum_vydani__isnull=True
    ).select_related('user').prefetch_related(
        'items__menu_item__jidlo',
        'items__menu_item__druh_jidla'
    ).order_by('-datum_vydani')[:20]
    
    completed_orders = []
    for order in completed_orders_qs:
        prepared = prepare_order_with_items(order, current_meal_type_ids)
        if prepared['issued_items']:
            completed_orders.append(prepared)
    
    pending_items = OrderItem.objects.filter(
        order__datum_vydeje=today,
        order__status__in=['objednano', 'zalozena-obsluhou', 'castecne-vydano'],
        vydano=False,
        menu_item__druh_jidla_id__in=current_meal_type_ids
    ).select_related(
        'menu_item__jidlo', 'menu_item__druh_jidla'
    ).values(
        'menu_item__jidlo__nazev',
        'menu_item__druh_jidla__nazev'
    ).annotate(
        total_quantity=Sum('quantity')
    ).order_by('menu_item__druh_jidla__nazev', 'menu_item__jidlo__nazev')
    
    pending_html = render_to_string('vydej_frontend/partials/pending_orders.html', {
        'pending_orders': pending_orders
    })
    
    completed_html = render_to_string('vydej_frontend/partials/completed_orders.html', {
        'completed_orders': completed_orders
    })
    
    recent_html = render_to_string('vydej_frontend/partials/recent_orders.html', {
        'completed_orders': completed_orders
    })
    
    summary_html = render_to_string('vydej_frontend/partials/summary_footer.html', {
        'pending_items': pending_items
    })
    
    return JsonResponse({
        'success': True,
        'rfid_ready': True,
        'pending_count': len(pending_orders),
        'completed_count': len(completed_orders),
        'pending_orders_html': pending_html,
        'completed_orders_html': completed_html,
        'recent_orders_html': recent_html,
        'summary_html': summary_html
    })


@csrf_exempt
@require_POST
def rfid_scan(request):
    """Najde objednávku podle RFID - zobrazí i už vydané"""
    try:
        data = json.loads(request.body)
        rfid_tag = data.get('rfid_tag', '').strip()
        
        if not rfid_tag:
            return JsonResponse({'success': False, 'error': 'Žádný RFID tag'})
        
        # Najdi uživatele podle pole identifikacni_medium
        try:
            user = User.objects.get(identifikacni_medium=rfid_tag)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Uživatel s kartou {rfid_tag} nenalezen v systému'
            })
        
        # Najdi dnešní objednávku
        today = date.today()
        
        # 🔥 NEJDŘÍV ZKUS NAJÍT NEVYDANOU
        order = Order.objects.filter(
            user=user,
            datum_vydeje=today,
            status__in=['objednano', 'zalozena-obsluhou', 'castecne-vydano']
        ).select_related('user').prefetch_related(
            'items__menu_item__jidlo',
            'items__menu_item__druh_jidla'
        ).order_by('-created_at').first()
        
        # Získej aktuální výdejní časy
        now = timezone.localtime(timezone.now()).time()
        current_meal_type_ids = list(MealPickupTime.objects.filter(
            pickup_from__lte=now,
            pickup_to__gte=now
        ).values_list('druh_jidla_id', flat=True))
        
        if order:
            # Má nevydanou objednávku
            if not current_meal_type_ids:
                return JsonResponse({
                    'success': False,
                    'error': f'Nyní není žádný výdejní čas pro {user.get_full_name()}. Zkuste později.'
                })
            
            # Zkontroluj, zda jsou položky k vydání
            pending_items = order.items.filter(
                vydano=False,
                menu_item__druh_jidla_id__in=current_meal_type_ids
            )
            
            if not pending_items.exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Žádné položky k vydání v aktuálním čase pro {user.get_full_name()}'
                })
            
            # ✅ ÚSPĚCH - Vrať informaci o objednávce
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'user_name': user.get_full_name(),
                'already_issued': False
            })
        
        # 🔥 POKUD NENÍ NEVYDANÁ, NAJDI UŽ VYDANOU
        issued_order = Order.objects.filter(
            user=user,
            datum_vydeje=today,
            status='vydano'
        ).select_related('user').prefetch_related(
            'items__menu_item__jidlo',
            'items__menu_item__druh_jidla'
        ).order_by('-datum_vydani').first()
        
        if issued_order:
            # ✅ Našli jsme už vydanou objednávku
            return JsonResponse({
                'success': True,
                'order_id': issued_order.id,
                'user_name': user.get_full_name(),
                'already_issued': True  # 🔥 KLÍČOVÝ FLAG
            })
        
        # Žádná objednávka nenalezena
        return JsonResponse({
            'success': False,
            'error': f'Žádná objednávka pro {user.get_full_name()} na dnes ({today.strftime("%d.%m.%Y")})'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Neplatný JSON formát'})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Chyba při RFID scan: {str(e)}', exc_info=True)
        return JsonResponse({'success': False, 'error': f'Systémová chyba: {str(e)}'})


@csrf_exempt
def rfid_debug(request):
    """Debug endpoint pro testování RFID"""
    if request.method == 'POST':
        data = json.loads(request.body)
        rfid = data.get('rfid_tag', '').strip()
        
        # Získej všechny uživatele s RFID
        all_users = list(User.objects.filter(
            identifikacni_medium__isnull=False
        ).values_list('username', 'first_name', 'last_name', 'identifikacni_medium'))
        
        # Zkus najít přesnou shodu
        user = User.objects.filter(identifikacni_medium=rfid).first()
        
        return JsonResponse({
            'input_rfid': rfid,
            'found': bool(user),
            'user': f"{user.first_name} {user.last_name}" if user else None,
            'all_users_sample': all_users[:10]
        })
    
    return JsonResponse({'error': 'POST only'}, status=405)

@login_required
@obsluha_required
def get_order_detail(request, order_id):
    """Vrátí detail objednávky pro RFID tab"""
    try:
        order = Order.objects.select_related('user').prefetch_related(
            'items__menu_item__jidlo',
            'items__menu_item__druh_jidla'
        ).get(id=order_id)
        
        # Získej aktuální výdejní časy
        now = timezone.localtime(timezone.now()).time()
        current_meal_type_ids = list(MealPickupTime.objects.filter(
            pickup_from__lte=now,
            pickup_to__gte=now
        ).values_list('druh_jidla_id', flat=True))
        
        # 🔥 KONTROLA - JE UŽ OBJEDNÁVKA VYDANÁ?
        already_issued = order.status == 'vydano'
        
        # 🔥 SESKUPENÍ POLOŽEK PODLE NÁZVU JÍDLA
        from collections import defaultdict
        
        grouped_items = defaultdict(lambda: {
            'quantity': 0,
            'type': '',
            'issued': False,
            'issued_times': [],
            'item_ids': []
        })
        
        if already_issued:
            # Seskup UŽ VYDANÉ položky
            for item in order.items.filter(vydano=True):
                key = item.menu_item.jidlo.nazev
                grouped_items[key]['quantity'] += item.quantity
                grouped_items[key]['type'] = item.menu_item.druh_jidla.nazev
                grouped_items[key]['issued'] = True
                grouped_items[key]['item_ids'].append(item.id)
                if item.datum_vydani:
                    grouped_items[key]['issued_times'].append(item.datum_vydani.strftime('%H:%M:%S'))
        else:
            # Seskup položky K VYDÁNÍ
            for item in order.items.filter(vydano=False, menu_item__druh_jidla_id__in=current_meal_type_ids):
                key = item.menu_item.jidlo.nazev
                grouped_items[key]['quantity'] += item.quantity
                grouped_items[key]['type'] = item.menu_item.druh_jidla.nazev
                grouped_items[key]['issued'] = False
                grouped_items[key]['item_ids'].append(item.id)
        
        # Převeď na seznam
        items = []
        for name, data in grouped_items.items():
            items.append({
                'name': name,
                'quantity': data['quantity'],
                'type': data['type'],
                'issued': data['issued'],
                'issued_time': data['issued_times'][0] if data['issued_times'] else None,
                'item_ids': data['item_ids']
            })
        
        # Seřaď podle typu jídla
        items.sort(key=lambda x: x['type'])
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'user_name': order.user.get_full_name(),
            'order_date': order.datum_vydeje.strftime('%d.%m.%Y'),
            'issued_time': order.datum_vydani.strftime('%H:%M:%S') if order.datum_vydani else None,
            'items': items,
            'already_issued': already_issued
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Objednávka nenalezena'}, status=404)

@login_required
@obsluha_required
@require_POST
def issue_single_item(request, item_id):
    """AJAX endpoint pro vydání JEDNÉ položky objednávky"""
    try:
        item = OrderItem.objects.select_related(
            'order__user',
            'menu_item__jidlo',
            'menu_item__druh_jidla'
        ).get(id=item_id)
        
        order = item.order
        
        # Kontrola stavu
        if order.status not in ['objednano', 'zalozena-obsluhou', 'castecne-vydano']:
            return JsonResponse({
                'success': False,
                'error': 'Objednávka nemůže být vydána (nesprávný stav)'
            }, status=400)
        
        # Kontrola, zda už není vydáno
        if item.vydano:
            return JsonResponse({
                'success': False,
                'error': 'Položka už byla vydána'
            }, status=400)
        
        # Kontrola výdejního času
        now = timezone.localtime(timezone.now()).time()
        current_meal_type_ids = list(MealPickupTime.objects.filter(
            pickup_from__lte=now,
            pickup_to__gte=now
        ).values_list('druh_jidla_id', flat=True))
        
        if item.menu_item.druh_jidla_id not in current_meal_type_ids:
            return JsonResponse({
                'success': False,
                'error': 'Tato položka není v aktuálním výdejním čase'
            }, status=400)
        
        # Vytvoř nebo najdi účtenku
        uctenka, created = VydejniUctenka.objects.get_or_create(
            order=order,
            defaults={
                'datum_vydeje': timezone.now(),
                'vydal': request.user,
                'celkova_cena': Decimal('0'),
                'celkova_dotace': Decimal('0')
            }
        )
        
        # Vytvoř položku účtenky
        cena_za_kus = item.cena
        puvodni_cena = item.menu_item.jidlo.cena
        dotace_za_kus = puvodni_cena - cena_za_kus
        
        PolozkaUctenky.objects.create(
            uctenka=uctenka,
            nazev_jidla=item.menu_item.jidlo.nazev,
            druh_jidla=item.menu_item.druh_jidla.nazev,
            mnozstvi=item.quantity,
            cena_za_kus=cena_za_kus,
            dotace_za_kus=dotace_za_kus
        )
        
        # Aktualizuj celkové částky na účtence
        uctenka.celkova_cena += cena_za_kus * item.quantity
        uctenka.celkova_dotace += dotace_za_kus * item.quantity
        uctenka.save()
        
        # Označ položku jako vydanou
        item.vydano = True
        item.datum_vydani = timezone.now()
        item.save()
        
        # Aktualizuj stav objednávky
        if order.items.filter(vydano=False).exists():
            order.status = 'castecne-vydano'
        else:
            order.status = 'vydano'
            if not order.datum_vydani:
                order.datum_vydani = timezone.now()
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Vydáno: {item.quantity}× {item.menu_item.jidlo.nazev}',
            'uctenka_id': uctenka.id,
            'order_complete': order.status == 'vydano'
        })
        
    except OrderItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Položka nenalezena'
        }, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Chyba při vydávání položky {item_id}: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Chyba při vytváření účtenky: {str(e)}'
        }, status=500)


from django.shortcuts import redirect
from django.contrib.auth import login
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def auto_login_kiosk(request):
    """Automatické přihlášení pro výdejní terminál"""
    if request.user.is_authenticated:
        return redirect('vydej_frontend:dashboard')
    
    # Najdi uživatele "obsluha" nebo prvního staff uživatele
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Zkus najít uživatele s username "obsluha" nebo "vydej"
        kiosk_user = User.objects.filter(
            username__in=['obsluha', 'vydej', 'kuchyne'],
            is_staff=True
        ).first()
        
        if not kiosk_user:
            # Fallback - první staff user
            kiosk_user = User.objects.filter(is_staff=True).first()
        
        if kiosk_user:
            # Automaticky přihlas
            login(request, kiosk_user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('vydej_frontend:dashboard')
        else:
            # Žádný vhodný uživatel
            return redirect('admin:login')
            
    except Exception as e:
        print(f"Chyba auto-login: {e}")
        return redirect('admin:login')
