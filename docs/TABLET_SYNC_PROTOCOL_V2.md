# Tablet PWA Bidirectional Sync Protocol v2

## 1. Overview
Protocol v2 delivers resilient synchronization between handheld tablet terminals and the central catering database over local Wi-Fi networks with intermittent connectivity.

## 2. Core Enhancements
- **Optimistic UI Updates**: Orders and customer records are created instantly in local storage, providing zero-latency operator feedback.
- **Vector Clock Versioning**: Records maintain sequential revision identifiers (`version_id`) to identify conflict states.
- **Batch Mutation Transmission**: Queued mutations are compressed and dispatched in JSON batches to `/api/sync/batch`.
- **Atomic Server Ingestion**: Central server processes batch items within database transactions, returning status arrays with generated IDs.
