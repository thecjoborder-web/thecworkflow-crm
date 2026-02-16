from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class Lead(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('assigned', 'Assigned'),
        ('contacted', 'Contacted'),
        ('awaiting', 'Awaiting List'),  # ✅ ADDED
        ('closed', 'Closed'),
        ('lost', 'Lost'),
    ]

    SOURCE_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('website', 'Website'),
        ('manual', 'Manual'),
    ]

    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=30)

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='manual'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads'
    )

    assigned_at = models.DateTimeField(null=True, blank=True)
    contacted_at = models.DateTimeField(null=True, blank=True)
    awaiting_at = models.DateTimeField(null=True, blank=True)  # ✅ OPTIONAL BUT GOOD
    closed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.status})"


class LeadActivity(models.Model):
    ACTIVITY_TYPES = [
        ('call', 'Call'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('note', 'Note'),
        ('status', 'Status Change'),
    ]

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES
    )

    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.lead.full_name} - {self.activity_type}"


class Note(models.Model):
    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name='notes'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note on {self.lead.full_name}"
