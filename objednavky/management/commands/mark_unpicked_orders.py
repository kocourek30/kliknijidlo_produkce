from django.core.management.base import BaseCommand
from django.utils import timezone
from objednavky.models import Order
from datetime import date


class Command(BaseCommand):
    help = 'Označí nevyzvednute objednávky starší nebo dnešní ve stavu objednano/zalozena-obsluhou'

    def handle(self, *args, **options):
        today = date.today()
        
        # Najdi všechny objednávky <= dnešní datum ve stavu objednano nebo zalozena-obsluhou
        orders_to_mark = Order.objects.filter(
            datum_vydeje__lte=today,
            status__in=['objednano', 'zalozena-obsluhou']
        )
        
        count = orders_to_mark.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('✅ Žádné nevyzvednuté objednávky k označení.')
            )
            return
        
        # Označ je jako nevyzvednuto
        orders_to_mark.update(
            status='nevyzvednuto',
            updated_at=timezone.now()
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Označeno {count} objednávek jako nevyzvednuto.'
            )
        )
