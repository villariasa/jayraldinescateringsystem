# Database Connection Dialog Specification

## 1. Overview
The `DBConnectionDialog` component provides an interactive user interface allowing administrators and station operators to configure, test, and persist PostgreSQL connection parameters without manually altering configuration files.

## 2. Key Capabilities
- **Host & Port Configuration**: Dynamic input for database hostname (localhost, IP address, or domain) and port (default 5432).
- **Credentials Management**: Secure entry of database username, database name, and password with masked text entry.
- **Connection Handshake Test**: Built-in async test button verifying socket reachability, authentication success, and schema presence before saving.
- **Fallback Recovery**: Automatic fallback to SQLite offline mode if PostgreSQL server is unreachable.
- **State Persistence**: Encrypted local caching of verified database credentials in `db_config.json`.
