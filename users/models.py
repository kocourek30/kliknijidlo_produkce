from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils.timezone import now
from django.db.models import Sum, F
from decimal import Decimal
from objednavky.models import OrderItem, Order




class Vklad(models.Model):
    STATUS_CHOICES = [
        ('standard', 'Standardní vklad'),
        ('nulovani_konta', 'Nulování konta'),
    ]
    uzivatel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vklady')
    castka = models.DecimalField(max_digits=10, decimal_places=2)
    datum = models.DateTimeField(default=now)
    poznamka = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='standard', editable=False)

    class Meta:
        verbose_name = "Vklad na konto"
        verbose_name_plural = "Vklady na konta"

    def __str__(self):
        return f"Vklad {self.castka} Kč pro {self.uzivatel} ({self.datum.date()})"


class CustomUser(AbstractUser):
    identifikacni_medium = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_("Identifikační médium")
    )     
    osobni_cislo = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Osobní číslo"))
    alergeny = models.ManyToManyField('jidelnicek.Alergen', blank=True, verbose_name=_("Alergeny"))

    def __str__(self):
        return self.username

    @property
    def aktualni_zustatek(self):
        """✅ SPRÁVNÝ VÝPOČET ZŮSTATKU"""
        try:
            # 1. VKLADY
            soucet_vkladu = self.vklady.aggregate(soucet=Sum('castka'))['soucet'] or Decimal('0')
            
            # 2. DOTACE (pokud model existuje)
            soucet_dotaci = Decimal('0')
            if hasattr(self, 'dotace'):
                soucet_dotaci = self.dotace.aggregate(soucet=Sum('castka'))['soucet'] or Decimal('0')
            
            # 3. OBJEDNÁVKY (SPRÁVNĚ!)
            soucet_objednavek = OrderItem.objects.filter(
                order__user=self,
                order__status__in=['zalozena-obsluhou', 'objednano', 'vydano', 'nevyzvednuto']            ).aggregate(
                total=Sum(F('quantity') * F('cena'))  # ← quantity * cena!
            )['total'] or Decimal('0')
            
            # VÝPOČET
            zustatek = soucet_vkladu + soucet_dotaci - soucet_objednavek
            return zustatek.quantize(Decimal('0.01'))
            
        except Exception as e:
            print(f"⚠️ aktualni_zustatek CHYBA: {e}")
            return Decimal('0')
