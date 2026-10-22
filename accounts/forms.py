"""
accounts/forms.py
=================
Forms for Customer Registration, Customer Login, and Staff Login.
"""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import UserProfile


class CustomerRegistrationForm(forms.ModelForm):
    """
    User registration form for optional customer accounts.
    Allows customers to register to view their past orders.
    """
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a secure password (min 6 characters)'
        }),
        min_length=6,
        help_text="Must be at least 6 characters long."
    )
    password_confirm = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Retype your password'
        })
    )
    phone_number = forms.CharField(
        label="Phone Number (Optional)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 9876543210'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("A user with that username already exists. Please pick another.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match. Please verify and retype.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            # Ensure profile has customer role and save phone
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = UserProfile.ROLE_CUSTOMER
            profile.phone_number = self.cleaned_data.get("phone_number", "")
            profile.save()
        return user


class CustomerLoginForm(AuthenticationForm):
    """
    Standard customer login form styled with Bootstrap 5.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username or Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )


class StaffLoginForm(AuthenticationForm):
    """
    Staff and Shop-Owner login form.
    Validates credentials and verifies the user has shop-operator permissions.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Staff Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        # Verify the user actually has operator rights
        has_role = False
        if hasattr(user, 'profile'):
            has_role = user.profile.is_shop_operator
        if not (has_role or user.is_staff or user.is_superuser):
            raise ValidationError(
                "Access restricted: This account does not have shop operator or dashboard privileges."
            )
