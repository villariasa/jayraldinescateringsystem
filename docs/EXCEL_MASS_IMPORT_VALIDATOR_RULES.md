# Excel Mass Import Schema Validation & Duplicate Prevention

## 1. Validation Rules
- **Header Conformance**: Validates column naming across all standardized workbook templates.
- **Data Coercion**: Robust type coercion for currency strings, phone number prefixes, and ISO date formats.
- **Deduplication**: Checks database for pre-existing records matching name and phone number before executing batch inserts.
