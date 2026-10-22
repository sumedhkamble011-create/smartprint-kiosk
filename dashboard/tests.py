"""
dashboard/tests.py
==================
Automated tests for Shop-Owner Dashboard:
1. Access control & operator permission enforcement
2. Overview KPIs and metric cards
3. Order list search & detail inspection
4. Status update actions and synchronization
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import UserProfile
from printing.models import Shop, Document, PrintOrder, PrintJob


class DashboardPermissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Regular customer
        self.customer = User.objects.create_user(username="cust", password="password")
        self.cust_profile = UserProfile.objects.get(user=self.customer)
        self.cust_profile.role = UserProfile.ROLE_CUSTOMER
        self.cust_profile.save()

        # Shop operator
        self.operator = User.objects.create_user(username="shopop", password="password", is_staff=True)
        self.op_profile = UserProfile.objects.get(user=self.operator)
        self.op_profile.role = UserProfile.ROLE_SHOP_OWNER
        self.op_profile.save()

    def test_anonymous_redirected_to_staff_login(self):
        """Unauthenticated requests must be redirected to the staff login page."""
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:staff_login'), response.url)

    def test_customer_denied_dashboard_access(self):
        """Regular customer accounts must be blocked from dashboard routes."""
        self.client.login(username="cust", password="password")
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('printing:home'))

    def test_operator_granted_dashboard_access(self):
        """Operator account must be granted 200 OK access to dashboard overview."""
        self.client.login(username="shopop", password="password")
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Active Print Queue")


class DashboardOrderActionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.operator = User.objects.create_user(username="boss", password="password", is_staff=True)
        self.profile = UserProfile.objects.get(user=self.operator)
        self.profile.role = UserProfile.ROLE_SHOP_OWNER
        self.profile.save()
        self.client.login(username="boss", password="password")

        self.shop = Shop.get_default_shop()
        self.doc_file = SimpleUploadedFile("dash.pdf", b"%PDF-1.4 dash", content_type="application/pdf")
        self.doc = Document.objects.create(
            original_filename="dash.pdf",
            file=self.doc_file,
            file_type='PDF',
            file_size=500,
            page_count=2
        )
        self.order = PrintOrder.objects.create(
            order_number=PrintOrder.generate_unique_order_number(),
            shop=self.shop,
            document=self.doc,
            rate_applied=Decimal('2.00'),
            total_pages_printed=2,
            subtotal_amount=Decimal('4.00'),
            total_amount=Decimal('4.00'),
            order_status=PrintOrder.STATUS_PAID,
            payment_status=PrintOrder.PAYMENT_COMPLETED
        )
        self.job = PrintJob.objects.create(order=self.order, job_status=PrintJob.JOB_QUEUED)

    def test_update_status_to_processing(self):
        """Operator transitions PAID order to PROCESSING."""
        url = reverse('dashboard:update_status', kwargs={'order_number': self.order.order_number})
        response = self.client.post(url, {'new_status': 'PROCESSING'})
        self.assertEqual(response.status_code, 302)

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, PrintOrder.STATUS_PROCESSING)

        self.job.refresh_from_db()
        self.assertEqual(self.job.job_status, PrintJob.JOB_PROCESSING)

    def test_update_status_to_ready(self):
        """Operator marks PROCESSING order as READY."""
        self.order.order_status = PrintOrder.STATUS_PROCESSING
        self.order.save()

        url = reverse('dashboard:update_status', kwargs={'order_number': self.order.order_number})
        response = self.client.post(url, {'new_status': 'READY'})
        self.assertEqual(response.status_code, 302)

        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, PrintOrder.STATUS_READY)

        self.job.refresh_from_db()
        self.assertEqual(self.job.job_status, PrintJob.JOB_PRINTED)
