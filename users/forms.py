from django import forms
from django.contrib import admin
from dotace.models import SkupinoveNastaveni, CustomUser

class VkladForm(forms.ModelForm):
    class Meta:
        model = Vklad
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Omezit volbu uživatelů, které mají cerpani_debit == False
        allowed_users = CustomUser.objects.filter(
            groups__nastaveni__cerpani_debit=False
        ).distinct()
        self.fields['uzivatel'].queryset = allowed_users

@admin.register(Vklad)
class VkladAdmin(admin.ModelAdmin):
    form = VkladForm
    list_display = ('uzivatel', 'castka', 'datum', 'poznamka')
    search_fields = ('uzivatel__username', 'uzivatel__osobni_cislo')
    list_filter = ('datum',)

    def save_model(self, request, obj, form, change):
        skupina = obj.uzivatel.groups.first()
        if skupina:
            try:
                nastaveni = skupina.nastaveni
                if nastaveni.cerpani_debit:
                    from django.core.exceptions import ValidationError
                    raise ValidationError(f"Uživatel {obj.uzivatel} má nastaveno čerpání debetu, nelze přidat vklad.")
            except SkupinoveNastaveni.DoesNotExist:
                pass
        else:
            raise ValidationError("Uživatel není přiřazen ke skupině, nelze vytvořit vklad.")
        super().save_model(request, obj, form, change)
