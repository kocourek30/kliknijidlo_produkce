# canteen_settings/utils.py

from datetime import timedelta, date
from django.utils import timezone
from .models import OrderClosingTime, OperatingDays, OperatingExceptions


def is_operating_day(check_date):
    """
    Kontrola, zda je daný datum provozní den.
    Priorita: Výjimky > Standardní provozní dny
    """
    print(f"🔍 is_operating_day CHECK: {check_date} ({check_date.strftime('%A')})")
    
    # 1. Kontrola výjimek (má přednost)
    exception = OperatingExceptions.objects.filter(date=check_date).first()
    if exception:
        result = exception.exception_type == 'open'
        print(f"   ✅ Výjimka nalezena: {exception.exception_type} → {result}")
        return result
    
    # 2. Kontrola standardních provozních dnů
    day_of_week = check_date.weekday()
    operating_day = OperatingDays.objects.filter(day_of_week=day_of_week).first()
    
    if operating_day:
        print(f"   ✅ Provozní den nalezen: {operating_day.get_day_of_week_display()} → {operating_day.is_operating}")
        return operating_day.is_operating
    
    # 3. Výchozí: Po-Pá jsou provozní
    result = day_of_week < 5
    print(f"   ⚠️ Žádné nastavení → výchozí (Po-Pá): {result}")
    return result


def get_order_closing_datetime(target_date):
    """
    Vrátí datum a čas uzávěrky pro daný cílový datum vydeje.
    Přeskakuje neprovozní dny a respektuje výjimky.
    """
    print(f"\n🕐 get_order_closing_datetime pro: {target_date}")
    
    try:
        settings = OrderClosingTime.objects.filter(je_aktivni=True).first()
        if not settings:
            print("   ❌ Žádné aktivní nastavení OrderClosingTime!")
            return None
        
        print(f"   ⚙️ Nastavení: {settings.advance_days} dní dopředu do {settings.closing_time}")
        
        # Kontrola, zda je cílový den vůbec provozní
        if not is_operating_day(target_date):
            print(f"   ❌ {target_date} NENÍ provozní den!")
            return None
        
        print(f"   ✅ {target_date} JE provozní den")
        
        # Spočítej uzávěrku s přeskakováním neprovozních dnů
        closing_date = target_date
        days_to_subtract = settings.advance_days
        
        print(f"   🔄 Počítám {days_to_subtract} provozních dnů zpět...")
        
        while days_to_subtract > 0:
            closing_date -= timedelta(days=1)
            
            # Počítej pouze provozní dny
            if is_operating_day(closing_date):
                days_to_subtract -= 1
                print(f"      ✅ {closing_date} je provozní → zbývá {days_to_subtract}")
            else:
                print(f"      ⏭️ {closing_date} přeskočeno (neprovozní)")
        
        # Kombinuj datum a čas
        closing_datetime = timezone.datetime.combine(
            closing_date, 
            settings.closing_time
        )
        closing_datetime = timezone.make_aware(
            closing_datetime, 
            timezone.get_current_timezone()
        )
        
        print(f"   📅 UZÁVĚRKA: {closing_datetime}")
        
        return closing_datetime
        
    except Exception as e:
        print(f"   ❌ CHYBA: {e}")
        import traceback
        traceback.print_exc()
        return None


def is_ordering_allowed(target_date):
    """Kontrola, zda je pro daný datum povoleno objednávání"""
    print(f"\n🚦 is_ordering_allowed pro: {target_date}")
    
    closing_datetime = get_order_closing_datetime(target_date)
    
    if not closing_datetime:
        print("   ❌ Žádná uzávěrka → ZAKÁZÁNO")
        return False
    
    now = timezone.now()
    allowed = now < closing_datetime
    
    print(f"   🕐 Teď: {now}")
    print(f"   📅 Uzávěrka: {closing_datetime}")
    print(f"   ✅ Povoleno: {allowed}")
    
    return allowed
