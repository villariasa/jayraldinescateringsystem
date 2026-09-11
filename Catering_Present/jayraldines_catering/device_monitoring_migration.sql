-- =============================================================================
-- Migration: Device & Terminal Session Monitoring
-- Tracks client devices, IP addresses, OS environments, active users,
-- and live connection heartbeats connecting to the PostgreSQL / SQLite database.
-- =============================================================================

CREATE TABLE IF NOT EXISTS device_sessions (
    device_id VARCHAR(64) PRIMARY KEY,
    hostname VARCHAR(128) NOT NULL,
    ip_address VARCHAR(45),
    os_info VARCHAR(128),
    app_version VARCHAR(32),
    username VARCHAR(64),
    user_role VARCHAR(32),
    active_module VARCHAR(64) DEFAULT 'Dashboard',
    status VARCHAR(20) DEFAULT 'online',
    first_connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_heartbeat TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_sessions_status ON device_sessions(status);
CREATE INDEX IF NOT EXISTS idx_device_sessions_heartbeat ON device_sessions(last_heartbeat);
