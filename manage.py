#!/usr/bin/env python
"""
manage.py - Django's command-line utility for administrative tasks.
===================================================================
Project: QR-Based Smart Document Printing and Automated Kiosk System (SmartPrintKiosk)

This file allows you to:
- Run migrations:       python manage.py migrate
- Create migrations:    python manage.py makemigrations
- Start the web server: python manage.py runserver
- Create admin user:    python manage.py createsuperuser
- Run test suite:       python manage.py test
- Run print worker:     python manage.py run_print_worker
"""
import os
import sys


def main():
    """Run administrative tasks."""
    # Set the default settings module for the 'SmartPrintKiosk' project
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
