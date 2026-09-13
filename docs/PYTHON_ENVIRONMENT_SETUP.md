# Python 3.11 Virtual Environment & Dependency Setup Guide

## 1. Environment Bootstrap
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Pinned Core Dependencies
- `PySide6==6.7.2`
- `psycopg2-binary==2.9.9`
- `reportlab==4.2.2`
- `openpyxl==3.1.5`
- `bcrypt==4.2.0`
