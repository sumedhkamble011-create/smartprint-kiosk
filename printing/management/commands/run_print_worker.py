"""
Command to start the SmartPrint Kiosk print worker daemon.
Usage:
    python manage.py run_print_worker
    python manage.py run_print_worker --shop default-kiosk --poll 5
"""

from django.core.management.base import BaseCommand
from printing.print_worker import KioskPrintWorker


class Command(BaseCommand):
    help = "Runs the print worker loop to process paid and queued print jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            '--shop',
            type=str,
            default='default-kiosk',
            help='Shop slug to process jobs for (default: default-kiosk)'
        )
        parser.add_argument(
            '--poll',
            type=int,
            default=5,
            help='Polling interval in seconds (default: 5)'
        )

    def handle(self, *args, **options):
        shop_slug = options['shop']
        poll = options['poll']
        self.stdout.write(self.style.SUCCESS(f"Starting SmartPrint Worker for shop '{shop_slug}'..."))
        worker = KioskPrintWorker(shop_slug=shop_slug, poll_interval=poll)
        try:
            worker.run_worker_loop()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Print worker stopped by operator."))
