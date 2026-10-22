"""
printing/models.py
==================
Core database models for SmartPrintKiosk:
1. Shop: Represents the kiosk/print shop location with QR code generation.
2. PricingSetting: Shop-specific pricing rules (B&W rate, color rate, duplex discount).
3. Document: Stores customer uploaded files (PDF, Word, Images), metadata, and page counts.
4. PrintOrder: Customer order containing print preferences, price calculation, and status.
5. PrintJob: Operational queue entry for simulated or physical printing.
"""

import os
import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings


def document_upload_path(instance, filename):
    """
    Generates a secure, unguessable storage path for uploaded documents.
    Format: media/uploads/YYYY/MM/DD/<uuid>_<safe_filename>
    This prevents path traversal and filename collisions.
    """
    ext = os.path.splitext(filename)[1].lower()
    safe_id = uuid.uuid4().hex[:12]
    today = timezone.now()
    return f"uploads/{today.year}/{today.month:02d}/{today.day:02d}/{safe_id}{ext}"


class Shop(models.Model):
    """
    Represents a printing shop or kiosk terminal.
    Contains counter identification and the generated public ordering QR code.
    """
    name = models.CharField(max_length=150, default="SmartPrint Campus Kiosk")
    slug = models.SlugField(max_length=60, unique=True, default="default-kiosk")
    address = models.TextField(default="Campus Library Ground Floor, Counter 1")
    contact_number = models.CharField(max_length=20, default="+91 98765 43210")
    contact_email = models.EmailField(default="support@smartprintkiosk.local")
    is_active = models.BooleanField(default=True)
    qr_code_image = models.ImageField(upload_to="qrcodes/", blank=True, null=True)
    configured_printer_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Name of physical Windows printer for print worker (optional)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shop / Kiosk"
        verbose_name_plural = "Shops & Kiosks"

    def __str__(self):
        return f"{self.name} ({self.slug})"

    @classmethod
    def get_default_shop(cls):
        """Returns the primary shop, creating it if it doesn't already exist."""
        shop, created = cls.objects.get_or_create(
            slug="default-kiosk",
            defaults={
                'name': "SmartPrint Campus Kiosk",
                'address': "Main Campus, Building A, Print Station 1",
                'contact_number': "+91 98765 43210",
                'contact_email': "kiosk@smartprint.local",
                'is_active': True,
            }
        )
        # Ensure it has pricing settings configured
        if not hasattr(shop, 'pricing'):
            PricingSetting.objects.get_or_create(shop=shop)
        return shop

    def generate_qr_code(self, base_url="http://127.0.0.1:8000"):
        """
        Generates and saves the QR code linking to this shop's public ordering page.
        """
        import qrcode
        from django.core.files.base import ContentFile
        from io import BytesIO

        target_url = f"{base_url.rstrip('/')}/?shop={self.slug}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(target_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0d6efd", back_color="#ffffff")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"shop_qr_{self.slug}.png"
        self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=True)


class PricingSetting(models.Model):
    """
    Stores configurable per-page printing rates and duplex policies for a Shop.
    All monetary amounts are stored as Decimals (never floating-point).
    """
    shop = models.OneToOneField(
        Shop,
        on_delete=models.CASCADE,
        related_name='pricing',
        help_text="The shop this pricing rule belongs to."
    )
    bw_rate_per_page = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('2.00'),
        validators=[MinValueValidator(Decimal('0.10'))],
        verbose_name="B&W Rate per Page (₹)"
    )
    color_rate_per_page = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('10.00'),
        validators=[MinValueValidator(Decimal('0.50'))],
        verbose_name="Colour Rate per Page (₹)"
    )
    duplex_discount_per_sheet = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Duplex Sheet Discount (₹)",
        help_text="Discount applied per physical sheet saved in double-sided mode."
    )
    max_copies_limit = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        verbose_name="Max Allowed Copies"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pricing Setting"
        verbose_name_plural = "Pricing Settings"

    def __str__(self):
        return f"Pricing for {self.shop.name}: B&W ₹{self.bw_rate_per_page}, Color ₹{self.color_rate_per_page}"


class Document(models.Model):
    """
    Represents an uploaded document file before or during printing.
    Tracks original name, stored path, detected page count, and validation status.
    """
    TYPE_PDF = 'PDF'
    TYPE_DOCX = 'DOCX'
    TYPE_DOC = 'DOC'
    TYPE_IMAGE = 'IMAGE'

    TYPE_CHOICES = [
        (TYPE_PDF, 'PDF Document (.pdf)'),
        (TYPE_DOCX, 'Microsoft Word (.docx)'),
        (TYPE_DOC, 'Microsoft Word Legacy (.doc)'),
        (TYPE_IMAGE, 'Image File (.jpg, .jpeg, .png)'),
    ]

    PAGE_STATUS_DETECTED = 'DETECTED'
    PAGE_STATUS_DEFAULT = 'DEFAULT'
    PAGE_STATUS_ESTIMATED = 'ESTIMATED'

    PAGE_STATUS_CHOICES = [
        (PAGE_STATUS_DETECTED, 'Accurately Detected'),
        (PAGE_STATUS_DEFAULT, 'Default (1 Page)'),
        (PAGE_STATUS_ESTIMATED, 'Estimated'),
    ]

    upload_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text="Secret unguessable token used by guest customer to reference their upload."
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        help_text="Owner user if logged in; null for guest uploads."
    )
    original_filename = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    file_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    file_size = models.PositiveIntegerField(help_text="File size in bytes.")
    page_count = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Total printable pages determined by server-side inspection."
    )
    page_count_status = models.CharField(
        max_length=20,
        choices=PAGE_STATUS_CHOICES,
        default=PAGE_STATUS_DEFAULT
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = "Uploaded Document"
        verbose_name_plural = "Uploaded Documents"

    def __str__(self):
        return f"{self.original_filename} ({self.file_type}, {self.page_count} pages)"

    @property
    def formatted_file_size(self):
        """Returns human-readable file size (KB or MB)."""
        kb = self.file_size / 1024
        if kb < 1024:
            return f"{kb:.1f} KB"
        mb = kb / 1024
        return f"{mb:.2f} MB"


class PrintOrder(models.Model):
    """
    Main order entity. Connects Customer, Shop, Document, and Print Options.
    Calculates and protects the final price and coordinates state transitions.
    """
    # Color Mode Choices
    COLOR_BW = 'BW'
    COLOR_FULL = 'COLOR'
    COLOR_CHOICES = [
        (COLOR_BW, 'Black & White (Monochrome)'),
        (COLOR_FULL, 'Full Colour'),
    ]

    # Page Selection Choices
    PAGE_MODE_ALL = 'ALL'
    PAGE_MODE_CUSTOM = 'CUSTOM'
    PAGE_MODE_CHOICES = [
        (PAGE_MODE_ALL, 'All Pages'),
        (PAGE_MODE_CUSTOM, 'Custom Page Range (e.g. 1-3, 5)'),
    ]

    # Duplex Choices
    DUPLEX_SINGLE = 'SINGLE'
    DUPLEX_DOUBLE = 'DOUBLE'
    DUPLEX_CHOICES = [
        (DUPLEX_SINGLE, 'Single-Sided (One side per sheet)'),
        (DUPLEX_DOUBLE, 'Double-Sided / Duplex (Both sides)'),
    ]

    # Orientation Choices
    ORIENT_PORTRAIT = 'PORTRAIT'
    ORIENT_LANDSCAPE = 'LANDSCAPE'
    ORIENT_CHOICES = [
        (ORIENT_PORTRAIT, 'Portrait'),
        (ORIENT_LANDSCAPE, 'Landscape'),
    ]

    # Order Lifecycle Statuses
    STATUS_AWAITING_PAYMENT = 'AWAITING_PAYMENT'
    STATUS_PAID = 'PAID'
    STATUS_QUEUED = 'QUEUED'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_READY = 'READY'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'
    STATUS_CANCELLED = 'CANCELLED'

    STATUS_CHOICES = [
        (STATUS_AWAITING_PAYMENT, 'Awaiting Payment'),
        (STATUS_PAID, 'Payment Received - Authorized'),
        (STATUS_QUEUED, 'Queued for Printing'),
        (STATUS_PROCESSING, 'Printing in Progress'),
        (STATUS_READY, 'Ready for Collection'),
        (STATUS_COMPLETED, 'Completed / Picked Up'),
        (STATUS_FAILED, 'Print Job Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    # Payment Status
    PAYMENT_PENDING = 'PENDING'
    PAYMENT_COMPLETED = 'COMPLETED'
    PAYMENT_FAILED = 'FAILED'
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_PENDING, 'Pending'),
        (PAYMENT_COMPLETED, 'Completed / Verified'),
        (PAYMENT_FAILED, 'Failed'),
    ]

    # Public Reference and Secure Tracking
    order_number = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Public order reference e.g. SPK-20261022-A1B2C3"
    )
    guest_tracking_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="Cryptographically secure token for guest order tracking."
    )

    # Ownership & Associations
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='print_orders',
        help_text="Null for guest customer orders."
    )
    customer_name = models.CharField(max_length=100, blank=True, default="Guest Customer")
    customer_phone = models.CharField(max_length=20, blank=True, default="")
    shop = models.ForeignKey(
        Shop,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.PROTECT,
        related_name='orders'
    )

    # Print Preferences
    color_mode = models.CharField(max_length=10, choices=COLOR_CHOICES, default=COLOR_BW)
    copies = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    page_selection_mode = models.CharField(max_length=10, choices=PAGE_MODE_CHOICES, default=PAGE_MODE_ALL)
    custom_page_range = models.CharField(
        max_length=100,
        blank=True,
        help_text="Specific pages requested e.g. '1-3, 5, 8'"
    )
    calculated_pages_per_copy = models.PositiveIntegerField(
        default=1,
        help_text="Number of document pages chosen per copy."
    )
    paper_size = models.CharField(max_length=10, default='A4')
    duplex_mode = models.CharField(max_length=10, choices=DUPLEX_CHOICES, default=DUPLEX_SINGLE)
    orientation = models.CharField(max_length=15, choices=ORIENT_CHOICES, default=ORIENT_PORTRAIT)

    # Financial Breakdown (All in INR - Decimal)
    rate_applied = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Per-page rate applied at the moment the order was placed."
    )
    total_pages_printed = models.PositiveIntegerField(
        help_text="Total printed sides (calculated_pages_per_copy * copies)."
    )
    subtotal_amount = models.DecimalField(max_digits=8, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Order Lifecycle State
    order_status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default=STATUS_AWAITING_PAYMENT,
        db_index=True
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_PENDING,
        db_index=True
    )

    # Tracking QR Code
    tracking_qr_code = models.ImageField(upload_to="qrcodes/", blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Print Order"
        verbose_name_plural = "Print Orders"

    def __str__(self):
        return f"Order #{self.order_number} - ₹{self.total_amount} ({self.get_order_status_display()})"

    @classmethod
    def generate_unique_order_number(cls):
        """Generates a human-friendly unique order ID: SPK-YYYYMMDD-XXXX."""
        today_str = timezone.now().strftime("%Y%m%d")
        rand_hex = uuid.uuid4().hex[:6].upper()
        candidate = f"SPK-{today_str}-{rand_hex}"
        while cls.objects.filter(order_number=candidate).exists():
            rand_hex = uuid.uuid4().hex[:6].upper()
            candidate = f"SPK-{today_str}-{rand_hex}"
        return candidate

    def can_transition_to(self, new_status):
        """
        Validates business logic status transitions.
        Prevents illegal transitions (e.g., Awaiting Payment directly to Completed).
        """
        valid_transitions = {
            self.STATUS_AWAITING_PAYMENT: [self.STATUS_PAID, self.STATUS_CANCELLED],
            self.STATUS_PAID: [self.STATUS_QUEUED, self.STATUS_PROCESSING, self.STATUS_CANCELLED],
            self.STATUS_QUEUED: [self.STATUS_PROCESSING, self.STATUS_CANCELLED],
            self.STATUS_PROCESSING: [self.STATUS_READY, self.STATUS_FAILED],
            self.STATUS_READY: [self.STATUS_COMPLETED],
            self.STATUS_FAILED: [self.STATUS_QUEUED, self.STATUS_CANCELLED],  # allows retry
            self.STATUS_COMPLETED: [],  # terminal
            self.STATUS_CANCELLED: [],  # terminal
        }
        return new_status in valid_transitions.get(self.order_status, [])

    def generate_tracking_qr(self, base_url="http://127.0.0.1:8000"):
        """Generates a QR code pointing directly to the order tracking URL."""
        import qrcode
        from django.core.files.base import ContentFile
        from io import BytesIO

        tracking_url = f"{base_url.rstrip('/')}/track/{self.guest_tracking_token}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=3,
        )
        qr.add_data(tracking_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#198754", back_color="#ffffff")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"order_qr_{self.order_number}.png"
        self.tracking_qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)


class PrintJob(models.Model):
    """
    Queue item representing the physical or simulated printing execution for an authorized order.
    Enforces idempotency and retry accounting.
    """
    JOB_QUEUED = 'QUEUED'
    JOB_PROCESSING = 'PROCESSING'
    JOB_PRINTED = 'PRINTED'
    JOB_FAILED = 'FAILED'

    JOB_STATUS_CHOICES = [
        (JOB_QUEUED, 'Queued in Buffer'),
        (JOB_PROCESSING, 'Sending to Printer'),
        (JOB_PRINTED, 'Successfully Printed'),
        (JOB_FAILED, 'Printing Failed'),
    ]

    order = models.OneToOneField(
        PrintOrder,
        on_delete=models.CASCADE,
        related_name='print_job',
        help_text="Order attached to this print job."
    )
    job_status = models.CharField(
        max_length=20,
        choices=JOB_STATUS_CHOICES,
        default=JOB_QUEUED,
        db_index=True
    )
    attempt_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of processing or print attempts."
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Details of any hardware or conversion error."
    )
    printed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Staff operator who supervised or processed the job."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Print Job Queue Item"
        verbose_name_plural = "Print Job Queue Items"

    def __str__(self):
        return f"PrintJob #{self.id} for Order {self.order.order_number} ({self.get_job_status_display()})"
