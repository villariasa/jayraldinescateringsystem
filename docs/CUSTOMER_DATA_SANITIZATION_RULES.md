# Customer Data Sanitization & Input Normalization

## 1. Input Validation Rules
- **Name Normalization**: Strips excessive whitespace, capitalizes proper names, removes control characters.
- **Phone Formatting**: Standardizes prefixes (`+63`, `09`, `63`) into uniform `09XXXXXXXXX` format.
- **HTML/SQL Escape**: Escapes special characters (`&`, `<`, `>`, `"`, `'`) across all client-rendered HTML strings.
