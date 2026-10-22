"""
accounts/urls.py
================
URL routing for account management.
"""

from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.customer_register, name='register'),
    path('login/', views.customer_login, name='login'),
    path('staff-login/', views.staff_login, name='staff_login'),
    path('logout/', views.user_logout, name='logout'),
    path('order-history/', views.order_history, name='order_history'),
    path('profile/', views.profile_view, name='profile'),
]
