# Automated Test Suite Runbook

## 1. Test Execution Commands
```powershell
# Run all unit tests
venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"

# Run extended QA audit suite
venv\Scripts\python.exe scratch/extended_qa_audit_suite.py
```
