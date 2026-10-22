"""
dashboard/urls.py
=================
URL patterns for the Shop-Owner and Operator Dashboard.
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard Overview & KPI Metrics
    path('', views.overview_view, name='overview'),

    # Order management & Search
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<str:order_number>/', views.order_detail_view, name='order_detail'),
    path('orders/<str:order_number>/status/', views.update_order_status_view, name='update_status'),

    # Pricing Configuration
    path('pricing/', views.pricing_settings_view, name='pricing_settings'),

    # Shop QR Code Management
    path('qr-code/', views.qr_management_view, name='qr_management'),

    # Shop & Printer Settings
    path('settings/', views.shop_settings_view, name='shop_settings'),
]
