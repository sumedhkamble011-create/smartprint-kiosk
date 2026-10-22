# QR-Based Smart Document Printing and Automated Kiosk System (SmartPrintKiosk)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Django](https://img.shields.io/badge/Django-5.1%2B-green.svg)
![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)
![Bootstrap](https://img.shields.io/badge/Frontend-Bootstrap%205-purple.svg)
![Tests](https://img.shields.io/badge/Tests-33%20Passed-brightgreen.svg)

A complete, functional, beginner-friendly college mini-project for an automated, self-service campus/shop document printing kiosk. Customers scan a counter QR code on their smartphone, upload documents (PDF, Word, Images), select printing preferences, inspect real-time server-verified price calculations, complete a safe demo payment, and track the status of their print job in real time.

---

## Table of Contents
1. [Key Features](#1-key-features)
2. [Technology Stack](#2-technology-stack)
3. [Prerequisites](#3-prerequisites)
4. [Quick Start on Windows (PowerShell Commands)](#4-quick-start-on-windows)
5. [Database Configuration: PostgreSQL & SQLite](#5-database-configuration)
6. [Default Accounts & Initial Data](#6-default-accounts--initial-data)
7. [Customer Workflow Walkthrough](#7-customer-workflow-walkthrough)
8. [Shop Owner & Operator Dashboard](#8-shop-owner--operator-dashboard)
9. [QR-Code Functionality & Mobile Wi-Fi Testing](#9-qr-code-functionality--mobile-wi-fi-testing)
10. [Print Execution Engine: Simulation vs Physical Worker](#10-print-execution-engine)
11. [Running Automated Tests](#11-running-automated-tests)
12. [Where to Customize / Key Files to Edit](#12-where-to-customize--key-files-to-edit)
13. [Troubleshooting & Common Questions](#13-troubleshooting--common-questions)

---

## 1. Key Features

- **Mobile First QR Workflow:** Counter QR code opens the kiosk interface directly on customer smartphones without requiring app installation.
- **Multi-Format Document Support:**
  - PDF (`.pdf`) with automatic, pure-Python page count inspection.
  - Microsoft Word (`.docx`, `.doc`) parsed safely.
  - Image files (`.jpg`, `.jpeg`, `.png`) detected as standard single-page prints.
- **Server-Side Price Calculation Engine:**
  - Independent rates for Black & White (default ₹2/page) and Full Colour (default ₹10/page).
  - Custom page range support (e.g. `1-3, 5, 8-10`).
  - Duplex double-sided sheet conservation discount calculation.
  - Frontend estimates are interactive, but final prices are strictly enforced on the server using Python's `Decimal` type.
- **Safe Demo Payment Gateway:**
  - Clearly labelled **"DEMO PAYMENT — NO REAL MONEY CHARGED"**.
  - Supports both **Success** and **Declined/Failure** simulation paths for comprehensive evaluation.
  - Idempotent transaction ledger prevents duplicate orders and double billing.
- **Live Real-Time Order Tracking:**
  - Cryptographically secure guest tracking UUID tokens (order URLs cannot be guessed).
  - Live status polling badge updates in real time from `Queued` &rarr; `Printing` &rarr; `Ready for Collection`.
- **Shop-Owner Dashboard:**
  - Executive overview cards: Total Orders, Revenue, In-Queue Jobs, Ready Orders, Completed Orders.
  - Full order search and filter system.
  - Validated status transitions (Queued &rarr; Processing &rarr; Ready &rarr; Completed).
  - Web-based rate configuration (B&W rate, colour rate, duplex discount, copy limits).
  - Counter QR code download and custom LAN IP regenerator.
- **Two-Stage Print Queue:**
  - **Stage A (Default):** Safe simulation mode for college presentations (zero ink or paper wasted).
  - **Stage B (Optional):** Windows background worker daemon that spools jobs directly to physical printers.

---

## 2. Technology Stack

- **Backend:** Python 3.12, Django 5.1
- **Database:** PostgreSQL (with SQLite development fallback)
- **Database Access:** Django ORM
- **Frontend:** HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Vanilla JavaScript
- **PDF & File Inspection:** `pypdf`, `python-docx`, `pillow`
- **QR Code Generation:** `qrcode[pil]`
- **Environment Configuration:** `python-dotenv`
- **Testing Framework:** Django Automated Test Runner (33 automated unit and integration tests)

---

## 3. Prerequisites

Before running the application on Windows, verify:
1. **Python 3.10+** is installed on your computer.
2. **PowerShell** or Command Prompt.
3. *(Optional)* **PostgreSQL 14+** (if you wish to connect PostgreSQL immediately; SQLite is also pre-configured as an initial fallback).

---

## 4. Quick Start on Windows

Open **Windows PowerShell** and execute the following exact commands:

```powershell
# 1. Navigate to the project directory
cd "c:\Users\pravi\Downloads\antigravtiy project - smartPRINT-1"

# 2. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Apply database migrations
python manage.py migrate

# 4. Seed initial shop counter, pricing, QR code, and default users
python manage.py seed_kiosk_data

# 5. Start the development server
python manage.py runserver
```

Open your browser and navigate to:
- **Public Kiosk Home:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Shop Operator Dashboard:** [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
- **Django Admin Interface:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## 5. Database Configuration

The application is engineered to work smoothly with **PostgreSQL** as the main target database, while allowing immediate zero-configuration testing via SQLite.

### Connecting PostgreSQL
When your PostgreSQL installation is complete:
1. Open `.env` in any text editor.
2. Change `DB_ENGINE` to `postgresql` and specify your PostgreSQL credentials:
   ```ini
   DB_ENGINE=postgresql
   DB_NAME=smartprint_db
   DB_USER=postgres
   DB_PASSWORD=your_postgres_password
   DB_HOST=localhost
   DB_PORT=5432
   ```
3. Create the database in PostgreSQL:
   ```sql
   CREATE DATABASE smartprint_db;
   ```
4. Run migrations:
   ```powershell
   python manage.py migrate
   python manage.py seed_kiosk_data
   ```

### Using SQLite (Development / Demo Mode)
In your `.env` file, simply set:
```ini
DB_ENGINE=sqlite
```
Django will automatically use the local `db.sqlite3` file without requiring any PostgreSQL service.

---

## 6. Default Accounts & Initial Data

The `seed_kiosk_data` command creates these initial credentials for demonstration:

| Role | Username | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Shop Owner / Admin** | `admin` | `adminpassword123` | Access to Shop Dashboard, rates, queue, and Django Admin |
| **Student Customer** | `student1` | `studentpassword123` | Pre-registered customer account with past order history |
| **Guest Customer** | *(None)* | *(None)* | Customers can order and track prints without registering! |

---

## 7. Customer Workflow Walkthrough

1. **Scan QR:** Customer scans the counter QR code to open `http://127.0.0.1:8000/`.
2. **Upload Document:** Selects a PDF, Word file, or image. The server validates extension, file size (max 15MB), magic bytes signature, and detects the total page count.
3. **Configure Preferences:**
   - Color Mode: Black & White (₹2.00/p) vs Full Colour (₹10.00/p).
   - Copies: 1 to 50 copies.
   - Pages: All Pages or Custom Page Range (e.g. `1-3, 5`).
   - Sides: Single-Sided vs Double-Sided (Duplex).
   - Real-time live estimate panel dynamically updates as options are toggled.
4. **Order Summary:** Detailed itemized bill before payment.
5. **Demo Payment:** Clearly marked simulator. Supports simulating **SUCCESS** (authorizes print) or **FAILURE** (tests error handling).
6. **Order Confirmation:** Order receives unique identifier (`SPK-YYYYMMDD-XXXXXX`) and a personalized Order Tracking QR Code.
7. **Live Tracking:** Real-time polling updates when the shop marks the prints as **Ready for Collection**.

---

## 8. Shop Owner & Operator Dashboard

Access at: `http://127.0.0.1:8000/dashboard/` (Log in with `admin` / `adminpassword123`).

- **Overview Cards:** Total orders, verified revenue, active print queue items, ready orders, completed orders.
- **Workflow State Management:**
  - `Queued` &rarr; `Processing` (Spooling to printer)
  - `Processing` &rarr; `Ready` (Ready for counter pickup)
  - `Ready` &rarr; `Completed` (Handed over to student)
  - `Failed` &rarr; `Queued` (Retry failed print jobs)
- **Manage Pricing:** Update B&W per-page rate, colour per-page rate, duplex discount, and max copy limit from the browser.
- **Counter QR Standee:** View and download high-resolution PNG for printing counter standees.

---

## 9. QR-Code Functionality & Mobile Wi-Fi Testing

When testing locally on your PC, `127.0.0.1` works only inside your computer's browser. To scan the QR code with an actual smartphone:
1. Connect your laptop and phone to the **same Wi-Fi network**.
2. Find your laptop's local IP address:
   ```powershell
   ipconfig
   ```
   *(e.g., `192.168.1.15`)*.
3. Add this IP to `DJANGO_ALLOWED_HOSTS` in `.env`:
   ```ini
   DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.15
   ```
4. Start Django listening on all interfaces:
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```
5. Go to `http://127.0.0.1:8000/dashboard/qr-code/`, type `http://192.168.1.15:8000`, and click **Regenerate QR**.
6. Scan the QR on your screen with your smartphone camera. The upload portal will open directly on your mobile device!

---

## 10. Print Execution Engine

### Stage A: Simulation Mode (Default)
Safe development mode. Print jobs are spooled virtually in the database buffer without wasting paper or ink. The shop owner clicks buttons in the dashboard to move orders from Queued to Ready.

### Stage B: Windows Physical Print Worker
To connect an actual physical printer:
1. Set `PRINT_MODE=worker` in `.env`.
2. Configure your printer name in Dashboard &rarr; Settings (e.g. `HP LaserJet Pro M404`).
3. Run the background worker daemon in PowerShell:
   ```powershell
   python manage.py run_print_worker
   ```
See [docs/printing_setup.md](docs/printing_setup.md) for complete hardware documentation.

---

## 11. Running Automated Tests

Run the full automated test suite containing 33 unit and integration tests:

```powershell
python manage.py test
```

### Actual Test Results
```
Creating test database for alias 'default'...
Found 33 test(s).
System check identified no issues (0 silenced).
.................................
----------------------------------------------------------------------
Ran 33 tests in 27.988s

OK
Destroying test database for alias 'default'...
```

**Tested Components:**
- Page range parsing, validation, and boundary checking
- Black & White and Colour pricing formulas
- Duplex double-sided sheet conservation discounts
- Copies limit enforcement
- File extension, size, and magic byte signature verification
- Document page count detection (PDF, images, docx)
- Order lifecycle states and prevention of illegal status jumps
- Print worker simulation and unpaid order rejection
- Customer registration, login, and staff permission guards
- Demo payment verification, failure simulation, and idempotency
- Shop dashboard access control and status advancement actions

---

## 12. Where to Customize / Key Files to Edit

- **Pricing Rates:** Edit via `http://127.0.0.1:8000/dashboard/pricing/` or change default fallbacks in `.env` / `config/settings.py`.
- **Max Upload Limit:** Set `MAX_UPLOAD_SIZE_MB=15` in `.env`.
- **Visual Design & CSS:** Edit `static/css/style.css` (custom colors, cards, badges).
- **Frontend JavaScript & Polling:** Edit `static/js/main.js` (dynamic price calculator, live status poller).
- **Supported File Types:** Edit `ALLOWED_DOCUMENT_EXTENSIONS` in `config/settings.py`.
- **Pricing Calculation Logic:** Edit `printing/pricing.py`.
- **File Validation & Signatures:** Edit `printing/validators.py`.
- **Print Worker Daemon:** Edit `printing/print_worker.py`.

---

## 13. Troubleshooting & Common Questions

**Q: I get `ExecutionPolicy` error when running `Activate.ps1` in PowerShell?**
A: Run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in PowerShell, then re-run `.\.venv\Scripts\Activate.ps1`.

**Q: Can a guest track an order without logging in?**
A: Yes! Every order generates an unguessable UUID tracking token. Guests can bookmark their confirmation link, scan the tracking QR code, or enter their Order ID on `/track/`.

**Q: How do I switch to PostgreSQL later?**
A: Simply change `DB_ENGINE=postgresql` in `.env`, provide your PostgreSQL password, and run `python manage.py migrate`. All tables and relationships are fully PostgreSQL-ready.
