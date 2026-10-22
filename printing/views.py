"""
printing/views.py
=================
Customer-facing kiosk views:
1. Home / Landing page
2. Document upload
3. Print preferences selection
4. Dynamic price calculation API (for real-time frontend preview)
5. Order summary & checkout initiation
6. Order confirmation
7. Secure guest order tracking & live status API
8. Document download (protected)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden, Http404, FileResponse
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from .models import Shop, Document, PrintOrder, PricingSetting
from .forms import DocumentUploadForm, PrintPreferencesForm, GuestOrderLookupForm
from .services import handle_document_upload, create_print_order
from .pricing import calculate_print_price, parse_page_range


def home_view(request):
    """
    Kiosk landing page. Displays current shop counter info, pricing rates,
    primary action buttons (Upload Document, Track Order), and QR code.
    """
    shop_slug = request.GET.get('shop') or request.session.get('kiosk_shop_slug')
    shop = Shop.objects.filter(slug=shop_slug).first() if shop_slug else Shop.get_default_shop()

    # Generate shop QR code if not already created
    if not shop.qr_code_image:
        host = request.build_absolute_uri('/')
        try:
            shop.generate_qr_code(base_url=host)
        except Exception:
            pass

    return render(request, 'printing/home.html', {
        'shop': shop,
        'pricing': getattr(shop, 'pricing', None),
        'lookup_form': GuestOrderLookupForm()
    })


def upload_document_view(request):
    """
    Step 1: Upload and validate document.
    """
    shop_slug = request.session.get('kiosk_shop_slug')
    shop = Shop.objects.filter(slug=shop_slug).first() if shop_slug else Shop.get_default_shop()

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data['document_file']
            customer_name = form.cleaned_data.get('customer_name', '')
            customer_phone = form.cleaned_data.get('customer_phone', '')

            # Save file record with detected page count
            user = request.user if request.user.is_authenticated else None
            doc = handle_document_upload(uploaded_file, user=user)

            # Store in session for subsequent steps
            request.session['customer_name'] = customer_name
            request.session['customer_phone'] = customer_phone
            request.session['current_upload_token'] = str(doc.upload_token)

            messages.success(
                request,
                f"File '{doc.original_filename}' uploaded successfully! Detected {doc.page_count} page(s)."
            )
            return redirect('printing:preferences', upload_token=doc.upload_token)
    else:
        form = DocumentUploadForm()

    return render(request, 'printing/upload.html', {
        'form': form,
        'shop': shop,
        'max_mb': settings.MAX_UPLOAD_SIZE_MB,
    })


def preferences_view(request, upload_token):
    """
    Step 2: Print options selection (Color/BW, copies, page range, duplex).
    """
    doc = get_object_or_404(Document, upload_token=upload_token)
    shop_slug = request.session.get('kiosk_shop_slug')
    shop = Shop.objects.filter(slug=shop_slug).first() if shop_slug else Shop.get_default_shop()
    pricing = getattr(shop, 'pricing', None) or PricingSetting.objects.get_or_create(shop=shop)[0]

    if request.method == 'POST':
        form = PrintPreferencesForm(
            request.POST,
            total_pages=doc.page_count,
            max_copies=pricing.max_copies_limit
        )
        if form.is_valid():
            # Store choices in session
            request.session['print_preferences'] = {
                'color_mode': form.cleaned_data['color_mode'],
                'copies': form.cleaned_data['copies'],
                'page_selection_mode': form.cleaned_data['page_selection_mode'],
                'custom_page_range': form.cleaned_data.get('custom_page_range', ''),
                'duplex_mode': form.cleaned_data['duplex_mode'],
                'orientation': form.cleaned_data['orientation'],
            }
            return redirect('printing:order_summary', upload_token=doc.upload_token)
    else:
        # Prepopulate with existing choices from session if available
        initial = request.session.get('print_preferences', {
            'color_mode': PrintOrder.COLOR_BW,
            'copies': 1,
            'page_selection_mode': PrintOrder.PAGE_MODE_ALL,
            'duplex_mode': PrintOrder.DUPLEX_SINGLE,
            'orientation': PrintOrder.ORIENT_PORTRAIT,
        })
        form = PrintPreferencesForm(
            initial=initial,
            total_pages=doc.page_count,
            max_copies=pricing.max_copies_limit
        )

    # Calculate initial default preview price
    initial_price = calculate_print_price(
        pricing_setting=pricing,
        total_document_pages=doc.page_count,
        color_mode=PrintOrder.COLOR_BW,
        copies=1,
        page_selection_mode=PrintOrder.PAGE_MODE_ALL,
        duplex_mode=PrintOrder.DUPLEX_SINGLE
    )

    return render(request, 'printing/preferences.html', {
        'doc': doc,
        'shop': shop,
        'pricing': pricing,
        'form': form,
        'initial_price': initial_price,
    })


@require_GET
def calculate_estimate_api(request, upload_token):
    """
    JSON API endpoint for real-time frontend price preview updates.
    Calculates strictly on the server and returns JSON.
    """
    doc = get_object_or_404(Document, upload_token=upload_token)
    shop_slug = request.session.get('kiosk_shop_slug')
    shop = Shop.objects.filter(slug=shop_slug).first() if shop_slug else Shop.get_default_shop()
    pricing = getattr(shop, 'pricing', None) or PricingSetting.objects.get_or_create(shop=shop)[0]

    color_mode = request.GET.get('color_mode', 'BW')
    try:
        copies = int(request.GET.get('copies', 1))
    except (ValueError, TypeError):
        copies = 1

    page_selection_mode = request.GET.get('page_selection_mode', 'ALL')
    custom_page_range = request.GET.get('custom_page_range', '')
    duplex_mode = request.GET.get('duplex_mode', 'SINGLE')

    try:
        price_info = calculate_print_price(
            pricing_setting=pricing,
            total_document_pages=doc.page_count,
            color_mode=color_mode,
            copies=copies,
            page_selection_mode=page_selection_mode,
            custom_page_range=custom_page_range,
            duplex_mode=duplex_mode
        )
        return JsonResponse({
            'success': True,
            'rate_per_page': str(price_info['rate_per_page']),
            'pages_per_copy': price_info['pages_per_copy'],
            'copies': price_info['copies'],
            'total_pages_printed': price_info['total_pages_printed'],
            'total_sheets': price_info['total_sheets'],
            'subtotal': str(price_info['subtotal']),
            'discount': str(price_info['discount']),
            'total_amount': str(price_info['total_amount']),
        })
    except ValueError as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)


def order_summary_view(request, upload_token):
    """
    Step 3: Review full order breakdown before checkout.
    """
    doc = get_object_or_404(Document, upload_token=upload_token)
    shop_slug = request.session.get('kiosk_shop_slug')
    shop = Shop.objects.filter(slug=shop_slug).first() if shop_slug else Shop.get_default_shop()
    pricing = getattr(shop, 'pricing', None) or PricingSetting.objects.get_or_create(shop=shop)[0]

    prefs = request.session.get('print_preferences')
    if not prefs:
        messages.warning(request, "Please select your printing preferences first.")
        return redirect('printing:preferences', upload_token=doc.upload_token)

    # Server price calculation
    price_info = calculate_print_price(
        pricing_setting=pricing,
        total_document_pages=doc.page_count,
        color_mode=prefs.get('color_mode', 'BW'),
        copies=int(prefs.get('copies', 1)),
        page_selection_mode=prefs.get('page_selection_mode', 'ALL'),
        custom_page_range=prefs.get('custom_page_range', ''),
        duplex_mode=prefs.get('duplex_mode', 'SINGLE')
    )

    if request.method == 'POST':
        # Create the order and route to Demo Payment
        base_url = request.build_absolute_uri('/')
        order = create_print_order(
            document=doc,
            shop=shop,
            preferences=prefs,
            customer_name=request.session.get('customer_name', ''),
            customer_phone=request.session.get('customer_phone', ''),
            user=request.user if request.user.is_authenticated else None,
            base_url=base_url
        )
        return redirect('payments:checkout', order_number=order.order_number)

    return render(request, 'printing/order_summary.html', {
        'doc': doc,
        'shop': shop,
        'prefs': prefs,
        'price_info': price_info,
        'customer_name': request.session.get('customer_name', ''),
        'customer_phone': request.session.get('customer_phone', ''),
    })


def order_confirmation_view(request, order_number):
    """
    Step 4: Displays payment success confirmation, assigned order number,
    and a QR code that directly links to guest tracking.
    """
    order = get_object_or_404(PrintOrder, order_number=order_number)
    return render(request, 'printing/order_confirmation.html', {
        'order': order,
        'tracking_url': request.build_absolute_uri(f"/track/{order.guest_tracking_token}/")
    })


def track_order_view(request, tracking_token=None):
    """
    Order tracking view.
    1. If tracking_token in URL (/track/<token>/), display the matching order.
    2. If GET request to /track/ with order_number search, look it up.
    """
    order = None
    form = GuestOrderLookupForm(request.GET or None)

    if tracking_token:
        order = get_object_or_404(PrintOrder, guest_tracking_token=tracking_token)
    elif request.GET.get('order_number'):
        num = request.GET.get('order_number').strip().upper()
        order = PrintOrder.objects.filter(order_number=num).first()
        if not order:
            messages.error(request, f"No print order found with reference '{num}'. Please verify the number.")

    return render(request, 'printing/track_order.html', {
        'order': order,
        'form': form,
    })


@require_GET
def order_status_api(request, tracking_token):
    """
    Pollable JSON endpoint for real-time order status updates on tracking screen.
    """
    order = get_object_or_404(PrintOrder, guest_tracking_token=tracking_token)
    job_status = order.print_job.job_status if hasattr(order, 'print_job') else 'NONE'

    return JsonResponse({
        'order_number': order.order_number,
        'order_status': order.order_status,
        'order_status_display': order.get_order_status_display(),
        'payment_status': order.payment_status,
        'job_status': job_status,
        'is_ready': order.order_status in [PrintOrder.STATUS_READY, PrintOrder.STATUS_COMPLETED],
        'is_completed': order.order_status == PrintOrder.STATUS_COMPLETED,
    })


def download_document_view(request, order_number):
    """
    Secure file download: Only order owner or shop staff can download the file.
    """
    order = get_object_or_404(PrintOrder, order_number=order_number)

    # Permission check
    is_staff = request.user.is_authenticated and (
        request.user.is_staff or (hasattr(request.user, 'profile') and request.user.profile.is_shop_operator)
    )
    is_owner = request.user.is_authenticated and (order.user == request.user)
    has_session = request.session.get('current_upload_token') == str(order.document.upload_token)

    if not (is_staff or is_owner or has_session):
        return HttpResponseForbidden("Access Denied: You do not have permission to view or download this document.")

    doc = order.document
    if not doc.file or not os.path.exists(doc.file.path):
        raise Http404("Document file not found on server.")

    return FileResponse(open(doc.file.path, 'rb'), as_attachment=False, filename=doc.original_filename)
