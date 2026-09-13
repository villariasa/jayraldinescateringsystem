# Background DB Server Service Guide

## 1. Architectural Role
The `db_server_service.py` module manages the lifecycle of the local PostgreSQL server process, ensuring high availability for multi-terminal catering operations.

## 2. Service Responsibilities
- **Service Probing**: Checks if the PostgreSQL Windows Service (e.g., `postgresql-x64-18`) is registered and running via Windows SC / PowerShell APIs.
- **Automated Service Initialization**: Attempts graceful startup of the database engine if stopped upon application launch.
- **Health Polling**: Executes periodic `SELECT 1` queries every 60 seconds to detect engine freeze or connection drops.
- **Graceful Shutdown**: Intercepts application exit events to flush pending write buffers and close active client connections cleanly.
