"""
payments/views.py
=================
Views for demo payment checkout, execution, and transaction receipt display.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from printing.models import PrintOrder
from .models import Payment
from .services import PaymentService


def checkout_payment_view(request, order_number):
    """
    Renders the demo payment gateway screen.
    Displays clear notices that this is a simulated demo payment.
    """
    order = get_object_or_404(PrintOrder, order_number=order_number)

    # Security check: if customer is logged in, ensure ownership; if guest, check session
    if order.user and request.user.is_authenticated and order.user != request.user:
        messages.error(request, "You are not authorized to view this payment page.")
        return redirect('printing:home')

    # If order is already paid, redirect straight to confirmation
    if order.payment_status == PrintOrder.PAYMENT_COMPLETED:
        messages.info(request, "This order has already been paid and authorized.")
        return redirect('printing:order_confirmation', order_number=order.order_number)

    context = {
        'order': order,
        'doc': order.document,
        'payment_modes': Payment.PAYMENT_MODE_CHOICES,
    }
    return render(request, 'payments/demo_payment.html', context)


@require_POST
def process_demo_payment_view(request, order_number):
    """
    Processes the demo payment simulation submitted via POST.
    Supports both SUCCESS and FAILURE simulation paths.
    """
    order = get_object_or_404(PrintOrder, order_number=order_number)

    payment_mode = request.POST.get('payment_mode', Payment.MODE_DEMO_UPI)
    simulate_outcome = request.POST.get('simulate_outcome', 'SUCCESS')

    success, payment, message = PaymentService.process_demo_payment(
        order=order,
        payment_mode=payment_mode,
        simulate_outcome=simulate_outcome
    )

    if success:
        messages.success(request, f"Payment Verified! {message}")
        return redirect('printing:order_confirmation', order_number=order.order_number)
    else:
        messages.error(request, f"Payment Declined! {message}")
        return redirect('payments:payment_result', transaction_id=payment.transaction_id)


def payment_result_view(request, transaction_id):
    """
    Displays payment result (success or failure) and transaction details.
    """
    payment = get_object_or_404(Payment, transaction_id=transaction_id)
    return render(request, 'payments/payment_result.html', {
        'payment': payment,
        'order': payment.order
    })
