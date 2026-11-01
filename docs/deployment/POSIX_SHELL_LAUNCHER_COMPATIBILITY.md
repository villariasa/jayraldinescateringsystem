# POSIX Shell Launcher Compatibility & Linux Workstation Setup

## 1. Overview
The `run.sh` launcher ensures seamless execution across modern Linux distributions (Ubuntu, Fedora, Arch) for catering back-office terminals.
- Auto-detects local `venv/bin/python` prior to falling back to global pyenv or miniconda runtimes.
- Configures `QT_QPA_PLATFORM=xcb` alongside bundled cursor dynamic libraries (`xcbcursor`).
- Establishes fallback logic for SQLite and optional central PostgreSQL connectivity.
