"""
Creates a fresh, schema-only catering.db at the repo root for the installer
build (package_installer.py bundles it as the template DB new installs start
from). Not needed for normal app usage - utils/db.py creates its own DB in
the user's app-data folder on first run.

Usage:
  python seed_catering_db.py
"""
from pathlib import Path

from utils import db

ROOT = Path(__file__).resolve().parent


def main():
    db_path = ROOT / "catering.db"
    if db_path.exists():
        db_path.unlink()
    db.set_sqlite_db_path(db_path)
    db.connect_sqlite()
    db.close()
    print(f"[seed_catering_db] Created {db_path} ({db_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
