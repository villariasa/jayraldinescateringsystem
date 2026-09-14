# In-Browser SQLite WASM & IndexedDB Binary Persistence

## 1. Storage Architecture
The tablet client executes an embedded SQLite WASM binary engine (`sql.js`) inside the browser JavaScript runtime:

- **Database Storage**: Entire `.db` binary byte arrays are serialized and stored inside IndexedDB (`jc_kiosk_sqlite` object store).
- **Schema Parity**: The client schema exactly replicates the desktop SQLite schema, enabling seamless database file exports.
- **Scheduled Debouncing**: Writes to IndexedDB are debounced ($300\text{ms}$) to minimize I/O overhead during rapid order item customization.
