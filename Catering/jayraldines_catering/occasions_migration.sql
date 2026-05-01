-- =============================================================================
-- Migration: Add occasions table
-- Run once on existing installations:
--   psql -U <user> -d jayraldines_catering -f occasions_migration.sql
-- =============================================================================

\connect jayraldines_catering

CREATE TABLE IF NOT EXISTS occasions (
    id          SERIAL          PRIMARY KEY,
    name        VARCHAR(120)    NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

INSERT INTO occasions (name) VALUES
    ('Wedding'),
    ('Birthday'),
    ('Anniversary'),
    ('Debut'),
    ('Graduation'),
    ('Christening / Baptism'),
    ('Corporate Event'),
    ('Family Reunion'),
    ('Holiday Party'),
    ('Other')
ON CONFLICT (name) DO NOTHING;
