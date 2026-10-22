"""
payments/admin.py
=================
Django admin configuration for Payment transactions ledger.
"""

from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'order', 'amount', 'payment_mode', 'status', 'created_at', 'verified_at')
    list_filter = ('status', 'payment_mode', 'created_at')
    search_fields = ('transaction_id', 'order__order_number', 'order__customer_name')
    readonly_fields = ('transaction_id', 'created_at', 'verified_at')
