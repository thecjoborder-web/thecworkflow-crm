from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Project(models.Model):
    """
    Project Model - Stores all project/job information
    from Project Supervisor uploads
    """
    
    PROJECT_STATUSES = [
        ('submitted', '📋 Submitted'),
        ('in_production', '🔄 In Production'),
        ('quality_check', '✅ Quality Check'),
        ('completed', '🎯 Completed'),
        ('ready_for_pickup', '🚚 Ready for Pickup'),
        ('cancelled', '❌ Cancelled'),
    ]

    COLOR_REQUIREMENTS = [
        ('b&w', 'Black & White'),
        ('color', 'Color'),
    ]

    BINDING_TYPES = [
        ('spiral', 'Spiral Binding'),
        ('perfect', 'Perfect Binding'),
        ('comb', 'Comb Binding'),
        ('saddle_stitch', 'Saddle Stitch'),
        ('none', 'No Binding'),
    ]

    # Basic Project Info
    project_title = models.CharField(max_length=255)
    project_description = models.TextField(blank=True, null=True)
    
    # Client Info
    client_name = models.CharField(max_length=255)
    client_contact = models.CharField(max_length=100, blank=True, null=True)
    
    # File Upload
    manuscript_file = models.FileField(
        upload_to='projects/manuscripts/%Y/%m/%d/',
        help_text='Upload project manuscript or main file'
    )
    
    # Project Specifications
    project_date = models.DateField(help_text='Project start date')
    deadline = models.DateField(help_text='Project deadline')
    number_of_copies = models.PositiveIntegerField(default=1)
    
    font_type = models.CharField(
        max_length=100,
        default='Times New Roman',
        help_text='Font to be used (e.g., Arial, Times New Roman, etc.)'
    )
    
    color_requirement = models.CharField(
        max_length=20,
        choices=COLOR_REQUIREMENTS,
        default='b&w'
    )
    
    paper_type = models.CharField(
        max_length=100,
        default='A4',
        help_text='Paper size (A4, A3, Letter, etc.)'
    )
    
    binding_type = models.CharField(
        max_length=20,
        choices=BINDING_TYPES,
        default='perfect'
    )
    
    special_instructions = models.TextField(
        blank=True,
        null=True,
        help_text='Any special requirements or instructions'
    )
    
    budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text='Project budget if applicable'
    )
    
    # Status & Workflow
    status = models.CharField(
        max_length=20,
        choices=PROJECT_STATUSES,
        default='submitted'
    )
    
    # Workflow Control: Can production see this?
    sent_to_production = models.BooleanField(
        default=False,
        help_text='Whether PS sent this to production'
    )
    
    sent_to_production_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When was this sent to production'
    )
    
    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_projects',
        help_text='Project Supervisor who created this'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('view_all_projects', 'Can view all projects'),
            ('send_to_production', 'Can send projects to production'),
        ]
    
    def __str__(self):
        return f"{self.project_title} - {self.client_name}"
    
    @property
    def days_until_deadline(self):
        """Calculate days remaining until deadline"""
        delta = self.deadline - timezone.now().date()
        return delta.days
    
    @property
    def is_overdue(self):
        """Check if project is overdue"""
        return self.days_until_deadline < 0


class ProjectStatusLog(models.Model):
    """
    Activity Log - Tracks ONLY status changes
    Lightweight activity logging for audit trail
    """
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='status_logs'
    )
    
    old_status = models.CharField(
        max_length=20,
        choices=Project.PROJECT_STATUSES
    )
    
    new_status = models.CharField(
        max_length=20,
        choices=Project.PROJECT_STATUSES
    )
    
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='status_changes'
    )
    
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project Status Log'
        verbose_name_plural = 'Project Status Logs'
    
    def __str__(self):
        return f"{self.project.project_title}: {self.old_status} → {self.new_status}"


class ProjectDownloadLog(models.Model):
    """
    Download Log - Track when production downloads projects
    Useful for audit trail
    """
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='downloads'
    )
    
    downloaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='project_downloads'
    )
    
    downloaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-downloaded_at']
    
    def __str__(self):
        return f"{self.project.project_title} - Downloaded by {self.downloaded_by}"


class ProductionNotification(models.Model):
    """
    In-App Notifications for Production activities
    PS sees notifications about their projects
    """
    
    NOTIFICATION_TYPES = [
        ('downloaded', '📥 Project Downloaded'),
        ('status_changed', '🔄 Status Changed'),
        ('production_complete', '✅ Production Complete'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='production_notifications',
        help_text='User who receives this notification'
    )
    
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"[{self.notification_type}] {self.title}"
