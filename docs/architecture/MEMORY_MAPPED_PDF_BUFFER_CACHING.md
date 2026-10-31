# Memory-Mapped PDF Buffer Caching for Thermal Printing

## 1. Caching Mechanism
Generated invoice PDFs are staged in memory-mapped temp files (`mmap`) to avoid disk write latency and reduce SSD wear on POS register terminals.
