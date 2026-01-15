# objednavky/urls.py - opravené importy
from django.urls import path
from . import views  # Vlastní views (pokud existují)
from jidelnicek import views as jidelnicek_views  # ✅ IMPORT Z JIDELNICEK

urlpatterns = [
    path('order-create/', jidelnicek_views.order_create_view, name='order_create'),
    path('order-delete/', jidelnicek_views.order_delete_view, name='order_delete'),
    # ... další URL
]
