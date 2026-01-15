# frontend/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.rfid_login_page, name='home'),
    path('api/rfid-login/', views.rfid_login_api, name='rfid-login-api'),
    path('logout/', auth_views.LogoutView.as_view(next_page='rfid-login'), name='logout'),
    path('rfid-login/', views.rfid_login_page, name='rfid-login'),
]
