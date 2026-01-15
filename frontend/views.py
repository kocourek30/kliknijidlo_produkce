# frontend/views.py
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt
from users.models import CustomUser

@csrf_exempt
def rfid_login_api(request):
    print('>>> RFID LOGIN API HIT', request.method)  # debug
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Neplatný JSON'}, status=400)

        rfid = data.get('rfid')
        if not rfid:
            return JsonResponse({'success': False, 'error': 'RFID chybí'}, status=400)

        rfid = rfid.strip()
        user = CustomUser.objects.filter(identifikacni_medium__iexact=rfid).first()
        if user:
            login(request, user)
            return JsonResponse({'success': True, 'username': user.username})
        else:
            return JsonResponse({'success': False, 'error': 'Uživatel nenalezen'}, status=404)
    else:
        return JsonResponse({'success': False, 'error': 'Nepodporovaný HTTP metod'}, status=405)

def rfid_login_page(request):
    if request.user.is_authenticated:
        return redirect('jidelnicek:dashboard')
    return render(request, 'rfid_login.html')
