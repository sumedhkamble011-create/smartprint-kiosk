"""
accounts/views.py
=================
Views for customer registration, customer login, staff dashboard login,
logout, user profile, and customer order history.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomerRegistrationForm, CustomerLoginForm, StaffLoginForm
from .models import UserProfile


def customer_register(request):
    """
    Renders customer registration form and registers a new customer.
    If already logged in, redirects to the kiosk home.
    """
    if request.user.is_authenticated:
        return redirect('printing:home')

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to SmartPrint Kiosk, {user.username}! Your account has been created.")
            return redirect('printing:home')
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def customer_login(request):
    """
    Handles customer authentication.
    """
    if request.user.is_authenticated:
        return redirect('printing:home')

    if request.method == 'POST':
        form = CustomerLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            next_url = request.GET.get('next') or request.POST.get('next')
            return redirect(next_url if next_url else 'printing:home')
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = CustomerLoginForm()

    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', '')
    })


def staff_login(request):
    """
    Dedicated login view for shop owners and operators.
    Verifies staff/operator permissions and redirects to the shop dashboard.
    """
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.is_shop_operator:
            return redirect('dashboard:overview')
        elif request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard:overview')

    if request.method == 'POST':
        form = StaffLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Staff access granted. Welcome, {user.username}!")
            return redirect('dashboard:overview')
        else:
            messages.error(request, "Staff login failed. Check credentials or operator permissions.")
    else:
        form = StaffLoginForm()

    return render(request, 'accounts/staff_login.html', {'form': form})


def user_logout(request):
    """
    Logs out the current user and redirects to the kiosk home.
    """
    logout(request)
    messages.info(request, "You have been logged out safely.")
    return redirect('printing:home')


@login_required
def order_history(request):
    """
    Displays the list of all print orders placed by the currently logged-in customer.
    Guest orders are not shown here unless claimed or placed while logged in.
    """
    from printing.models import PrintOrder
    orders = PrintOrder.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'accounts/order_history.html', {'orders': orders})


@login_required
def profile_view(request):
    """
    Allows a customer or staff user to review their profile details.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {
        'user': request.user,
        'profile': profile
    })
