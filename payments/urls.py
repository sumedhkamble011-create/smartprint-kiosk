"""
payments/urls.py
================
URL patterns for demo payments subsystem.
"""

from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('checkout/<str:order_number>/', views.checkout_payment_view, name='checkout'),
    path('process/<str:order_number>/', views.process_demo_payment_view, name='process'),
    path('result/<str:transaction_id>/', views.payment_result_view, name='payment_result'),
]
