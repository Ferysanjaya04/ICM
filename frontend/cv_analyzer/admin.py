from django.contrib import admin
from .models import AnalysisLog, CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

@admin.register(AnalysisLog)
class AnalysisLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'mode', 'compatibility_score', 'created_at')
    list_filter = ('mode', 'compatibility_level', 'created_at')
    search_fields = ('user__username', 'user__email', 'job_description')
    readonly_fields = ('id', 'created_at', 'results', 'top_roles', 'skill_gap_matched', 'skill_gap_missing', 'roadmap')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False