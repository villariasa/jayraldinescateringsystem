# Dynamic Theme Accent Color Runtime Engine

## 1. Implementation
`utils/accent.py` broadcasts `accent_changed` signals across all instantiated PySide6 widgets.
Stylesheets dynamically recompile using template string replacement, instantly updating highlights without restarting the app.
