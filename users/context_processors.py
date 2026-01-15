from decimal import Decimal
from .models import CustomUser

def user_balance(request):
    if request.user.is_authenticated:
        return {'user_balance': request.user.aktualni_zustatek}
    return {'user_balance': Decimal('0')}  # ✅ IMPORT PŘIDÁN!
