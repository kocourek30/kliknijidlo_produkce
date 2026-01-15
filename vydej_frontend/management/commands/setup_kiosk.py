from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Vytvoří uživatele pro výdejní terminál'

    def handle(self, *args, **options):
        username = 'vydej_terminal'
        
        # Zkontroluj, zda už existuje
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Uživatel {username} už existuje'))
            return
        
        # Vytvoř uživatele
        user = User.objects.create_user(
            username=username,
            first_name='Výdejní',
            last_name='Terminál',
            email='vydej@kliknijidlo.cz',
            is_staff=True,
            is_active=True
        )
        
        user.set_password('vydej2026')  # Změň na bezpečnější heslo
        user.save()
        
        self.stdout.write(self.style.SUCCESS(f'✅ Uživatel {username} vytvořen'))
        self.stdout.write(self.style.SUCCESS(f'   Heslo: vydej2026'))
