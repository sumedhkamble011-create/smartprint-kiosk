"""
accounts/models.py
==================
Role and profile extensions for Django's built-in User authentication system.

Why this is needed:
Django provides a solid User model (username, email, password, is_staff, is_superuser).
For SmartPrintKiosk, we attach a UserProfile that stores:
- User role: CUSTOMER (default), STAFF (kiosk operator), or SHOP_OWNER (admin/manager).
- Phone number: for optional SMS or kiosk pickup identification.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """
    Extends Django's User model with kiosk-specific roles and contact information.
    """
    ROLE_CUSTOMER = 'CUSTOMER'
    ROLE_STAFF = 'STAFF'
    ROLE_SHOP_OWNER = 'SHOP_OWNER'

    ROLE_CHOICES = [
        (ROLE_CUSTOMER, 'Customer'),
        (ROLE_STAFF, 'Shop Staff / Operator'),
        (ROLE_SHOP_OWNER, 'Shop Owner / Manager'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        help_text="Underlying Django auth user."
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CUSTOMER,
        help_text="Determines dashboard access permissions."
    )
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        help_text="Contact number for order ready alerts."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_shop_operator(self):
        """Returns True if user has staff or owner privileges for the dashboard."""
        return self.role in [self.ROLE_STAFF, self.ROLE_SHOP_OWNER] or self.user.is_staff or self.user.is_superuser


# Signal receiver to automatically create or update UserProfile when a User is saved
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # If user is superuser or staff, give them SHOP_OWNER role by default
        default_role = UserProfile.ROLE_SHOP_OWNER if (instance.is_superuser or instance.is_staff) else UserProfile.ROLE_CUSTOMER
        UserProfile.objects.create(user=instance, role=default_role)
    else:
        # Save existing profile if present
        if hasattr(instance, 'profile'):
            instance.profile.save()
