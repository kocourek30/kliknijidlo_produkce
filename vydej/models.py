from django.db import models
from django.conf import settings
from django.utils import timezone  # ✅ Správný import
from objednavky.models import Order
from django.db import models
from django.conf import settings
from django.utils import timezone
from objednavky.models import Order

class VydejOrder(Order):
    class Meta:
        proxy = True
        app_label = 'vydej'
        verbose_name = "Výdej objednávky"
        verbose_name_plural = "Výdej objednávek"


class PrehledProKuchyni(Order):
    """Proxy model pro přehled objednaných jídel pro kuchyni"""
    class Meta:
        proxy = True
        app_label = 'vydej'
        verbose_name = "Přehled pro kuchyni"
        verbose_name_plural = "Přehled pro kuchyni"




class VydejniUctenka(models.Model):
    """Účtenka pro vydanou objednávku"""
    order = models.OneToOneField(
        'objednavky.Order', 
        on_delete=models.CASCADE, 
        related_name='vydejni_uctenka',
        verbose_name="Objednávka"
    )
    datum_vydeje = models.DateTimeField(
        default=timezone.now,  # ✅ Teď bude fungovat
        verbose_name="Datum a čas výdeje"
    )
    vydal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vydane_objednavky',
        verbose_name="Vydal"
    )
    celkova_cena = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Celková cena"
    )
    celkova_dotace = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Celková dotace"
    )
    poznamka = models.TextField(
        blank=True,
        null=True,
        verbose_name="Poznámka"
    )
    
    class Meta:
        verbose_name = "Výdejní účtenka"
        verbose_name_plural = "Výdejní účtenky"
        ordering = ['-datum_vydeje']
    
    def __str__(self):
        return f"Účtenka #{self.id} - {self.order.user.get_full_name()} ({self.datum_vydeje.strftime('%d.%m.%Y %H:%M')})"


class PolozkaUctenky(models.Model):
    """Položka na účtence"""
    uctenka = models.ForeignKey(
        VydejniUctenka,
        on_delete=models.CASCADE,
        related_name='polozky',
        verbose_name="Účtenka"
    )
    nazev_jidla = models.CharField(max_length=255, verbose_name="Název jídla")
    druh_jidla = models.CharField(max_length=100, verbose_name="Druh jídla")
    mnozstvi = models.PositiveIntegerField(verbose_name="Množství")
    cena_za_kus = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Cena za kus")
    dotace_za_kus = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Dotace za kus"
    )
    
    class Meta:
        verbose_name = "Položka účtenky"
        verbose_name_plural = "Položky účtenky"
    
    def celkova_cena(self):
        return self.mnozstvi * self.cena_za_kus
    
    def celkova_dotace(self):
        return self.mnozstvi * self.dotace_za_kus
    
    def __str__(self):
        return f"{self.nazev_jidla} x {self.mnozstvi}"

from django.db import models
from objednavky.models import Order

class StornovaneObjednavky(Order):
    """Proxy model pro stornované objednávky"""
    class Meta:
        proxy = True
        verbose_name = "Stornovaný účet"
        verbose_name_plural = "Stornované účty"
    
    def __str__(self):
        return f"🗑️ #{self.id} - {self.user.get_full_name()}"
