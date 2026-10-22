"""
URL Configuration for SmartPrintKiosk project.
==============================================
QR-Based Smart Document Printing and Automated Kiosk System

URL patterns:
1. '' (root)      -> printing.urls: Customer flow (Upload, Preferences, Summary, Track)
2. 'accounts/'   -> accounts.urls: Registration, Login, Logout, Order history
3. 'payments/'   -> payments.urls: Demo payment flow, verification, result
4. 'dashboard/'  -> dashboard.urls: Shop-owner control panel, stats, pricing, QR
5. 'admin/'      -> Django administrative interface
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Built-in Django admin portal
    path('admin/', admin.site.urls),

    # User Accounts & Authentication routes (customer & staff)
    path('accounts/', include('accounts.urls', namespace='accounts')),

    # Customer Kiosk & Document Printing workflow
    path('', include('printing.urls', namespace='printing')),

    # Safe Demo Payment subsystem
    path('payments/', include('payments.urls', namespace='payments')),

    # Shop Owner Management Dashboard
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
]

# In development, serve uploaded media documents and generated QR codes
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Custom admin site titles
admin.site.site_header = "SmartPrint Kiosk Administration"
admin.site.site_title = "SmartPrint Kiosk Admin Portal"
admin.site.index_title = "Welcome to SmartPrint Kiosk Management"
