"""
dashboard/views.py
==================
Shop-Owner and Staff Operator Dashboard:
- Overview KPIs (revenue, order counts, status breakdown)
- Order management, search, filtering, and detail inspect
- Validated state transitions (Approve, Process, Ready, Complete, Cancel)
- Pricing settings management
- QR code generation and download for counter display
- Shop profile and printer configuration
"""

from functools import wraps
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.conf import settings
from printing.models import Shop, PrintOrder, PrintJob, PricingSetting
from printing.forms import PricingSettingsForm, ShopSettingsForm
from printing.services import update_order_status


def operator_required(view_func):
    """
    Decorator enforcing that the user is authenticated and possesses shop operator,
    staff, or superuser permissions.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in with staff credentials to access the shop dashboard.")
            return redirect('accounts:staff_login')

        is_op = False
        if hasattr(request.user, 'profile'):
            is_op = request.user.profile.is_shop_operator

        if not (is_op or request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Access Denied: You do not have operator or staff permissions.")
            return redirect('printing:home')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


@operator_required
def overview_view(request):
    """
    Executive dashboard overview with metric cards and recent order activities.
    """
    shop = Shop.get_default_shop()

    # Aggregate KPIs
    all_orders = PrintOrder.objects.filter(shop=shop)
    total_orders = all_orders.count()

    # Revenue from paid/completed orders
    revenue_agg = all_orders.filter(payment_status=PrintOrder.PAYMENT_COMPLETED).aggregate(
        total_rev=Sum('total_amount')
    )
    total_revenue = revenue_agg['total_rev'] or Decimal('0.00')

    # Status counts
    awaiting_payment_count = all_orders.filter(order_status=PrintOrder.STATUS_AWAITING_PAYMENT).count()
    in_queue_count = all_orders.filter(order_status__in=[
        PrintOrder.STATUS_PAID, PrintOrder.STATUS_QUEUED, PrintOrder.STATUS_PROCESSING
    ]).count()
    ready_count = all_orders.filter(order_status=PrintOrder.STATUS_READY).count()
    completed_count = all_orders.filter(order_status=PrintOrder.STATUS_COMPLETED).count()

    # Recent 8 orders
    recent_orders = all_orders.select_related('document').order_by('-created_at')[:8]

    # Active print queue jobs
    active_jobs = PrintJob.objects.filter(
        order__shop=shop,
        job_status__in=[PrintJob.JOB_QUEUED, PrintJob.JOB_PROCESSING]
    ).select_related('order', 'order__document').order_by('created_at')

    context = {
        'shop': shop,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'awaiting_payment_count': awaiting_payment_count,
        'in_queue_count': in_queue_count,
        'ready_count': ready_count,
        'completed_count': completed_count,
        'recent_orders': recent_orders,
        'active_jobs': active_jobs,
        'print_mode': settings.PRINT_MODE,
    }
    return render(request, 'dashboard/overview.html', context)


@operator_required
def order_list_view(request):
    """
    Comprehensive searchable and filterable order list with pagination.
    """
    shop = Shop.get_default_shop()
    orders = PrintOrder.objects.filter(shop=shop).select_related('document').order_by('-created_at')

    # Search filter
    search_query = request.GET.get('q', '').strip()
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(customer_name__icontains=search_query) |
            Q(customer_phone__icontains=search_query) |
            Q(document__original_filename__icontains=search_query)
        )

    # Status filter
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        orders = orders.filter(order_status=status_filter)

    # Color mode filter
    color_filter = request.GET.get('color', '').strip()
    if color_filter:
        orders = orders.filter(color_mode=color_filter)

    # Date filter (today)
    date_filter = request.GET.get('date', '').strip()
    if date_filter == 'today':
        today = timezone.localdate()
        orders = orders.filter(created_at__date=today)

    paginator = Paginator(orders, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/order_list.html', {
        'shop': shop,
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'color_filter': color_filter,
        'date_filter': date_filter,
        'status_choices': PrintOrder.STATUS_CHOICES,
    })


@operator_required
def order_detail_view(request, order_number):
    """
    Detailed inspection of a print order:
    - Customer & Document metadata
    - Print options & price calculation details
    - Payment ledger & transaction details
    - Print job attempt logs & status actions
    """
    order = get_object_or_404(PrintOrder.objects.select_related('document', 'shop'), order_number=order_number)
    payment = getattr(order, 'payment', None)
    job = getattr(order, 'print_job', None)

    return render(request, 'dashboard/order_detail.html', {
        'order': order,
        'doc': order.document,
        'payment': payment,
        'job': job,
    })


@operator_required
@require_POST
def update_order_status_view(request, order_number):
    """
    Action endpoint to advance order status (e.g. mark Ready, Complete, Cancel).
    Validates state transitions to prevent business logic bypass.
    """
    order = get_object_or_404(PrintOrder, order_number=order_number)
    new_status = request.POST.get('new_status')

    if not new_status:
        messages.error(request, "No status provided.")
        return redirect('dashboard:order_detail', order_number=order.order_number)

    success = update_order_status(order, new_status, operator_user=request.user)
    if success:
        messages.success(request, f"Order #{order.order_number} status updated to '{order.get_order_status_display()}'.")
    else:
        messages.error(
            request,
            f"Cannot change status from '{order.get_order_status_display()}' to '{new_status}'. Transition not permitted."
        )

    return redirect('dashboard:order_detail', order_number=order.order_number)


@operator_required
def pricing_settings_view(request):
    """
    Allows shop owner to configure B&W rate, Colour rate, duplex discount, and max copies limit.
    """
    shop = Shop.get_default_shop()
    pricing = getattr(shop, 'pricing', None) or PricingSetting.objects.get_or_create(shop=shop)[0]

    if request.method == 'POST':
        form = PricingSettingsForm(request.POST, instance=pricing)
        if form.is_valid():
            form.save()
            messages.success(request, "Shop pricing rates updated successfully!")
            return redirect('dashboard:pricing_settings')
    else:
        form = PricingSettingsForm(instance=pricing)

    return render(request, 'dashboard/pricing_settings.html', {
        'shop': shop,
        'pricing': pricing,
        'form': form,
    })


@operator_required
def qr_management_view(request):
    """
    Manages the counter QR code.
    Allows viewing, downloading, and regenerating with a custom host address (useful for LAN testing).
    """
    shop = Shop.get_default_shop()

    if request.method == 'POST':
        custom_host = request.POST.get('custom_host', '').strip()
        if not custom_host:
            custom_host = request.build_absolute_uri('/')
        try:
            shop.generate_qr_code(base_url=custom_host)
            messages.success(request, f"Counter QR Code regenerated for target: {custom_host}")
        except Exception as exc:
            messages.error(request, f"Failed to generate QR code: {exc}")
        return redirect('dashboard:qr_management')

    return render(request, 'dashboard/qr_management.html', {
        'shop': shop,
        'current_host': request.build_absolute_uri('/'),
    })


@operator_required
def shop_settings_view(request):
    """
    Manages shop name, contact information, and physical Windows printer configuration.
    """
    shop = Shop.get_default_shop()

    if request.method == 'POST':
        form = ShopSettingsForm(request.POST, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, "Shop settings and printer configuration updated.")
            return redirect('dashboard:shop_settings')
    else:
        form = ShopSettingsForm(instance=shop)

    return render(request, 'dashboard/shop_settings.html', {
        'shop': shop,
        'form': form,
        'print_mode': settings.PRINT_MODE,
    })
