# Performance Benchmarks & High-Concurrency Latency Targets

## 1. Target Service Level Objectives (SLOs)
- **Menu Query Response**: < 50ms at 95th percentile.
- **Order Placement Throughput**: > 200 orders per minute without table locking.
- **Sync Batch Ingestion**: < 500ms for batches of 50 mutations.
- **Client Startup Time**: < 2.5 seconds on quad-core Intel i5 workstation.

## 2. Test Scenarios
Benchmarked against concurrent workloads simulating 10 active tablet stations and 2 main cashier terminals.
