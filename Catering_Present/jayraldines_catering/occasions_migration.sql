-- =============================================================================
-- Migration: Add occasions table
-- Run once on existing installations:
--   psql -U <user> -d jayraldines_catering -f occasions_migration.sql
-- =============================================================================

\connect jayraldines_catering

CREATE TABLE IF NOT EXISTS occasions (
    occ_id          SERIAL          PRIMARY KEY,
    occ_name        VARCHAR(120)    NOT NULL UNIQUE,
    occ_created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

INSERT INTO occasions (occ_name) VALUES
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
ON CONFLICT (occ_name) DO NOTHING;
