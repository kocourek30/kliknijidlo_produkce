from django.db import models

class PrepoctyDummy(models.Model):
    """Prázdný model jen pro zobrazení sekce v admin menu"""
    
    class Meta:
        managed = False  # Nevytváří tabulku v DB
        verbose_name = "Přepočet"
        verbose_name_plural = "Přepočty"
        app_label = 'prepocty'
