"""
payments/models.py
==================
Payment transaction tracking and ledger for SmartPrintKiosk.

Why this is needed:
1. Records every payment attempt, status, and verification timestamp.
2. Clearly flagged as DEMO PAYMENT for prototype / college project safety.
3. Structured cleanly so a real payment gateway (Razorpay, Stripe, Paytm) can be plugged in.
4. Security: Does NOT store UPI PINs, card numbers, CVVs, or passwords.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from printing.models import PrintOrder


class Payment(models.Model):
    """
    Financial transaction record associated with a PrintOrder.
    Enforces idempotency and tracks payment lifecycle.
    """
    MODE_DEMO_UPI = 'DEMO_UPI'
    MODE_DEMO_CARD = 'DEMO_CARD'
    MODE_DEMO_NETBANKING = 'DEMO_NETBANKING'
    MODE_DEMO_CASH = 'DEMO_CASH'

    PAYMENT_MODE_CHOICES = [
        (MODE_DEMO_UPI, 'Demo UPI (GPay / PhonePe / Paytm QR)'),
        (MODE_DEMO_CARD, 'Demo Card Payment (Test Simulator)'),
        (MODE_DEMO_NETBANKING, 'Demo Net Banking (Test Bank)'),
        (MODE_DEMO_CASH, 'Demo Pay at Counter (Cash on Collection)'),
    ]

    STATUS_PENDING = 'PENDING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Payment Pending Verification'),
        (STATUS_SUCCESS, 'Payment Successful & Verified'),
        (STATUS_FAILED, 'Payment Failed / Declined'),
    ]

    order = models.OneToOneField(
        PrintOrder,
        on_delete=models.CASCADE,
        related_name='payment',
        help_text="The print order this payment settles."
    )
    transaction_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique reference e.g. TXN-DEMO-20261022-ABC123"
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Amount in INR charged for this transaction."
    )
    payment_mode = models.CharField(
        max_length=25,
        choices=PAYMENT_MODE_CHOICES,
        default=MODE_DEMO_UPI
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True
    )
    demo_disclaimer = models.CharField(
        max_length=150,
        default="DEMO PAYMENT — NO REAL MONEY IS CHARGED"
    )
    gateway_response_code = models.CharField(max_length=50, blank=True, default="TEST_OK")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Payment Record"
        verbose_name_plural = "Payment Records"

    def __str__(self):
        return f"Payment {self.transaction_id} for Order {self.order.order_number}: ₹{self.amount} ({self.status})"

    @classmethod
    def generate_transaction_id(cls):
        """Generates a unique reference: TXN-DEMO-YYYYMMDD-XXXX."""
        today_str = timezone.now().strftime("%Y%m%d")
        rand_hex = uuid.uuid4().hex[:8].upper()
        return f"TXN-DEMO-{today_str}-{rand_hex}"
