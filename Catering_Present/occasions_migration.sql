-- occasions_migration.sql
-- Adds the occasions table with prefixed column names

CREATE TABLE IF NOT EXISTS occasions (
    occ_id         SERIAL PRIMARY KEY,
    occ_name       VARCHAR(100) NOT NULL UNIQUE,
    occ_created_at TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_occasions_name ON occasions (occ_name);

INSERT INTO occasions (occ_name) VALUES
    ('Birthday'),
    ('Wedding'),
    ('Debut'),
    ('Anniversary'),
    ('Baptism'),
    ('Graduation'),
    ('Corporate Event'),
    ('Christmas Party'),
    ('New Year Celebration'),
    ('Reunion'),
    ('Seminar / Conference'),
    ('Other')
ON CONFLICT (occ_name) DO NOTHING;
