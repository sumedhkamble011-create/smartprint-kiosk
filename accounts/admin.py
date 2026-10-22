"""
accounts/admin.py
=================
Django admin integration for UserProfile and custom User admin display.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    """Allows editing the profile (role, phone) directly from the Django User admin page."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile & Roles'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'get_role', 'is_staff', 'is_active')

    def get_role(self, instance):
        if hasattr(instance, 'profile'):
            return instance.profile.get_role_display()
        return "No profile"
    get_role.short_description = 'Kiosk Role'


# Re-register UserAdmin with the profile inline
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
