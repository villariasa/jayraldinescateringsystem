> **Note:** Reviewed & updated 2026-09-29 — Jayraldine's Catering System.

# Dynamic Theme Accent Color Runtime Engine

## 1. Implementation
`utils/accent.py` broadcasts `accent_changed` signals across all instantiated PySide6 widgets.
Stylesheets dynamically recompile using template string replacement, instantly updating highlights without restarting the app.
