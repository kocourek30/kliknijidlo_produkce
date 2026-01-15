from django import forms
from .models import Objednavka, PolozkaObjednavky
from jidelnicek.models import Jidelnicek, PolozkaJidelnicku


class ObjednavkaForm(forms.ModelForm):
    jidlo_ids = forms.MultipleChoiceField(
        label="Jídla k objednání",
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[]
    )

    class Meta:
        model = Objednavka
        fields = ['uzivatel', 'datum_objednavky', 'poznamka']
        widgets = {
            'datum_objednavky': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        datum = None

        # Hodnota data buď z POST, nebo instance (editace)
        if 'datum_objednavky' in self.data:
            datum = self.data.get('datum_objednavky')
        elif self.instance.pk:
            datum = self.instance.datum_objednavky

        if datum:
            jidelnicky = Jidelnicek.objects.filter(platnost_od__lte=datum, platnost_do__gte=datum)
            if jidelnicky.exists():
                jidelnicek = jidelnicky.first()
                polozky = PolozkaJidelnicku.objects.filter(jidelnicek=jidelnicek).select_related('jidlo')
                choices = [(str(p.jidlo.id), f'{p.jidlo.nazev} ({p.jidlo.cena} Kč)') for p in polozky]
                self.fields['jidlo_ids'].choices = choices
            else:
                self.fields['jidlo_ids'].choices = []
        else:
            self.fields['jidlo_ids'].choices = []

        # Předvyplnit již existující položky při editaci
        if self.instance.pk:
            existujici = self.instance.polozky.values_list('jidlo_id', flat=True)
            self.initial['jidlo_ids'] = [str(i) for i in existujici]

    def save(self, commit=True):
        objednavka = super().save(commit=False)
        if commit:
            objednavka.save()  # Uložení objednávky, aby měla PK

            # Pro přepsání položek odstraníme staré 
            objednavka.polozky.all().delete()

            jidlo_ids = self.cleaned_data.get('jidlo_ids', [])
            for jidlo_id in jidlo_ids:
                jidlo_obj = PolozkaObjednavky.objects.model.jidlo.field.remote_field.model.objects.get(pk=jidlo_id)
                PolozkaObjednavky.objects.create(objednavka=objednavka, jidlo=jidlo_obj, pocet=1)
        return objednavka
