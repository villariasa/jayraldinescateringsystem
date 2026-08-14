# Jayraldine's Catering — Setup Guide

This is the general reference for getting the app running on **any** machine
(Windows or Linux), what the setup scripts do under the hood, and how to
configure or troubleshoot the environment afterward.

For a Windows-specific, from-scratch walkthrough (as if unboxing a brand new
PC), see [`SETUP_WINDOWS.md`](./SETUP_WINDOWS.md). This document covers both
platforms at a higher level and is the one to come back to for
configuration and troubleshooting after the initial install.

---

## What This App Is

A desktop catering management system built with:

- **Python 3.11+** and **PySide6** (Qt) for the UI
- **PostgreSQL** for the database
- **psycopg2** to talk to PostgreSQL
- **reportlab** / **openpyxl** for PDF receipts and Excel exports

All of this is declared in [`requirements.txt`](./requirements.txt).

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11 or newer | 3.12 recommended |
| PostgreSQL | 13–17 | Any of these work; scripts default to 16 |
| OS | Windows 10/11, or Ubuntu 22.04/24.04 | Other Linux distros likely work but aren't scripted |
| Disk space | ~500 MB | Python + PostgreSQL + dependencies |

You do **not** need to pre-install anything — the setup scripts described
below install Python and PostgreSQL for you if they're missing.

---

## Quick Start

### Windows

```powershell
cd path\to\jayraldines_catering
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

Then launch the app anytime with `run.bat`.

See [`SETUP_WINDOWS.md`](./SETUP_WINDOWS.md) for the full walkthrough and
manual fallback steps.

### Linux (Ubuntu 22.04 / 24.04, no sudo required)

```bash
cd path/to/jayraldines_catering
chmod +x setup_linux.sh
./setup_linux.sh
```

Then launch the app anytime with `./run.sh`.

The Linux script installs everything into your user's home directory
(`~/.local/pgsql`, `~/.local/pystand`, etc.) — no `sudo` or root access is
needed, which makes it safe to run on shared/managed machines.

---

## What the Setup Scripts Actually Do

Both `setup.ps1` (Windows) and `setup_linux.sh` (Linux) perform the same
logical steps, just with platform-appropriate tooling:

1. **Find or install Python 3.11+.**
   - Windows: checks `python`/`python3`/`py` on PATH and common install
     folders; downloads Python 3.12.4 from python.org if none found.
   - Linux: checks `python3`/`python` on PATH, or a previously-downloaded
     standalone Python under `~/.local/pystand`.
2. **Find or install PostgreSQL.**
   - Windows: checks PATH, common `Program Files` locations, the Windows
     registry, and running services before offering to download PostgreSQL
     16.
   - Linux: checks for an already-running/accessible PostgreSQL first, then
     falls back to a portable PostgreSQL 16 tarball extracted into
     `~/.local/pgsql` (no package manager or sudo needed).
3. **Set up the Python environment and install dependencies** from
   `requirements.txt` (plus Pillow, used for icon/image conversion).
   - Windows uses a standard `venv`.
   - Linux uses the standalone Python directly (no venv needed since it's
     already isolated).
4. **Initialize/start PostgreSQL** (Linux only — Windows installs it as a
   system service that starts automatically).
5. **Create the database and load the schema.**
   - Prompts for a PostgreSQL password (default `12345678` if you just
     press Enter).
   - If the `jayraldines_catering` database already exists, asks whether to
     drop and recreate it, or keep it and only apply missing migrations.
   - Runs the schema files in order — see [Database Schema
     Files](#database-schema-files) below.
6. **Verify the app can actually connect** to the database using the same
   `utils/db.py` module the app uses at runtime.
7. **Write a launcher** (`run.bat` on Windows, `run.sh` on Linux) with the
   database credentials and environment variables pre-configured, so future
   launches are a single double-click / command.

Both scripts are **idempotent** — safe to re-run. They detect what's already
installed/configured and skip those steps.

---

## Configuration

The app reads its database connection settings from environment variables,
with these fallbacks (see [`utils/db.py`](./utils/db.py)):

| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL server host |
| `DB_PORT` | `5432` | PostgreSQL server port |
| `DB_NAME` | `jayraldines_catering` | Database name |
| `DB_USER` | `postgres` | PostgreSQL role/user |
| `DB_PASSWORD` | `12345678` | PostgreSQL password |

The generated launcher (`run.bat` / `run.sh`) sets these automatically based
on what you entered during setup. To point the app at a different database
(e.g. a remote server), edit the `set` (Windows) or `export` (Linux) lines
at the top of the launcher, or set the variables in your shell/session
before running `python main.py` directly.

### Optional: startup profiling

Set `JAYRALDINES_PROFILE_STARTUP=1` before launching to print timing
breakdowns of each startup phase (Qt imports, DB connect, window build,
etc.) — useful when diagnosing slow launches. See `main.py`.

---

## Database Schema Files

Run in this order for a from-scratch install (the setup scripts already do
this for you):

1. **`jayraldines_catering_clean.sql`** — the main schema. Drops and
   recreates the `jayraldines_catering` database, then creates every table,
   view, and seed row (including Cebu address data). Start here for a fresh
   install.
2. **`cebu_address_migration.sql`** — address tables migration for
   *upgrading* an older database that predates the address feature. Not
   needed on a fresh install since the main schema already includes it.
3. **`occasions_migration.sql`** — adds the `occasions` table if missing.
4. **`confirmed_only_views_migration.sql`** — updates reporting views to
   only include confirmed bookings.
5. **`analytics_functions_migration.sql`** — adds SQL functions used by the
   analytics/reports screens (year-over-year comparisons, weekly summaries).

If you ever need to apply these by hand, use `psql -U postgres -h localhost
-p 5432 -d jayraldines_catering -f <file>.sql` (or `-d postgres` for the
main schema file, since it creates the database itself).

---

## Running the App

| Platform | Command |
|---|---|
| Windows (after setup) | Double-click `run.bat` |
| Windows (manual) | `venv\Scripts\activate` then `python main.py` |
| Linux (after setup) | `./run.sh` |
| Linux (manual) | `source venv/bin/activate` then `python main.py` (if using a venv) |

---

## Troubleshooting

**Database connection failed on startup**
- Confirm PostgreSQL is running:
  - Windows: check the `postgresql-x64-*` service in `services.msc`.
  - Linux: `pg_ctl status -D ~/.local/pgsql_data` (or check if a system
    Postgres is running with `pg_isready`).
- Confirm the password in the launcher matches the actual PostgreSQL
  password.
- The app runs in **offline mode** if the DB is unreachable at startup (see
  `main.py`) — you'll be able to open the window but data won't load/save.

**"Already Running" dialog on Windows**
- The app uses a single-instance mutex on Windows. Check your taskbar for an
  existing window, or check Task Manager for a stray `main.py`/`python.exe`
  process and end it.

**PySide6 / Qt platform plugin errors on Linux**
- The generated `run.sh` sets `QT_QPA_PLATFORM=xcb` and the necessary
  `LD_LIBRARY_PATH`/`QT_PLUGIN_PATH` for the bundled PySide6 Qt libraries.
  If running `python main.py` directly (bypassing `run.sh`), you'll need to
  set these yourself — easiest is to just always launch via `run.sh`.

**Re-running setup after it partially failed**
- Both scripts are safe to re-run from scratch. They re-detect existing
  Python/PostgreSQL installs and won't reinstall them.

**Starting over with a clean database**
- Re-run the setup script and answer `y` when asked to drop and recreate
  the database, or manually:
  ```
  psql -U postgres -h localhost -p 5432 -d postgres -c "DROP DATABASE jayraldines_catering;"
  ```
  then re-run the setup script (or `psql -f jayraldines_catering_clean.sql`)
  to rebuild it.

---

## Packaging a Standalone .exe

If you need to distribute the app as a single Windows executable (no Python
required on the target machine), see
[`PACKAGING_GUIDE.md`](./PACKAGING_GUIDE.md), which covers building with
PyInstaller. That's a separate concern from this setup guide, which is
about running the app from source with Python installed.
