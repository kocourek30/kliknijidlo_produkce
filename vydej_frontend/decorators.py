from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages


def obsluha_required(function):
    """
    Dekorátor pro ověření, že uživatel je obsluha (staff nebo superuser)
    """
    def check_obsluha(user):
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return True
        return False
    
    decorator = user_passes_test(
        check_obsluha,
        login_url='/admin/login/',  # Přesměruj na admin login
        redirect_field_name='next'
    )
    
    return decorator(function)
