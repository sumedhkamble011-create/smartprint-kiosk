"""
seed_kiosk_data.py
==================
Populates the SmartPrint Kiosk database with default initial data:
1. Creates default Shop ("SmartPrint Campus Kiosk") and PricingSetting.
2. Generates initial counter QR code image.
3. Creates a default operator/superuser account:
   - Username: admin
   - Password: adminpassword123
   - Role: SHOP_OWNER
4. Creates a demo customer account:
   - Username: student1
   - Password: studentpassword123
   - Role: CUSTOMER
"""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile
from printing.models import Shop, PricingSetting


class Command(BaseCommand):
    help = "Seeds initial kiosk shop, default pricing, QR code, and admin/operator users."

    def handle(self, *args, **options):
        self.stdout.write("Initializing SmartPrint Kiosk initial setup...")

        # 1. Default Shop
        shop = Shop.get_default_shop()
        self.stdout.write(self.style.SUCCESS(f"[+] Shop initialized: '{shop.name}' (slug: {shop.slug})"))

        # 2. Generate Counter QR Code
        try:
            shop.generate_qr_code(base_url="http://127.0.0.1:8000")
            self.stdout.write(self.style.SUCCESS(f"[+] Counter QR code generated: {shop.qr_code_image.name}"))
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"[-] QR generation skipped: {exc}"))

        # 3. Superuser / Shop Owner
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                'email': "admin@smartprintkiosk.local",
                'first_name': "Kiosk",
                'last_name': "Administrator",
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password("adminpassword123")
            admin_user.save()
            profile = admin_user.profile
            profile.role = UserProfile.ROLE_SHOP_OWNER
            profile.phone_number = "9876543210"
            profile.save()
            self.stdout.write(self.style.SUCCESS("[+] Created default operator/admin user: admin / adminpassword123"))
        else:
            self.stdout.write("[*] Admin user already exists.")

        # 4. Demo Student Customer
        student_user, created = User.objects.get_or_create(
            username="student1",
            defaults={
                'email': "student1@college.edu",
                'first_name': "Rahul",
                'last_name': "Sharma",
                'is_staff': False,
                'is_superuser': False,
            }
        )
        if created:
            student_user.set_password("studentpassword123")
            student_user.save()
            profile = student_user.profile
            profile.role = UserProfile.ROLE_CUSTOMER
            profile.phone_number = "9123456780"
            profile.save()
            self.stdout.write(self.style.SUCCESS("[+] Created demo student user: student1 / studentpassword123"))
        else:
            self.stdout.write("[*] Student user already exists.")

        self.stdout.write(self.style.SUCCESS("\n[OK] SmartPrint Kiosk initial database seeding complete!"))
