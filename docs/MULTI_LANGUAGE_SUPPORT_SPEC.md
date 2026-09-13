# Internationalization (i18n) Resource Dictionary Specification

## 1. Architecture
UI text strings are decoupled into JSON translation resource dictionaries:
- `en_US.json`: Standard English terminology.
- `fil_PH.json`: Filipino / Tagalog colloquial and formal catering terminology.

## 2. Dynamic Switching
Switching languages updates all active labels, table headers, and error dialog messages instantly without requiring an application restart.
