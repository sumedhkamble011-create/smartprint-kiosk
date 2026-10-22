"""
printing/tests.py
=================
Comprehensive automated test suite for SmartPrintKiosk:
1. Pricing calculation engine (B&W, Colour, page ranges, copies, duplex discounts)
2. File validation & security checks (extensions, size limits, signatures)
3. Order lifecycle & state transitions
4. Kiosk views & live JSON endpoints
5. Print worker simulation & unpaid job prevention
"""

import os
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from .models import Shop, PricingSetting, Document, PrintOrder, PrintJob
from .pricing import calculate_print_price, parse_page_range
from .validators import validate_uploaded_document, detect_document_page_count
from .services import handle_document_upload, create_print_order, authorize_paid_order, update_order_status
from .print_worker import KioskPrintWorker


class PricingCalculationTests(TestCase):
    """Tests the server-side price calculation logic and page range parser."""

    def setUp(self):
        self.shop = Shop.objects.create(
            name="Test Kiosk",
            slug="test-kiosk"
        )
        self.pricing = PricingSetting.objects.create(
            shop=self.shop,
            bw_rate_per_page=Decimal('2.00'),
            color_rate_per_page=Decimal('10.00'),
            duplex_discount_per_sheet=Decimal('0.50'),
            max_copies_limit=50
        )

    def test_page_range_parser_valid(self):
        """Test parsing valid page range strings."""
        pages = parse_page_range("1-3, 5, 8", max_pages=10)
        self.assertEqual(pages, [1, 2, 3, 5, 8])

    def test_page_range_parser_exceeds_max(self):
        """Test that requesting pages beyond the document length raises ValueError."""
        with self.assertRaises(ValueError):
            parse_page_range("1-15", max_pages=10)

    def test_page_range_parser_invalid_tokens(self):
        """Test that malformed ranges raise ValueError."""
        with self.assertRaises(ValueError):
            parse_page_range("1-abc", max_pages=10)
        with self.assertRaises(ValueError):
            parse_page_range("5-2", max_pages=10)

    def test_bw_price_calculation(self):
        """5 pages B&W, 2 copies = 10 pages * ₹2.00 = ₹20.00."""
        calc = calculate_print_price(
            pricing_setting=self.pricing,
            total_document_pages=5,
            color_mode='BW',
            copies=2,
            page_selection_mode='ALL',
            duplex_mode='SINGLE'
        )
        self.assertEqual(calc['total_pages_printed'], 10)
        self.assertEqual(calc['subtotal'], Decimal('20.00'))
        self.assertEqual(calc['discount'], Decimal('0.00'))
        self.assertEqual(calc['total_amount'], Decimal('20.00'))

    def test_color_price_calculation(self):
        """3 pages Colour, 1 copy = 3 * ₹10.00 = ₹30.00."""
        calc = calculate_print_price(
            pricing_setting=self.pricing,
            total_document_pages=3,
            color_mode='COLOR',
            copies=1,
            page_selection_mode='ALL',
            duplex_mode='SINGLE'
        )
        self.assertEqual(calc['rate_per_page'], Decimal('10.00'))
        self.assertEqual(calc['total_amount'], Decimal('30.00'))

    def test_duplex_discount_calculation(self):
        """
        4 pages, 1 copy in double-sided (duplex).
        Physical sheets used = ceil(4 / 2) = 2 sheets.
        Sheets saved = 4 - 2 = 2 sheets.
        Discount = 2 sheets * ₹0.50 = ₹1.00.
        B&W subtotal = 4 * ₹2.00 = ₹8.00.
        Total = 8.00 - 1.00 = ₹7.00.
        """
        calc = calculate_print_price(
            pricing_setting=self.pricing,
            total_document_pages=4,
            color_mode='BW',
            copies=1,
            page_selection_mode='ALL',
            duplex_mode='DOUBLE'
        )
        self.assertEqual(calc['total_sheets'], 2)
        self.assertEqual(calc['sheets_saved'], 2)
        self.assertEqual(calc['discount'], Decimal('1.00'))
        self.assertEqual(calc['total_amount'], Decimal('7.00'))

    def test_copies_limit_enforced(self):
        """Copies exceeding shop limit should raise ValueError."""
        with self.assertRaises(ValueError):
            calculate_print_price(
                pricing_setting=self.pricing,
                total_document_pages=5,
                copies=55
            )


class DocumentValidationTests(TestCase):
    """Tests file extension, size, and header signature checks."""

    def test_valid_pdf_upload(self):
        pdf_bytes = b"%PDF-1.4 sample pdf content"
        f = SimpleUploadedFile("sample.pdf", pdf_bytes, content_type="application/pdf")
        doc_type = validate_uploaded_document(f)
        self.assertEqual(doc_type, 'PDF')

    def test_valid_image_upload(self):
        png_bytes = b"\x89PNG\r\n\x1a\nfake png data"
        f = SimpleUploadedFile("receipt.png", png_bytes, content_type="image/png")
        doc_type = validate_uploaded_document(f)
        self.assertEqual(doc_type, 'IMAGE')

    def test_unsupported_file_extension(self):
        exe_file = SimpleUploadedFile("malware.exe", b"MZexecutabledata", content_type="application/x-dosexec")
        with self.assertRaises(ValidationError):
            validate_uploaded_document(exe_file)

    def test_mismatched_magic_signature(self):
        """File claiming to be .pdf but actually containing plain text/script."""
        fake_pdf = SimpleUploadedFile("bad.pdf", b"This is not a real PDF file header", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_uploaded_document(fake_pdf)


class OrderWorkflowAndStateTests(TestCase):
    """Tests order creation, state transitions, and tracking tokens."""

    def setUp(self):
        self.shop = Shop.get_default_shop()
        self.pricing = self.shop.pricing
        self.doc_file = SimpleUploadedFile("test.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        self.document = Document.objects.create(
            original_filename="test.pdf",
            file=self.doc_file,
            file_type='PDF',
            file_size=1024,
            page_count=2,
            page_count_status='DETECTED'
        )

    def test_order_creation_initial_state(self):
        """Newly created orders must be AWAITING_PAYMENT with PENDING payment."""
        prefs = {
            'color_mode': 'BW',
            'copies': 1,
            'page_selection_mode': 'ALL',
            'duplex_mode': 'SINGLE',
            'orientation': 'PORTRAIT'
        }
        order = create_print_order(
            document=self.document,
            shop=self.shop,
            preferences=prefs,
            customer_name="Alice Student"
        )
        self.assertEqual(order.order_status, PrintOrder.STATUS_AWAITING_PAYMENT)
        self.assertEqual(order.payment_status, PrintOrder.PAYMENT_PENDING)
        self.assertIsNotNone(order.guest_tracking_token)
        self.assertEqual(order.total_amount, Decimal('4.00'))  # 2 pages * 2.00

    def test_valid_state_transitions(self):
        """Tests advancing status from Paid -> Queued -> Processing -> Ready -> Completed."""
        prefs = {'color_mode': 'BW', 'copies': 1, 'page_selection_mode': 'ALL', 'duplex_mode': 'SINGLE'}
        order = create_print_order(self.document, self.shop, prefs)

        # 1. Authorize order
        job = authorize_paid_order(order)
        order.refresh_from_db()
        self.assertEqual(order.order_status, PrintOrder.STATUS_QUEUED)
        self.assertEqual(order.payment_status, PrintOrder.PAYMENT_COMPLETED)
        self.assertEqual(job.job_status, PrintJob.JOB_QUEUED)

        # 2. Advance to PROCESSING
        success = update_order_status(order, PrintOrder.STATUS_PROCESSING)
        self.assertTrue(success)
        order.refresh_from_db()
        self.assertEqual(order.order_status, PrintOrder.STATUS_PROCESSING)

        # 3. Advance to READY
        success = update_order_status(order, PrintOrder.STATUS_READY)
        self.assertTrue(success)
        order.refresh_from_db()
        self.assertEqual(order.order_status, PrintOrder.STATUS_READY)

        # 4. Advance to COMPLETED
        success = update_order_status(order, PrintOrder.STATUS_COMPLETED)
        self.assertTrue(success)
        order.refresh_from_db()
        self.assertEqual(order.order_status, PrintOrder.STATUS_COMPLETED)
        self.assertIsNotNone(order.completed_at)

    def test_illegal_state_transition_prevented(self):
        """Direct jump from Awaiting Payment to Completed must be forbidden."""
        prefs = {'color_mode': 'BW', 'copies': 1, 'page_selection_mode': 'ALL', 'duplex_mode': 'SINGLE'}
        order = create_print_order(self.document, self.shop, prefs)
        self.assertFalse(order.can_transition_to(PrintOrder.STATUS_COMPLETED))
        success = update_order_status(order, PrintOrder.STATUS_COMPLETED)
        self.assertFalse(success)


class PrintWorkerSimulationTests(TestCase):
    """Tests the print worker daemon logic in simulation mode."""

    def setUp(self):
        self.shop = Shop.get_default_shop()
        self.worker = KioskPrintWorker(shop_slug=self.shop.slug, poll_interval=1)
        self.doc_file = SimpleUploadedFile("job.pdf", b"%PDF-1.4 file data", content_type="application/pdf")
        self.document = Document.objects.create(
            original_filename="job.pdf",
            file=self.doc_file,
            file_type='PDF',
            file_size=512,
            page_count=1
        )

    def test_unpaid_order_refused_by_worker(self):
        """Worker must not print an order whose payment is not completed."""
        order = create_print_order(
            self.document, self.shop,
            {'color_mode': 'BW', 'copies': 1, 'page_selection_mode': 'ALL', 'duplex_mode': 'SINGLE'}
        )
        job = PrintJob.objects.create(order=order, job_status=PrintJob.JOB_QUEUED)
        processed = self.worker.process_single_job(job)
        self.assertFalse(processed)
        job.refresh_from_db()
        self.assertEqual(job.job_status, PrintJob.JOB_FAILED)
        self.assertIn("NOT paid", job.error_message)


class KioskViewTests(TestCase):
    """Tests customer-facing URL responses and API endpoints."""

    def setUp(self):
        self.client = Client()
        self.shop = Shop.get_default_shop()
        self.doc_file = SimpleUploadedFile("view_test.pdf", b"%PDF-1.4 data", content_type="application/pdf")
        self.doc = Document.objects.create(
            original_filename="view_test.pdf",
            file=self.doc_file,
            file_type='PDF',
            file_size=500,
            page_count=3
        )

    def test_home_page_status_200(self):
        response = self.client.get(reverse('printing:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SmartPrint")

    def test_upload_page_status_200(self):
        response = self.client.get(reverse('printing:upload'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload Your Document")

    def test_price_estimate_api(self):
        url = reverse('printing:api_price', kwargs={'upload_token': self.doc.upload_token})
        response = self.client.get(f"{url}?color_mode=COLOR&copies=2&page_selection_mode=ALL&duplex_mode=SINGLE")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        # 3 pages * 2 copies = 6 pages * ₹10.00 = ₹60.00
        self.assertEqual(data['total_pages_printed'], 6)
        self.assertEqual(data['total_amount'], "60.00")
