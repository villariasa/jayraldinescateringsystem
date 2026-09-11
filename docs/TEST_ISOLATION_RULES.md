# Test Isolation & Teardown Rules

## Rules
1. Test records MUST use distinct identifiers (e.g., `[QA-TEST]`, `09990000000`).
2. All created test entities MUST be removed during Phase 14 teardown.
3. Tests MUST NOT modify or delete live production records.
