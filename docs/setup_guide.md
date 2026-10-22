# SmartPrintKiosk - Comprehensive Setup & PostgreSQL Guide

## 1. Introduction
**QR-Based Smart Document Printing and Automated Kiosk System (SmartPrintKiosk)** is an end-to-end self-service document printing solution built using Python, Django, PostgreSQL, and Bootstrap 5.

Customers scan a counter QR code, upload documents (PDF, Word, Images), select printing preferences, inspect real-time server-verified price calculations, complete a safe demo payment, and track the status of their print job in real time.

---

## 2. Windows Environment Setup

### 2.1 Verify Python Installation
Open Windows PowerShell and check that Python 3.10+ is installed:
```powershell
python --version
```
If Python is not installed or not in PATH, download Python from [python.org](https://www.python.org/) and check **"Add Python to PATH"** during installation.

### 2.2 Create & Activate Python Virtual Environment
Navigate to the project root folder:
```powershell
cd "c:\Users\pravi\Downloads\antigravtiy project - smartPRINT-1"
```
Create a virtual environment:
```powershell
python -m venv .venv
```
Activate the virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If you see an execution policy error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in PowerShell).*

### 2.3 Install Required Dependencies
With the virtual environment active, install all packages:
```powershell
pip install -r requirements.txt
```

---

## 3. Database Configuration (PostgreSQL & SQLite)

The application supports both PostgreSQL (the target production database) and SQLite (for offline development/testing).

### 3.1 PostgreSQL Installation & Service Verification
1. Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/download/windows/) if not already installed.
2. Verify that the PostgreSQL Windows service is running:
   ```powershell
   Get-Service *postgres*
   ```
3. If stopped, start it:
   ```powershell
   Start-Service postgresql-x64-16
   ```

### 3.2 Create PostgreSQL Database & User
Open `psql` command-line (or pgAdmin 4):
```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
```
Run the following SQL commands to create the database and user:
```sql
CREATE DATABASE smartprint_db;
CREATE USER postgres WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE smartprint_db TO postgres;
\q
```

### 3.3 Configure `.env` File
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Open `.env` in any text editor and configure:
```ini
DJANGO_SECRET_KEY=django-insecure-smartprint-kiosk-college-demo-key-2026-change-in-prod
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.5

# Toggle DB_ENGINE to 'postgresql' when PostgreSQL is ready:
DB_ENGINE=postgresql
DB_NAME=smartprint_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

PRINT_MODE=simulation
MAX_UPLOAD_SIZE_MB=15
DEFAULT_BW_RATE=2.00
DEFAULT_COLOR_RATE=10.00
```

> **Note:** If PostgreSQL is not yet configured on your machine, simply keep `DB_ENGINE=sqlite` in `.env`. Everything will work seamlessly with SQLite until you are ready to switch.

---

## 4. Database Migrations & Initial Data

### 4.1 Apply Migrations
Create tables in your database:
```powershell
python manage.py migrate
```

### 4.2 Seed Initial Kiosk Shop & Accounts
We have built a convenient one-command seeder:
```powershell
python manage.py seed_kiosk_data
```
This automatically sets up:
1. Default Print Shop: **SmartPrint Campus Kiosk**
2. Counter QR code pre-generated for counter scanning
3. Superuser/Shop Owner: `admin` / `adminpassword123`
4. Demo Student Customer: `student1` / `studentpassword123`

---

## 5. Starting the Development Server

Start the local server:
```powershell
python manage.py runserver
```
Open your browser to:
- **Public Kiosk Home:** `http://127.0.0.1:8000/`
- **Shop Staff Dashboard:** `http://127.0.0.1:8000/dashboard/`
- **Django Admin Portal:** `http://127.0.0.1:8000/admin/`

---

## 6. Testing Mobile QR-Code Scanning on Local Wi-Fi

1. Connect your laptop and your mobile smartphone to the **same Wi-Fi network**.
2. Find your computer's local IP address:
   ```powershell
   ipconfig
   ```
   Look for `IPv4 Address`, for example: `192.168.1.15`.
3. Add this IP to `DJANGO_ALLOWED_HOSTS` in your `.env` file:
   ```ini
   DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,192.168.1.15
   ```
4. Start the server listening on all network interfaces:
   ```powershell
   python manage.py runserver 0.0.0.0:8000
   ```
5. Open `http://127.0.0.1:8000/dashboard/qr-code/` on your computer. Enter `http://192.168.1.15:8000` in the "Host Address" box and click **Regenerate QR**.
6. Point your mobile phone camera at the screen QR code. Your mobile phone will open the SmartPrint portal instantly!
