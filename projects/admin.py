from django.contrib import admin
from .models import Project, ProjectStatusLog, ProjectDownloadLog, ProductionNotification


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_title', 'client_name', 'status', 'sent_to_production', 'deadline', 'created_by', 'created_at')
    list_filter = ('status', 'sent_to_production', 'color_requirement', 'binding_type', 'created_at')
    search_fields = ('project_title', 'client_name', 'project_description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    fieldsets = (
        ('Project Information', {
            'fields': ('project_title', 'project_description', 'client_name', 'client_contact')
        }),
        ('File', {
            'fields': ('manuscript_file',)
        }),
        ('Specifications', {
            'fields': ('number_of_copies', 'font_type', 'color_requirement', 'paper_type', 'binding_type')
        }),
        ('Timeline', {
            'fields': ('project_date', 'deadline')
        }),
        ('Additional', {
            'fields': ('budget', 'special_instructions')
        }),
        ('Workflow', {
            'fields': ('status', 'sent_to_production', 'sent_to_production_at')
        }),
        ('Tracking', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProjectStatusLog)
class ProjectStatusLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('created_at', 'new_status')
    search_fields = ('project__project_title', 'changed_by__username')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        return False  # Cannot manually add logs


@admin.register(ProjectDownloadLog)
class ProjectDownloadLogAdmin(admin.ModelAdmin):
    list_display = ('project', 'downloaded_by', 'downloaded_at')
    list_filter = ('downloaded_at',)
    search_fields = ('project__project_title', 'downloaded_by__username')
    readonly_fields = ('downloaded_at',)
    
    def has_add_permission(self, request):
        return False


@admin.register(ProductionNotification)
class ProductionNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'recipient', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        return False
