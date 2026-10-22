"""
printing/services.py
====================
Business logic service layer for:
- Document processing and page count detection
- PrintOrder creation and price calculation
- Order state transitions (Payment verification, queuing, completion)
- Idempotent print job creation
"""

import os
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Document, PrintOrder, PrintJob, Shop, PricingSetting
from .validators import validate_uploaded_document, detect_document_page_count
from .pricing import calculate_print_price


def handle_document_upload(uploaded_file, user=None) -> Document:
    """
    Validates uploaded file, detects page count, and creates a Document database record.
    """
    # 1. Validation
    file_type = validate_uploaded_document(uploaded_file)

    # 2. Page count detection
    page_count, page_status = detect_document_page_count(uploaded_file, file_type)

    # 3. Save Document model instance
    document = Document.objects.create(
        user=user if (user and user.is_authenticated) else None,
        original_filename=uploaded_file.name,
        file=uploaded_file,
        file_type=file_type,
        file_size=uploaded_file.size,
        page_count=page_count,
        page_count_status=page_status,
    )
    return document


@transaction.atomic
def create_print_order(
    document: Document,
    shop: Shop,
    preferences: dict,
    customer_name: str = "",
    customer_phone: str = "",
    user=None,
    base_url: str = "http://127.0.0.1:8000"
) -> PrintOrder:
    """
    Calculates final price on the server and creates an order in AWAITING_PAYMENT status.
    """
    pricing = getattr(shop, 'pricing', None)
    if not pricing:
        pricing = PricingSetting.objects.create(shop=shop)

    # Server-side price calculation
    price_info = calculate_print_price(
        pricing_setting=pricing,
        total_document_pages=document.page_count,
        color_mode=preferences.get('color_mode', 'BW'),
        copies=int(preferences.get('copies', 1)),
        page_selection_mode=preferences.get('page_selection_mode', 'ALL'),
        custom_page_range=preferences.get('custom_page_range', ''),
        duplex_mode=preferences.get('duplex_mode', 'SINGLE'),
    )

    # Generate unique order number
    order_number = PrintOrder.generate_unique_order_number()

    order = PrintOrder.objects.create(
        order_number=order_number,
        user=user if (user and user.is_authenticated) else None,
        customer_name=customer_name or ("Customer" if not user else user.get_full_name() or user.username),
        customer_phone=customer_phone or "",
        shop=shop,
        document=document,
        color_mode=price_info['color_mode'],
        copies=price_info['copies'],
        page_selection_mode=preferences.get('page_selection_mode', 'ALL'),
        custom_page_range=preferences.get('custom_page_range', ''),
        calculated_pages_per_copy=price_info['pages_per_copy'],
        paper_size='A4',
        duplex_mode=price_info['duplex_mode'],
        orientation=preferences.get('orientation', 'PORTRAIT'),
        rate_applied=price_info['rate_per_page'],
        total_pages_printed=price_info['total_pages_printed'],
        subtotal_amount=price_info['subtotal'],
        discount_amount=price_info['discount'],
        total_amount=price_info['total_amount'],
        order_status=PrintOrder.STATUS_AWAITING_PAYMENT,
        payment_status=PrintOrder.PAYMENT_PENDING,
    )

    # Generate tracking QR code
    try:
        order.generate_tracking_qr(base_url=base_url)
    except Exception:
        pass  # QR generation non-critical if graphics library is in limited environment

    return order


@transaction.atomic
def authorize_paid_order(order: PrintOrder) -> PrintJob:
    """
    Transitions order to PAID and queues a PrintJob idempotently.
    Repeated calls will not duplicate jobs or re-charge.
    """
    # 1. Update order status if not already paid
    if order.order_status == PrintOrder.STATUS_AWAITING_PAYMENT:
        order.order_status = PrintOrder.STATUS_PAID
        order.payment_status = PrintOrder.PAYMENT_COMPLETED
        order.paid_at = timezone.now()
        order.save(update_fields=['order_status', 'payment_status', 'paid_at', 'updated_at'])

    # 2. Create or retrieve PrintJob in buffer (Idempotent)
    job, created = PrintJob.objects.get_or_create(
        order=order,
        defaults={
            'job_status': PrintJob.JOB_QUEUED,
            'attempt_count': 0
        }
    )

    # 3. Transition order to QUEUED
    if order.order_status == PrintOrder.STATUS_PAID:
        order.order_status = PrintOrder.STATUS_QUEUED
        order.save(update_fields=['order_status', 'updated_at'])

    return job


@transaction.atomic
def update_order_status(order: PrintOrder, new_status: str, operator_user=None) -> bool:
    """
    Safely transitions order through valid lifecycle statuses and synchronizes PrintJob.
    """
    if not order.can_transition_to(new_status):
        return False

    order.order_status = new_status
    if new_status == PrintOrder.STATUS_COMPLETED:
        order.completed_at = timezone.now()

    order.save()

    # Synchronize with PrintJob
    if hasattr(order, 'print_job'):
        job = order.print_job
        if new_status == PrintOrder.STATUS_PROCESSING:
            job.job_status = PrintJob.JOB_PROCESSING
            job.processed_at = timezone.now()
            if operator_user:
                job.printed_by = operator_user
            job.attempt_count += 1
            job.save()
        elif new_status in [PrintOrder.STATUS_READY, PrintOrder.STATUS_COMPLETED]:
            job.job_status = PrintJob.JOB_PRINTED
            job.completed_at = timezone.now()
            job.save()
        elif new_status == PrintOrder.STATUS_FAILED:
            job.job_status = PrintJob.JOB_FAILED
            job.save()

    return True
