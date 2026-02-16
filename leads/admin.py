from django.contrib import admin
from .models import Lead, LeadActivity, Note


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'assigned_to', 'status', 'created_at')
    list_filter = ('status', 'assigned_to')
    search_fields = ('full_name', 'email', 'phone')


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = ('lead', 'activity_type', 'message', 'created_by', 'created_at')


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('lead', 'user', 'created_at')
