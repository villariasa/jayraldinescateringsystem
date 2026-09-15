# Structured JSON Logging & Daily File Rotation

## 1. Logging Standards
- **Format**: Structured JSON entries containing timestamp, log level, module origin, active user, and transaction context.
- **Rotation Schedule**: Daily log file rotation (`app_YYYY-MM-DD.log`) with automated 30-day cleanup.
- **Crash Trace Capture**: Native C-level segfault stack trace capture via Python `faulthandler`.
