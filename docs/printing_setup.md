# SmartPrintKiosk - Print Queue & Hardware Setup Guide

## 1. Overview of the Two-Stage Print Queue Architecture

SmartPrintKiosk implements an enterprise-grade, two-stage print execution model:

```
[Customer Uploads & Pays]
           │
           ▼
[Payment Verified by Server]
           │
           ▼
[PrintJob Enqueued in Buffer (Idempotent)]
           │
           ├─────────────────────────────────────────┐
           ▼                                         ▼
   [Stage A: Simulation Mode]              [Stage B: Physical Worker]
   • Default development mode             • Windows-side daemon
   • Safe for college demonstration        • Sends jobs to physical printer
   • Virtual spooling in web buffer       • Requires PRINT_MODE=worker
   • Operator controls in Dashboard       • Win32 Print API / PowerShell
```

---

## 2. Stage A: Safe Simulation Mode (Default)

In Simulation Mode:
- **Zero physical paper or ink is consumed.**
- When a customer pays, an order transitions to `QUEUED` and creates a `PrintJob` buffer record.
- The shop operator can view the queued job in `http://127.0.0.1:8000/dashboard/`.
- The operator clicks **"Start Printing"** (moves to `PROCESSING`) and then **"Mark Ready"** (moves to `READY`).
- The customer's mobile tracking screen immediately alerts them with:
  *"Your Prints are Ready for Collection!"*
- Perfect for demonstrations, viva examinations, and college exhibitions.

---

## 3. Stage B: Optional Windows Physical Print Worker

For actual production or live counter deployment, SmartPrintKiosk includes a dedicated Windows background worker daemon: `printing/print_worker.py`.

### 3.1 How the Physical Worker Operates
1. The authorized shop computer runs the worker daemon using:
   ```powershell
   python manage.py run_print_worker
   ```
2. The worker polls the database every 5 seconds for orders matching:
   - `order_status = 'QUEUED'`
   - `payment_status = 'COMPLETED'`
   - `shop = 'default-kiosk'`
3. The worker validates:
   - File exists on disk in `media/uploads/`.
   - The file is not corrupted.
   - The order has not already been printed (Idempotency guarantee).
4. The worker delivers the file directly to the configured Windows printer driver using the Windows `PrintTo` shell handler.
5. Upon successful transmission, the order is updated to `READY` for collection.

### 3.2 Finding Installed Printers on Windows
To see which printers are installed on your Windows machine, open PowerShell and run:
```powershell
Get-Printer | Select-Object Name, Type, DriverName
```
Example output:
```
Name                     Type   DriverName
----                     ----   ----------
HP LaserJet Pro M404n    Local  HP LaserJet Pro M404
Microsoft Print to PDF   Local  Microsoft Print to PDF
OneNote for Windows 10   Local  OneNote
```

### 3.3 Configuring the Printer in SmartPrint Dashboard
1. Log into the Shop Dashboard: `http://127.0.0.1:8000/dashboard/settings/`
2. In the **"Configured Windows Printer Name"** field, enter the exact printer name (e.g. `HP LaserJet Pro M404n` or `Microsoft Print to PDF`).
3. Click **"Save Kiosk Settings"**.

### 3.4 Enabling Physical Printing in `.env`
Edit your `.env` file:
```ini
PRINT_MODE=worker
```

### 3.5 Starting the Windows Worker Daemon
Open a dedicated Windows PowerShell window, activate your virtual environment, and launch:
```powershell
.\.venv\Scripts\Activate.ps1
python manage.py run_print_worker --shop default-kiosk --poll 5
```
You will see:
```
[*] SmartPrint Worker started. Mode: PHYSICAL
[*] Shop: default-kiosk. Polling every 5s...
```
When an order is paid on the website, the worker will automatically detect it, spool the document to the Windows printer, and advance the order status.

---

## 4. Safety & Security Safeguards

1. **Unpaid Orders are Never Printed:** The worker enforces strict database-level checks. Any unpaid or cancelled job is immediately rejected.
2. **Idempotency Protection:** Repeated worker polls will never print the same order twice.
3. **No File Execution:** Uploaded files are treated purely as binary streams sent to the printer driver. They are NEVER executed as shell scripts or executables.
4. **Isolated Media Storage:** Uploaded files are saved with randomized UUID paths (`media/uploads/YYYY/MM/DD/<uuid>.<ext>`) outside of any web root.
