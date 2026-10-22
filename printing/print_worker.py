"""
printing/print_worker.py
========================
Shop-Side Print Worker: Stage A (Safe Simulation) and Stage B (Windows Physical Printing).

Stage A: Simulation Mode (Default)
- No physical printer commands are ever sent.
- Processes jobs virtually, logs actions, and transitions statuses safely.

Stage B: Optional Windows Print Worker
- Run on the authorized Windows shop computer with:
    python manage.py run_print_worker
- Retrieves PAID & QUEUED jobs for the local shop.
- Verifies order payment authorization and file safety.
- Sends PDF or image file to the configured Windows printer using Windows shell printing.
- Never prints unpaid, cancelled, or completed orders.
- Records attempts, logs results, and handles errors idempotently.
"""

import os
import sys
import time
import logging
from django.conf import settings
from django.utils import timezone
from .models import PrintJob, PrintOrder, Shop

logger = logging.getLogger(__name__)


class KioskPrintWorker:
    """
    Worker daemon responsible for polling and executing print jobs.
    """
    def __init__(self, shop_slug=None, poll_interval=5):
        self.shop_slug = shop_slug or "default-kiosk"
        self.poll_interval = poll_interval
        self.is_simulation = (settings.PRINT_MODE != 'worker')
        self.running = False

    def get_shop(self):
        try:
            return Shop.objects.get(slug=self.shop_slug)
        except Shop.DoesNotExist:
            return None

    def process_single_job(self, job: PrintJob) -> bool:
        """
        Executes a single print job. Verifies safety, payment, and file integrity.
        """
        order = job.order

        # 1. Verification of Payment and Eligibility
        if order.payment_status != PrintOrder.PAYMENT_COMPLETED:
            job.error_message = f"Refused: Order {order.order_number} is NOT paid."
            job.job_status = PrintJob.JOB_FAILED
            job.save()
            return False

        if order.order_status in [PrintOrder.STATUS_COMPLETED, PrintOrder.STATUS_CANCELLED]:
            return False

        # 2. Mark Processing
        job.job_status = PrintJob.JOB_PROCESSING
        job.attempt_count += 1
        job.processed_at = timezone.now()
        job.save()

        order.order_status = PrintOrder.STATUS_PROCESSING
        order.save(update_fields=['order_status', 'updated_at'])

        # 3. Execution (Simulation vs Physical)
        doc = order.document
        file_path = doc.file.path

        if not os.path.exists(file_path):
            error = f"Document file missing on disk: {file_path}"
            job.error_message = error
            job.job_status = PrintJob.JOB_FAILED
            job.save()
            order.order_status = PrintOrder.STATUS_FAILED
            order.save(update_fields=['order_status', 'updated_at'])
            return False

        if self.is_simulation:
            # Stage A: Safe Simulation
            time.sleep(2)  # Simulate printer spooling delay
            job.job_status = PrintJob.JOB_PRINTED
            job.completed_at = timezone.now()
            job.error_message = "Simulated printing succeeded without physical printer output."
            job.save()

            order.order_status = PrintOrder.STATUS_READY
            order.save(update_fields=['order_status', 'updated_at'])
            return True
        else:
            # Stage B: Windows Physical Printing
            shop = order.shop
            printer_name = shop.configured_printer_name

            if not printer_name:
                error = "Physical printing failed: No Windows printer name configured for this shop."
                job.error_message = error
                job.job_status = PrintJob.JOB_FAILED
                job.save()
                order.order_status = PrintOrder.STATUS_FAILED
                order.save(update_fields=['order_status', 'updated_at'])
                return False

            success, msg = self._send_to_windows_printer(file_path, printer_name, order.copies)
            if success:
                job.job_status = PrintJob.JOB_PRINTED
                job.completed_at = timezone.now()
                job.error_message = msg
                job.save()

                order.order_status = PrintOrder.STATUS_READY
                order.save(update_fields=['order_status', 'updated_at'])
                return True
            else:
                job.job_status = PrintJob.JOB_FAILED
                job.error_message = msg
                job.save()

                order.order_status = PrintOrder.STATUS_FAILED
                order.save(update_fields=['order_status', 'updated_at'])
                return False

    def _send_to_windows_printer(self, file_path: str, printer_name: str, copies: int) -> tuple[bool, str]:
        """
        Sends file to Windows printer using win32api or ShellExecute.
        """
        if sys.platform != 'win32':
            return False, f"Physical printing is only supported on Windows host (Current: {sys.platform})."

        try:
            import win32api
            import win32print

            # Verify printer exists in Windows registry
            installed_printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            if printer_name not in installed_printers:
                return False, f"Printer '{printer_name}' not found. Available printers: {', '.join(installed_printers)}"

            # Print using ShellExecute
            for _ in range(copies):
                win32api.ShellExecute(
                    0,
                    "printto",
                    file_path,
                    f'"{printer_name}"',
                    ".",
                    0
                )
            return True, f"Sent {copies} copy/copies to Windows printer '{printer_name}'."
        except ImportError:
            # Fallback using Windows rundll32 or powershell Start-Process
            import subprocess
            try:
                cmd = f'Start-Process -FilePath "{file_path}" -Verb PrintTo -ArgumentList "{printer_name}" -PassThru | Out-Null'
                subprocess.run(["powershell", "-Command", cmd], check=True, timeout=15)
                return True, f"Sent to Windows printer '{printer_name}' via PowerShell PrintTo verb."
            except Exception as e:
                return False, f"Failed to send to printer via fallback: {str(e)}"
        except Exception as exc:
            return False, f"Windows print error: {str(exc)}"

    def run_worker_loop(self):
        """
        Continuous polling loop for the print worker.
        """
        self.running = True
        print(f"[*] SmartPrint Worker started. Mode: {'SIMULATION' if self.is_simulation else 'PHYSICAL'}")
        print(f"[*] Shop: {self.shop_slug}. Polling every {self.poll_interval}s...")

        while self.running:
            try:
                # Find queued jobs
                eligible_jobs = PrintJob.objects.filter(
                    job_status=PrintJob.JOB_QUEUED,
                    order__shop__slug=self.shop_slug,
                    order__payment_status=PrintOrder.PAYMENT_COMPLETED
                ).order_by('created_at')

                for job in eligible_jobs:
                    print(f"[*] Processing PrintJob #{job.id} (Order: {job.order.order_number})...")
                    self.process_single_job(job)

            except Exception as exc:
                print(f"[!] Worker exception: {exc}")

            time.sleep(self.poll_interval)
