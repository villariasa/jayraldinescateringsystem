# Windows Setup Guide — Brand New PC

This guide walks you through installing **Jayraldine's Catering** on a Windows
PC that has nothing installed yet — no Python, no PostgreSQL, nothing. Follow
it top to bottom and you'll end up with a working app you can launch by
double-clicking `run.bat`.

There are two ways to do this:

- **Option A — Automated (recommended).** One script (`setup.ps1`) installs
  everything for you.
- **Option B — Manual.** Do every step by hand. Use this only if the
  automated script fails or you want full control.

For a platform-agnostic overview of what the scripts do and how the app is
configured, see [`SETUP_GUIDE.md`](./SETUP_GUIDE.md).

---

## Before You Start

- **Windows 10 or 11**, 64-bit.
- An internet connection (the script downloads Python and PostgreSQL
  installers if they're missing — roughly 100–150 MB total).
- You do **not** need admin rights for most of this, but the PostgreSQL
  installer may prompt for elevation (UAC) — accept it if asked.
- The project folder copied onto the machine, e.g. via USB drive, network
  share, or `git clone`. This guide assumes the folder is at:
  `C:\Jayraldines\jayraldines_catering`

---

## Option A — Automated Setup (Recommended)

### 1. Copy the project folder onto the PC

Copy the entire `jayraldines_catering` folder to a permanent location, e.g.
`C:\Jayraldines\jayraldines_catering`. Avoid folders that need admin rights
to write to (like `C:\Program Files`).

### 2. Open the folder and run the setup script

1. Open the folder in File Explorer.
2. Right-click **`setup.ps1`** → **Run with PowerShell**.
   - If Windows shows "Windows protected your PC", click **More info** →
     **Run anyway**. This happens because the script isn't digitally signed,
     not because it's unsafe.
   - If PowerShell refuses to run the script at all (execution policy
     error), open PowerShell manually instead:
     ```powershell
     cd C:\Jayraldines\jayraldines_catering
     Set-ExecutionPolicy -Scope Process Bypass
     .\setup.ps1
     ```

### 3. Follow the prompts

The script will, in order:

1. **Detect or install Python 3.11+.** If missing, it silently downloads and
   installs Python 3.12 for all users and adds it to PATH.
2. **Detect or install PostgreSQL 16.** If missing, it downloads the
   installer and opens it for you. When the installer window appears:
   - Keep the **default install directory**.
   - Set the **postgres superuser password to `12345678`** (or remember
     whatever you choose — you'll need it in the next step).
   - Keep the **default port `5432`**.
   - Click through the rest with defaults, then finish, and come back to the
     PowerShell window and press **ENTER**.
3. **Create a Python virtual environment** (`venv\`) inside the project
   folder.
4. **Install all required Python packages** (PySide6, psycopg2, reportlab,
   openpyxl, Pillow) from `requirements.txt`.
5. **Create and initialize the database**, prompting you for the PostgreSQL
   password (press ENTER to accept the default `12345678`, or type the one
   you set during PostgreSQL install).
6. **Verify the database connection** works from Python.
7. **Write `run.bat`**, a launcher that activates the environment and starts
   the app with the correct DB password baked in.

At the end you'll be asked **"Launch the app now?"** — type `y` and press
ENTER, or just double-click `run.bat` any time afterward.

### 4. Day-to-day use

From now on, to start the app:

- Double-click **`run.bat`** in the project folder.

No further setup is needed unless you move the project to a different
machine.

---

## Option B — Manual Setup (Step by Step)

Use this if the automated script fails partway through, or you want to
understand/control each step.

### 1. Install Python 3.11 or newer

1. Go to https://www.python.org/downloads/ and download the latest Python
   3.x installer (64-bit).
2. Run the installer. **Check "Add python.exe to PATH"** at the bottom of
   the first screen before clicking Install.
3. Verify in a new Command Prompt:
   ```cmd
   python --version
   ```
   It should print `Python 3.11.x` or later.

### 2. Install PostgreSQL

1. Go to https://www.postgresql.org/download/windows/ and download the
   PostgreSQL 16 installer (EnterpriseDB build).
2. Run it. During install:
   - Keep the default install directory and default port `5432`.
   - Set a superuser (`postgres`) password — remember it. This guide uses
     `12345678` as the example/default.
   - You can uncheck "Stack Builder" at the end — it's not needed.
3. Verify `psql` is available. Open a **new** Command Prompt:
   ```cmd
   psql --version
   ```
   If that fails with "command not found", add PostgreSQL's `bin` folder to
   your PATH, e.g.:
   ```
   C:\Program Files\PostgreSQL\16\bin
   ```
   (System Properties → Environment Variables → Path → Edit → New)

### 3. Copy the project and create a virtual environment

```cmd
cd C:\Jayraldines\jayraldines_catering
python -m venv venv
venv\Scripts\activate
```

Your prompt should now start with `(venv)`.

### 4. Install Python dependencies

```cmd
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pillow
```

### 5. Create the database and load the schema

Set the password so `psql` doesn't prompt for it each time (replace
`12345678` with your actual postgres password):

```cmd
set PGPASSWORD=12345678
```

Run the main schema (this creates the `jayraldines_catering` database and
all tables):

```cmd
psql -U postgres -h localhost -p 5432 -d postgres -f jayraldines_catering_clean.sql
```

Then apply the migrations, in this order:

```cmd
psql -U postgres -h localhost -p 5432 -d jayraldines_catering -f cebu_address_migration.sql
psql -U postgres -h localhost -p 5432 -d jayraldines_catering -f confirmed_only_views_migration.sql
psql -U postgres -h localhost -p 5432 -d jayraldines_catering -f analytics_functions_migration.sql
```

> If `occasions_migration.sql` reports the table already exists, that's
> fine — it's included in the main schema already but kept as a
> standalone migration for older databases.

### 6. Verify the connection

```cmd
python -c "import utils.db as db; print('OK' if db.connect() else 'FAILED')"
```

If it prints `FAILED`, double-check:
- PostgreSQL service is running (Services app → look for `postgresql-x64-16`).
- The password matches what you set in step 2.
- Port `5432` isn't blocked by a firewall or used by another Postgres
  instance.

### 7. Run the app

```cmd
set DB_PASSWORD=12345678
python main.py
```

(Optional) Create a `run.bat` so you don't have to repeat this:

```bat
@echo off
cd /d "%~dp0"
call venv\Scripts\activate
set DB_PASSWORD=12345678
python main.py
pause
```

Save this as `run.bat` in the project folder; double-click it to launch the
app from then on.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Running scripts is disabled on this system" | Run `Set-ExecutionPolicy -Scope Process Bypass` in PowerShell before `.\setup.ps1`, or right-click the script and choose "Run with PowerShell" instead of double-clicking. |
| "Windows protected your PC" (SmartScreen) | Click **More info** → **Run anyway**. The script is unsigned but not malicious — you can review its contents in a text editor first. |
| `python` / `psql` not recognized after install | Close and reopen Command Prompt/PowerShell (PATH changes don't apply to already-open windows). If still missing, add the install folder to PATH manually and reopen. |
| PostgreSQL installer never appears / setup script hangs | The download may be blocked by a corporate firewall or antivirus. Install PostgreSQL manually from postgresql.org and re-run `setup.ps1` — it will detect the existing install. |
| Database connection failed | Confirm the PostgreSQL service is **running** (Services app), the password is correct, and nothing else is using port 5432. |
| App window doesn't open / crashes immediately | Run `python main.py` from a terminal (not `run.bat`) so you can read the error message printed to the console. |
| Need to start over with a clean database | Re-run `setup.ps1` — when it detects the existing `jayraldines_catering` database it will ask **"Drop and recreate it?"**; answer `y`. |

---

## Uninstalling / Resetting

- **Remove the app:** delete the project folder (`venv`, `run.bat`, etc. are
  all self-contained inside it).
- **Remove the database only:**
  ```cmd
  set PGPASSWORD=12345678
  psql -U postgres -h localhost -p 5432 -d postgres -c "DROP DATABASE jayraldines_catering;"
  ```
- **Remove PostgreSQL entirely:** use "Add or Remove Programs" in Windows
  Settings and uninstall PostgreSQL.
- **Remove Python entirely:** use "Add or Remove Programs" and uninstall
  Python 3.x.
