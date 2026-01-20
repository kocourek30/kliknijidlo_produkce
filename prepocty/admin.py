from django.contrib import admin
from .models import PrepoctyDummy

@admin.register(PrepoctyDummy)
class PrepoctyDummyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_module_permission(self, request):
        return True  # Zobrazí sekci v menu
