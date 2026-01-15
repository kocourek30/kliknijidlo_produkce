from django.contrib import admin
from .models import DotacniPolitika, DotaceProJidelniskouSkupinu, Dotace, SkupinoveNastaveni

class DotaceProJidelniskouSkupinuInline(admin.TabularInline):
    model = DotaceProJidelniskouSkupinu
    extra = 1
    autocomplete_fields = ['jidelniskova_skupina']
    fields = ('jidelniskova_skupina', 'procento', 'castka')
    verbose_name = "Dotace pro skupinu jídla"
    verbose_name_plural = "Dotace pro skupiny jídel"

@admin.register(DotacniPolitika)
class DotacniPolitikaAdmin(admin.ModelAdmin):
    # Zobrazí pouze skupinu ve "General" záložce, ostatní pole skryje
    fieldsets = (
        (None, {
            'fields': ('skupina',),
            'description': 'Zvol skupinu uživatelů. Detailní dotace pro druhy jídel nastav dole v sekci "Dotace pro skupiny jídel".',
        }),
    )
    inlines = [DotaceProJidelniskouSkupinuInline]
    list_display = ('skupina',)  # Přehled pouze podle skupiny uživatelů
    # Můžeš doplnit search_fields nebo další filtry dle potřeby

@admin.register(SkupinoveNastaveni)
class SkupinoveNastaveniAdmin(admin.ModelAdmin):
    list_display = ('skupina', 'cerpani_debit', 'debit_limit', 'nutnost_dobit')
    fields = ('skupina', 'cerpani_debit', 'debit_limit', 'nutnost_dobit')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # volitelné: můžeš nastavit či upravit pole podle hodnoty cerpani_debit
        return form
    
admin.site.register(Dotace)


