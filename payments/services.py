"""
payments/services.py
====================
Dedicated payment processing service module.

Responsibilities:
1. Initialize payment transaction records for an order.
2. Verify payment outcomes (handles success and failure demo paths).
3. Enforce idempotency: multiple calls with the same order won't duplicate payments or print jobs.
4. Trigger print order authorization upon verified payment.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Payment
from printing.models import PrintOrder
from printing.services import authorize_paid_order


class PaymentService:
    """
    Service layer providing clean abstraction for payment gateways.
    Currently implements a secure demo gateway for college demonstration.
    """

    @classmethod
    @transaction.atomic
    def process_demo_payment(
        cls,
        order: PrintOrder,
        payment_mode: str = Payment.MODE_DEMO_UPI,
        simulate_outcome: str = 'SUCCESS'
    ) -> tuple[bool, Payment, str]:
        """
        Executes and verifies a demo payment for the given order.

        Parameters:
        - order: PrintOrder instance to pay for.
        - payment_mode: Choice from Payment.PAYMENT_MODE_CHOICES.
        - simulate_outcome: 'SUCCESS' or 'FAILURE'.

        Returns:
        - (success: bool, payment: Payment, message: str)
        """
        # 1. Idempotency Check: If order is already paid, return existing success payment
        if order.payment_status == PrintOrder.PAYMENT_COMPLETED:
            existing_payment = Payment.objects.filter(order=order, status=Payment.STATUS_SUCCESS).first()
            if existing_payment:
                return True, existing_payment, "Order is already paid and verified."

        # 2. Get or create payment transaction record
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'transaction_id': Payment.generate_transaction_id(),
                'amount': order.total_amount,
                'payment_mode': payment_mode,
                'status': Payment.STATUS_PENDING,
            }
        )

        if not created and payment.status == Payment.STATUS_SUCCESS:
            return True, payment, "Order is already paid."

        # 3. Simulate Gateway Outcome
        if simulate_outcome.upper() == 'SUCCESS':
            payment.status = Payment.STATUS_SUCCESS
            payment.payment_mode = payment_mode
            payment.verified_at = timezone.now()
            payment.gateway_response_code = "DEMO_SUCCESS_200"
            payment.error_message = ""
            payment.save()

            # 4. Authorize order and create queued print job
            authorize_paid_order(order)

            return True, payment, "Demo payment completed and verified successfully."
        else:
            # Failure path
            payment.status = Payment.STATUS_FAILED
            payment.payment_mode = payment_mode
            payment.gateway_response_code = "DEMO_DECLINED_402"
            payment.error_message = "Simulated bank payment decline: insufficient demo funds or user cancelled."
            payment.save()

            order.payment_status = PrintOrder.PAYMENT_FAILED
            order.save(update_fields=['payment_status', 'updated_at'])

            return False, payment, "Demo payment was declined or cancelled as requested."
