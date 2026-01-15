from django.contrib import admin
from django.urls import include, path
from users import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('frontend.urls')),  # zůstává, pokud chceš homepage/login atd.
    path('accounts/', include('django.contrib.auth.urls')),
    path('profile/', views.user_profile_view, name='user-profile'),
    path('jidelnicek/', include('jidelnicek.urls')), 
    path('users/', include('users.urls', namespace='users')),
    path('vydej/', include('vydej_frontend.urls')),  
    
    
    
]

