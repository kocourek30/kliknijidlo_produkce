from django.urls import path
from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction, models
from django.db.models import Count, Max, Sum  # Min, Q teď nepotřebuješ, klidně je přidej
from django.http import JsonResponse
from decimal import Decimal


from .models import Order, OrderItem
from jidelnicek.models import Jidelnicek, PolozkaJidelnicku
from dotace.models import DotacniPolitika, DotaceProJidelniskouSkupinu


User = get_user_model()


def get_cena_for_user_and_item(user, menu_item):
    skupina = user.groups.first()
    if not skupina:
        return menu_item.jidlo.cena
    politika = getattr(skupina, 'dotacni_politika', None)
    if not politika:
        return menu_item.jidlo.cena
    prepis = DotaceProJidelniskouSkupinu.objects.filter(
        dotacni_politika=politika,
        jidelniskova_skupina=menu_item.druh_jidla
    ).first()
    procento = prepis.procento if prepis and prepis.procento is not None else politika.procento
    castka = prepis.castka if prepis and prepis.castka is not None else politika.castka
    base_price = menu_item.jidlo.cena
    snizena_cena = base_price
    if procento and procento != Decimal('0'):
        snizena_cena = base_price * (Decimal('1') - Decimal(procento) / Decimal(100))
    if castka and castka != Decimal('0'):
        snizena_cena = max(Decimal('0'), snizena_cena - Decimal(castka))
    return snizena_cena.quantize(Decimal('0.01'))


class BulkOrderForm(forms.Form):
    datum_vydeje = forms.DateField(
        label="Datum výdeje",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}, format='%Y-%m-%d'),
        input_formats=['%Y-%m-%d']
    )
    menu_items = forms.ModelMultipleChoiceField(
        queryset=PolozkaJidelnicku.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Položky jídelníčku"
    )
    skupina = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Skupina zákazníků",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    uzivatele = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select'}),
        label="Uživatelé"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        datum = self.data.get('datum_vydeje') or self.initial.get('datum_vydeje')
        if datum:
            from datetime import datetime
            try:
                datum_obj = datetime.strptime(datum, '%Y-%m-%d').date()
                self.fields['menu_items'].queryset = PolozkaJidelnicku.objects.filter(
                    jidelnicek__platnost_od__lte=datum_obj,
                    jidelnicek__platnost_do__gte=datum_obj
                )
            except Exception:
                self.fields['menu_items'].queryset = PolozkaJidelnicku.objects.none()
        else:
            self.fields['menu_items'].queryset = PolozkaJidelnicku.objects.none()

        group_id = self.data.get('skupina') or self.initial.get('skupina')
        if group_id:
            try:
                group_id = int(group_id)
                self.fields['uzivatele'].queryset = User.objects.filter(
                    groups__id=group_id,
                    is_active=True
                )
            except Exception:
                self.fields['uzivatele'].queryset = User.objects.filter(is_active=True)
        else:
            self.fields['uzivatele'].queryset = User.objects.filter(is_active=True)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_list_template = "admin/orders_changelist.html"
    list_display = (
        'created_at_formatted',
        'osobni_cislo',
        'jmeno',
        'prijmeni',
        'formatted_datum',
        'status',
        'total_items',
        'show_items',
    )
    list_display_links = None
    list_filter = ('status', 'datum_vydeje', 'user', 'created_at')
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__osobni_cislo',
    ]
    list_select_related = ('user',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk_create/', self.admin_site.admin_view(self.bulk_create_view), name='bulk_create_orders'),
            path('api/menu_items/', self.admin_site.admin_view(self.menu_items_api), name='menu_items_api'),
            path('api/jidelnicek_days/', self.admin_site.admin_view(self.jidelnicek_days_api), name='jidelnicek_days_api'),
            path('api/zákazníci/', self.admin_site.admin_view(self.users_api), name='users_api'),
        ]
        return custom_urls + urls

    @admin.display(description="Datum vytvoření", ordering='created_at')
    def created_at_formatted(self, obj):
        if getattr(obj, 'created_at', None):
            return obj.created_at.strftime('%d.%m.%Y %H:%M')
        return '-'

    @admin.display(description="Osobní číslo", ordering='user__osobni_cislo')
    def osobni_cislo(self, obj):
        return getattr(obj.user, 'osobni_cislo', '') or '-'

    @admin.display(description="Jméno", ordering='user__first_name')
    def jmeno(self, obj):
        return obj.user.first_name or '-'

    @admin.display(description="Příjmení", ordering='user__last_name')
    def prijmeni(self, obj):
        return obj.user.last_name or '-'

    @admin.display(description="Datum výdeje", ordering='datum_vydeje')
    def formatted_datum(self, obj):
        return obj.datum_vydeje.strftime('%d.%m.%Y')

    @admin.display(description="Počet položek", ordering='items__quantity')
    def total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())
    total_items.short_description = "Počet"

    @admin.display(description="Položky objednávky a cena")
    def show_items(self, obj):
        return ", ".join(
            f"{item.menu_item.jidlo.nazev} x{item.quantity} ({item.cena} Kč)"
            for item in obj.items.select_related('menu_item__jidlo')[:3]
        )

    @admin.display(description="Zákazník")
    def user_info(self, obj):
        user = obj.user
        return f"{getattr(user, 'osobni_cislo', '') or ''} - {user.first_name} {user.last_name}"

    def bulk_create_view(self, request):
        from django.shortcuts import render, redirect
        form = BulkOrderForm(request.POST or None)
        error_users = []
        if request.method == "POST" and form.is_valid():
            datum_vydeje = form.cleaned_data['datum_vydeje']
            menu_items = form.cleaned_data['menu_items']
            uzivatele = form.cleaned_data['uzivatele']

            with transaction.atomic():
                for uzivatel in uzivatele:
                    skupina = uzivatel.groups.first()
                    nastaveni = getattr(skupina, 'nastaveni', None)
                    cena_objednavky = sum(
                        get_cena_for_user_and_item(uzivatel, item) for item in menu_items
                    )
                    zustatek = uzivatel.aktualni_zustatek
                    povoleno = True

                    if nastaveni:
                        if nastaveni.nutnost_dobit and (zustatek - cena_objednavky < 0):
                            povoleno = False
                        if nastaveni.cerpani_debit and (
                            zustatek - cena_objednavky < float(nastaveni.debit_limit)
                        ):
                            povoleno = False

                    if not povoleno:
                        error_users.append(
                            f"{uzivatel.osobni_cislo or uzivatel.username} "
                            f"({uzivatel.first_name} {uzivatel.last_name})"
                        )
                        continue

                    order, created = Order.objects.get_or_create(
                        user=uzivatel,
                        datum_vydeje=datum_vydeje,
                        defaults={'status': 'zalozena-obsluhou'}
                    )
                    if not created:
                        order.status = 'zalozena-obsluhou'
                        order.save()
                    order.items.all().delete()
                    items_to_create = [
                        OrderItem(
                            order=order,
                            menu_item=item,
                            quantity=1,
                            cena=get_cena_for_user_and_item(uzivatel, item)
                        )
                        for item in menu_items
                    ]
                    OrderItem.objects.bulk_create(items_to_create)

            if error_users:
                self.message_user(
                    request,
                    "Některé objednávky nebyly vytvořeny kvůli nedostatku zůstatku nebo limitu: "
                    + ", ".join(error_users),
                    level='error'
                )
            else:
                self.message_user(
                    request,
                    f"Vytvořeno {len(uzivatele) - len(error_users)} objednávek na datum {datum_vydeje}."
                )
            return redirect('..')

        context = dict(
            self.admin_site.each_context(request),
            form=form,
        )
        return render(request, "admin/bulk_create_orders.html", context)

    def users_api(self, request):
        query = request.GET.get('q', '').strip()
        skupina = request.GET.get('skupina', '').strip()
        users = User.objects.filter(is_active=True)
        if skupina:
            try:
                group_id = int(skupina)
                users = users.filter(groups__id=group_id)
            except ValueError:
                pass
        if query and len(query) > 0:
            users = users.filter(
                models.Q(username__icontains=query) |
                models.Q(first_name__icontains=query) |
                models.Q(last_name__icontains=query) |
                models.Q(osobni_cislo__icontains=query)
            )
        data = [
            {
                "id": u.id,
                "osobni_cislo": getattr(u, 'osobni_cislo', ''),
                "name": f"{u.first_name} {u.last_name}",
                "username": u.username,
            }
            for u in users.order_by('last_name', 'first_name')
        ]
        return JsonResponse(data, safe=False)

    def menu_items_api(self, request):
        datum = request.GET.get('datum')
        if not datum:
            return JsonResponse([], safe=False)
        from datetime import datetime
        try:
            datum_obj = datetime.strptime(datum, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse([], safe=False)
        items = PolozkaJidelnicku.objects.filter(
            jidelnicek__platnost_od__lte=datum_obj,
            jidelnicek__platnost_do__gte=datum_obj
        ).values('id', 'jidlo__nazev')
        data = [{'id': item['id'], 'nazev': item['jidlo__nazev']} for item in items]
        return JsonResponse(data, safe=False)

    def jidelnicek_days_api(self, request):
        from datetime import timedelta
        days_set = set()
        jidelnicky = Jidelnicek.objects.all()
        for j in jidelnicky:
            current = j.platnost_od
            while current <= j.platnost_do:
                days_set.add(current.strftime('%Y-%m-%d'))
                current += timedelta(days=1)
        days_list = sorted(days_set)
        return JsonResponse(days_list, safe=False)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Detailní list položek objednávek:
    - osobní číslo, jméno, příjmení (přes order.user)
    - datum výdeje
    - druh jídla
    - název jídla
    - počet ks, cena, celkem
    """
    list_display = [
        'datum_vydeje',
        'osobni_cislo',
        'jmeno',
        'prijmeni',
        'druh_jidla',
        'jidlo_nazev',
        'quantity',
        'cena',
        'total_price',
    ]
    list_filter = ['order__datum_vydeje', 'order__user', 'order__status', 'menu_item__druh_jidla']
    search_fields = [
        'order__user__username',
        'order__user__first_name',
        'order__user__last_name',
        'order__user__osobni_cislo',
        'menu_item__jidlo__nazev',
    ]
    readonly_fields = ['total_price']
    list_select_related = ('order__user', 'menu_item__jidlo', 'menu_item__druh_jidla')

    @admin.display(description="Datum výdeje", ordering='order__datum_vydeje')
    def datum_vydeje(self, obj):
        return obj.order.datum_vydeje.strftime('%d.%m.%Y')

    @admin.display(description="Osobní číslo", ordering='order__user__osobni_cislo')
    def osobni_cislo(self, obj):
        return getattr(obj.order.user, 'osobni_cislo', '') or '-'

    @admin.display(description="Jméno", ordering='order__user__first_name')
    def jmeno(self, obj):
        return obj.order.user.first_name or '-'

    @admin.display(description="Příjmení", ordering='order__user__last_name')
    def prijmeni(self, obj):
        return obj.order.user.last_name or '-'

    @admin.display(description="Druh jídla", ordering='menu_item__druh_jidla__nazev')
    def druh_jidla(self, obj):
        return getattr(obj.menu_item.druh_jidla, 'nazev', str(obj.menu_item.druh_jidla))

    @admin.display(description="Jídlo", ordering='menu_item__jidlo__nazev')
    def jidlo_nazev(self, obj):
        return obj.menu_item.jidlo.nazev

    def total_price(self, obj):
        return f"{obj.quantity * obj.cena} Kč"
    total_price.short_description = "Celkem"


class OrderSummaryAdmin(admin.ModelAdmin):
    """
    Souhrn: jídelníček vs. počet objednaných jídel
    pro nejbližší den, na který jsou objednávky uzavřené.
    """
    change_list_template = "admin/order_summary_changelist.html"

    CLOSED_STATUSES = ["uzavrena", "uzavrena-objednavani"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return OrderItem.objects.none()

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import render

        closed_orders = Order.objects.filter(status__in=self.CLOSED_STATUSES)
        nearest_date = closed_orders.aggregate(d=Max('datum_vydeje'))['d']

        jidelnicek_items = []
        chart_labels = []
        chart_values = []

        if nearest_date:
            jidelnicek_items_qs = PolozkaJidelnicku.objects.filter(
                jidelnicek__platnost_od__lte=nearest_date,
                jidelnicek__platnost_do__gte=nearest_date
            ).select_related('jidlo', 'druh_jidla')

            objednavky_agg = (
                OrderItem.objects
                .filter(
                    order__datum_vydeje=nearest_date,
                    order__status__in=self.CLOSED_STATUSES
                )
                .values('menu_item_id')
                .annotate(pocet_kusu=Sum('quantity'))
            )

            objednavky_map = {
                row['menu_item_id']: row['pocet_kusu'] for row in objednavky_agg
            }

            for item in jidelnicek_items_qs:
                pocet = objednavky_map.get(item.id, 0) or 0
                jidelnicek_items.append({
                    "druh_jidla": getattr(item.druh_jidla, "nazev", str(item.druh_jidla)),
                    "jidlo": item.jidlo.nazev,
                    "pocet_kusu": pocet,
                })
                chart_labels.append(item.jidlo.nazev)
                chart_values.append(pocet)

        context = {
            **self.admin_site.each_context(request),
            "summary_date": nearest_date,
            "jidelnicek_items": jidelnicek_items,
            "chart_labels": chart_labels,
            "chart_values": chart_values,
            "title": "Souhrn objednávek vs. jídelníček",
        }
        return render(request, self.change_list_template, context)



