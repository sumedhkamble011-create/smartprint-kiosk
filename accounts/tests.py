"""
accounts/tests.py
=================
Automated tests for customer registration, authentication, staff authorization,
and order history permission checks.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile


class AccountAuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create regular customer
        self.customer_user = User.objects.create_user(
            username="student1",
            email="student1@college.edu",
            password="securepassword123"
        )
        self.customer_profile = UserProfile.objects.get(user=self.customer_user)
        self.customer_profile.role = UserProfile.ROLE_CUSTOMER
        self.customer_profile.save()

        # Create staff operator
        self.staff_user = User.objects.create_user(
            username="operator1",
            email="operator1@shop.com",
            password="operatorpass123",
            is_staff=True
        )
        self.staff_profile = UserProfile.objects.get(user=self.staff_user)
        self.staff_profile.role = UserProfile.ROLE_STAFF
        self.staff_profile.save()

    def test_customer_registration_success(self):
        """Test registering a new customer account."""
        url = reverse('accounts:register')
        data = {
            'username': 'newstudent',
            'email': 'newstudent@college.edu',
            'first_name': 'New',
            'last_name': 'Student',
            'phone_number': '9876543210',
            'password': 'password123',
            'password_confirm': 'password123',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)  # Redirects to home upon successful registration
        self.assertTrue(User.objects.filter(username='newstudent').exists())

    def test_customer_registration_password_mismatch(self):
        """Registration should fail when passwords do not match."""
        url = reverse('accounts:register')
        data = {
            'username': 'mismatchuser',
            'email': 'mismatch@college.edu',
            'password': 'password123',
            'password_confirm': 'differentpassword',
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='mismatchuser').exists())

    def test_customer_login_success(self):
        """Test successful customer login."""
        url = reverse('accounts:login')
        response = self.client.post(url, {'username': 'student1', 'password': 'securepassword123'})
        self.assertEqual(response.status_code, 302)

    def test_staff_login_permits_operator(self):
        """Staff login must succeed for operator/staff account."""
        url = reverse('accounts:staff_login')
        response = self.client.post(url, {'username': 'operator1', 'password': 'operatorpass123'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard:overview'))

    def test_staff_login_denies_regular_customer(self):
        """Staff login must reject a regular customer who lacks operator permissions."""
        url = reverse('accounts:staff_login')
        response = self.client.post(url, {'username': 'student1', 'password': 'securepassword123'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Access restricted")

    def test_order_history_requires_login(self):
        """Anonymous user trying to access order history must be redirected to login."""
        url = reverse('accounts:order_history')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
