"""
printing/urls.py
================
URL patterns for the primary customer kiosk flow.
"""

from django.urls import path
from . import views

app_name = 'printing'

urlpatterns = [
    # Kiosk Home & Shop landing
    path('', views.home_view, name='home'),

    # Step 1: Upload document
    path('upload/', views.upload_document_view, name='upload'),

    # Step 2: Preferences
    path('preferences/<uuid:upload_token>/', views.preferences_view, name='preferences'),

    # Dynamic pricing estimation API for JavaScript frontend
    path('api/price/<uuid:upload_token>/', views.calculate_estimate_api, name='api_price'),

    # Step 3: Order Summary & Review
    path('summary/<uuid:upload_token>/', views.order_summary_view, name='order_summary'),

    # Step 4: Confirmation
    path('confirmation/<str:order_number>/', views.order_confirmation_view, name='order_confirmation'),

    # Step 5: Guest & Live Order Tracking
    path('track/', views.track_order_view, name='track_order'),
    path('track/<uuid:tracking_token>/', views.track_order_view, name='track_order_token'),

    # Live Status API (polled by tracking page)
    path('api/status/<uuid:tracking_token>/', views.order_status_api, name='api_status'),

    # Secure document download
    path('download/<str:order_number>/', views.download_document_view, name='download_document'),
]
