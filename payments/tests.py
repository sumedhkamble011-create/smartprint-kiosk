"""
payments/tests.py
=================
Automated tests for demo payment service:
1. Successful payment verification and job authorization
2. Failed payment decline simulation
3. Payment idempotency (no duplicate charges or double job queuing)
4. Payment checkout views
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from printing.models import Shop, Document, PrintOrder, PrintJob
from payments.models import Payment
from payments.services import PaymentService


class PaymentServiceTests(TestCase):
    def setUp(self):
        self.shop = Shop.get_default_shop()
        self.doc_file = SimpleUploadedFile("bill.pdf", b"%PDF-1.4 payment test", content_type="application/pdf")
        self.document = Document.objects.create(
            original_filename="bill.pdf",
            file=self.doc_file,
            file_type='PDF',
            file_size=1024,
            page_count=2
        )
        self.order = PrintOrder.objects.create(
            order_number=PrintOrder.generate_unique_order_number(),
            shop=self.shop,
            document=self.document,
            color_mode='BW',
            copies=1,
            rate_applied=Decimal('2.00'),
            total_pages_printed=2,
            subtotal_amount=Decimal('4.00'),
            total_amount=Decimal('4.00'),
            order_status=PrintOrder.STATUS_AWAITING_PAYMENT,
            payment_status=PrintOrder.PAYMENT_PENDING
        )

    def test_demo_payment_success_flow(self):
        """Successful payment must authorize order and create a queued print job."""
        success, payment, msg = PaymentService.process_demo_payment(
            order=self.order,
            payment_mode=Payment.MODE_DEMO_UPI,
            simulate_outcome='SUCCESS'
        )
        self.assertTrue(success)
        self.assertEqual(payment.status, Payment.STATUS_SUCCESS)
        self.assertIsNotNone(payment.verified_at)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, PrintOrder.PAYMENT_COMPLETED)
        self.assertEqual(self.order.order_status, PrintOrder.STATUS_QUEUED)

        # Verify PrintJob queue item created
        self.assertTrue(hasattr(self.order, 'print_job'))
        self.assertEqual(self.order.print_job.job_status, PrintJob.JOB_QUEUED)

    def test_demo_payment_failure_flow(self):
        """Failed payment must mark payment and order as failed, with NO authorized print job."""
        success, payment, msg = PaymentService.process_demo_payment(
            order=self.order,
            payment_mode=Payment.MODE_DEMO_CARD,
            simulate_outcome='FAILURE'
        )
        self.assertFalse(success)
        self.assertEqual(payment.status, Payment.STATUS_FAILED)

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, PrintOrder.PAYMENT_FAILED)
        self.assertFalse(hasattr(self.order, 'print_job'))

    def test_payment_idempotency(self):
        """Submitting payment twice on the same order must not duplicate payments or print jobs."""
        # First call: succeeds
        success1, payment1, _ = PaymentService.process_demo_payment(self.order, simulate_outcome='SUCCESS')
        self.assertTrue(success1)

        # Second call: returns existing payment without duplicating
        success2, payment2, _ = PaymentService.process_demo_payment(self.order, simulate_outcome='SUCCESS')
        self.assertTrue(success2)
        self.assertEqual(payment1.id, payment2.id)

        # Verify database counts
        self.assertEqual(Payment.objects.filter(order=self.order).count(), 1)
        self.assertEqual(PrintJob.objects.filter(order=self.order).count(), 1)


class PaymentViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.shop = Shop.get_default_shop()
        self.doc_file = SimpleUploadedFile("chk.pdf", b"%PDF-1.4 chk", content_type="application/pdf")
        self.doc = Document.objects.create(
            original_filename="chk.pdf",
            file=self.doc_file,
            file_type='PDF',
            file_size=500,
            page_count=1
        )
        self.order = PrintOrder.objects.create(
            order_number=PrintOrder.generate_unique_order_number(),
            shop=self.shop,
            document=self.doc,
            rate_applied=Decimal('2.00'),
            total_pages_printed=1,
            subtotal_amount=Decimal('2.00'),
            total_amount=Decimal('2.00'),
            order_status=PrintOrder.STATUS_AWAITING_PAYMENT,
            payment_status=PrintOrder.PAYMENT_PENDING
        )

    def test_checkout_page_renders_with_demo_notice(self):
        url = reverse('payments:checkout', kwargs={'order_number': self.order.order_number})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DEMO PAYMENT")
        self.assertContains(response, "NO REAL MONEY IS CHARGED")
