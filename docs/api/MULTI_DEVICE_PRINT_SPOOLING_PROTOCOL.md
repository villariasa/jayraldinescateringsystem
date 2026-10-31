# Multi-Device Invoice Print Spooling Queue Protocol

## Architecture
When multiple tablet kiosks trigger receipts simultaneously, the desktop server queues print jobs in a thread-safe FIFO spooler, preventing interleaved thermal output.
