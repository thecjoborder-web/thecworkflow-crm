from django.conf import settings
from django.db import models
from django.utils import timezone

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


class JobOrder(models.Model):
    """
    Job Order Model - Stores sales job orders before sending to project management
    """

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent_to_project', 'Sent to Project'),
        ('closed', 'Closed'),
    ]

    PRODUCT_SERVICE_CHOICES = [
        ('book_printing', 'Book Printing'),
        ('complete_publishing', 'Complete Publishing'),
        ('isbn_procurement', 'ISBN Procurement'),
        ('poster_printing', 'Poster Printing'),
        ('flyer_printing', 'Flyer Printing'),
        ('business_card', 'Business Card'),
        ('shirt_printing', 'Shirt Printing'),
        ('roll_up_banner', 'Roll Up Banner'),
        ('program_booklet', 'Program Booklet'),
        ('other_service', 'Other Service'),
    ]

    SIZE_CHOICES = [
        ('a4', 'A4'),
        ('a3', 'A3'),
        ('letter', 'Letter'),
        ('custom', 'Custom'),
    ]

    COLOR_CHOICES = [
        ('b&w', 'Black & White'),
        ('color', 'Color'),
        ('cmyk', 'CMYK'),
    ]

    PAPER_TYPE_CHOICES = [
        ('standard', 'Standard'),
        ('glossy', 'Glossy'),
        ('matte', 'Matte'),
        ('cardstock', 'Cardstock'),
    ]

    BINDING_CHOICES = [
        ('spiral', 'Spiral'),
        ('perfect', 'Perfect'),
        ('comb', 'Comb'),
        ('saddle_stitch', 'Saddle Stitch'),
        ('none', 'None'),
    ]

    LAMINATION_CHOICES = [
        ('none', 'None'),
        ('glossy', 'Glossy'),
        ('matte', 'Matte'),
    ]

    DESIGN_NEEDED_CHOICES = [
        ('cover_inner', 'Yes - Cover & Inner'),
        ('cover_only', 'Yes - Cover Only'),
        ('no', 'No - I Have Design'),
    ]

    DESIGN_CONCEPTS_CHOICES = [
        ('1', '1 Concept'),
        ('2', '2 Concepts'),
        ('3', '3 Concepts'),
    ]

    DESIGN_STYLE_CHOICES = [
        ('modern', 'Modern'),
        ('classic', 'Classic'),
        ('minimal', 'Minimal'),
        ('custom', 'Custom'),
    ]

    LINE_SPACING_CHOICES = [
        ('single', 'Single'),
        ('1.5', '1.5'),
        ('double', 'Double'),
    ]

    DELIVERY_MODE_CHOICES = [
        ('pickup', 'Pickup'),
        ('delivery', 'Delivery'),
        ('shipping', 'Shipping'),
    ]

    URGENCY_CHOICES = [
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('rush', 'Rush'),
    ]

    SOURCE_CHOICES = [
        ('walk_in', 'Walk In'),
        ('phone', 'Phone'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('website', 'Website'),
        ('referral', 'Referral'),
    ]

    # Order Info
    order_no = models.CharField(max_length=20, unique=True, help_text='Auto-generated order number')
    date = models.DateField(default=timezone.now, help_text='Order date')

    # Customer Info
    customer_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    delivery_address = models.TextField(blank=True, null=True)

    # Product/Service
    product_service = models.CharField(
        max_length=20,
        choices=PRODUCT_SERVICE_CHOICES,
        default='book_printing'
    )

    # Job Specifications
    title_description = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    size_dimension = models.CharField(
        max_length=20,
        choices=SIZE_CHOICES,
        default='a4'
    )
    color_mode = models.CharField(
        max_length=20,
        choices=COLOR_CHOICES,
        default='b&w'
    )
    paper_type = models.CharField(
        max_length=20,
        choices=PAPER_TYPE_CHOICES,
        default='standard'
    )
    paper_weight = models.CharField(max_length=20, blank=True, null=True, help_text='e.g., 80gsm, 100gsm')
    binding = models.CharField(
        max_length=20,
        choices=BINDING_CHOICES,
        default='none'
    )
    lamination = models.CharField(
        max_length=20,
        choices=LAMINATION_CHOICES,
        default='none'
    )
    total_pages = models.PositiveIntegerField(blank=True, null=True)

    # Design Requirements
    design_needed = models.CharField(
        max_length=20,
        choices=DESIGN_NEEDED_CHOICES,
        default='no'
    )
    design_concepts = models.CharField(
        max_length=20,
        choices=DESIGN_CONCEPTS_CHOICES,
        blank=True, null=True
    )
    design_style = models.CharField(
        max_length=20,
        choices=DESIGN_STYLE_CHOICES,
        blank=True, null=True
    )
    font_type = models.CharField(max_length=100, blank=True, null=True)
    font_size = models.CharField(max_length=20, blank=True, null=True)
    line_spacing = models.CharField(
        max_length=20,
        choices=LINE_SPACING_CHOICES,
        blank=True, null=True
    )
    isbn_required = models.BooleanField(default=False)

    # Additional Specifications
    special_instructions = models.TextField(blank=True, null=True)

    # Delivery & Urgency
    delivery_mode = models.CharField(
        max_length=20,
        choices=DELIVERY_MODE_CHOICES,
        default='pickup'
    )
    expected_delivery_date = models.DateField(blank=True, null=True)
    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='normal'
    )
    source_of_deal = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='walk_in'
    )

    # Pricing & Payment
    estimated_budget = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    agreed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    part_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )
    balance_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00
    )

    # File Uploads
    invoice_file = models.FileField(
        upload_to='job_orders/invoices/%Y/%m/%d/',
        blank=True, null=True
    )
    manuscript_file = models.FileField(
        upload_to='job_orders/manuscripts/%Y/%m/%d/',
        blank=True, null=True
    )

    # Status & Workflow
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Creator
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_job_orders'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_no} - {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.order_no:
            # Auto-generate order number: TP-2025-XXXX
            import random
            year = timezone.now().year
            random_num = str(random.randint(1000, 9999))
            self.order_no = f"TP-{year}-{random_num}"
            # Ensure uniqueness
            while JobOrder.objects.filter(order_no=self.order_no).exists():
                random_num = str(random.randint(1000, 9999))
                self.order_no = f"TP-{year}-{random_num}"
        super().save(*args, **kwargs)
