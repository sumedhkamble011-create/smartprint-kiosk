"""
printing/admin.py
=================
Django admin configuration for Shop, PricingSetting, Document, PrintOrder, and PrintJob.
"""

from django.contrib import admin
from .models import Shop, PricingSetting, Document, PrintOrder, PrintJob


class PricingSettingInline(admin.StackedInline):
    model = PricingSetting
    can_delete = False
    verbose_name = "Shop Pricing Settings"


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'contact_number', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (PricingSettingInline,)


@admin.register(PricingSetting)
class PricingSettingAdmin(admin.ModelAdmin):
    list_display = ('shop', 'bw_rate_per_page', 'color_rate_per_page', 'duplex_discount_per_sheet', 'max_copies_limit', 'updated_at')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'file_type', 'formatted_file_size', 'page_count', 'page_count_status', 'uploaded_at')
    list_filter = ('file_type', 'page_count_status')
    search_fields = ('original_filename',)


class PrintJobInline(admin.StackedInline):
    model = PrintJob
    can_delete = False
    readonly_fields = ('created_at', 'processed_at', 'completed_at')


@admin.register(PrintOrder)
class PrintOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer_name', 'total_amount', 'color_mode', 'copies', 'order_status', 'payment_status', 'created_at')
    list_filter = ('order_status', 'payment_status', 'color_mode', 'created_at')
    search_fields = ('order_number', 'customer_name', 'customer_phone')
    readonly_fields = ('order_number', 'guest_tracking_token', 'created_at', 'updated_at', 'paid_at', 'completed_at')
    inlines = (PrintJobInline,)


@admin.register(PrintJob)
class PrintJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'job_status', 'attempt_count', 'created_at', 'processed_at', 'completed_at')
    list_filter = ('job_status',)
    search_fields = ('order__order_number',)
