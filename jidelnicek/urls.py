# jidelnicek/urls.py - KOMPLETNÍ
from django.http import JsonResponse
from django.urls import path
from . import views

app_name = 'jidelnicek'  # ✅ TOTO JE KLÍČOVÉ!

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('menuitem-partial/', views.menu_item_partial, name='menuitem_partial'),
    path('my-orders-partial/', views.my_orders_partial, name='my_orders_partial'),
    path('order-create/', views.order_create_view, name='order_create'),
    path('order-delete/', views.order_delete_view, name='order_delete'),
    # jidelnicek/urls.py - PŘIDEJ:
    # ... tvé existující URL
    path('api/user-balance/', views.user_balance_api, name='user_balance_api'),

    
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # AJAX endpoints
    path('ajax/menu-item/<int:menu_item_id>/', views.menu_item_partial, name='menu_item_partial'),
    path('ajax/my-orders/', views.my_orders_partial, name='my_orders_partial'),
    path('ajax/order/create/', views.order_create_view, name='order_create'),
    path('ajax/order/delete/', views.order_delete_view, name='order_delete'),
    path('ajax/balance/', views.user_balance_api, name='user_balance_api'),
]
