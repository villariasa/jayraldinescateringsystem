-- cebu_address_migration.sql
-- Address lookup tables with prefixed column names + FK on customers

CREATE TABLE IF NOT EXISTS address_regions (
    ar_id   SERIAL       PRIMARY KEY,
    ar_name VARCHAR(100) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_address_regions_name ON address_regions (ar_name);


CREATE TABLE IF NOT EXISTS address_provinces (
    ap_id        SERIAL       PRIMARY KEY,
    ap_region_id INT          NOT NULL REFERENCES address_regions(ar_id) ON DELETE CASCADE,
    ap_name      VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_address_provinces_region ON address_provinces (ap_region_id);
CREATE INDEX IF NOT EXISTS idx_address_provinces_name   ON address_provinces (ap_name);


CREATE TABLE IF NOT EXISTS address_cities (
    ac_id          SERIAL       PRIMARY KEY,
    ac_province_id INT          NOT NULL REFERENCES address_provinces(ap_id) ON DELETE CASCADE,
    ac_name        VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_address_cities_province ON address_cities (ac_province_id);
CREATE INDEX IF NOT EXISTS idx_address_cities_name     ON address_cities (ac_name);


CREATE TABLE IF NOT EXISTS address_barangays (
    ab_id      SERIAL       PRIMARY KEY,
    ab_city_id INT          NOT NULL REFERENCES address_cities(ac_id) ON DELETE CASCADE,
    ab_name    VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_address_barangays_city ON address_barangays (ab_city_id);
CREATE INDEX IF NOT EXISTS idx_address_barangays_name ON address_barangays (ab_name);


CREATE TABLE IF NOT EXISTS addresses (
    addr_id          SERIAL       PRIMARY KEY,
    addr_region_id   INT          DEFAULT NULL REFERENCES address_regions(ar_id)   ON DELETE SET NULL,
    addr_province_id INT          DEFAULT NULL REFERENCES address_provinces(ap_id) ON DELETE SET NULL,
    addr_city_id     INT          DEFAULT NULL REFERENCES address_cities(ac_id)    ON DELETE SET NULL,
    addr_barangay_id INT          DEFAULT NULL REFERENCES address_barangays(ab_id) ON DELETE SET NULL,
    addr_street      TEXT         NOT NULL DEFAULT '',
    addr_created_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_addresses_region   ON addresses (addr_region_id);
CREATE INDEX IF NOT EXISTS idx_addresses_province ON addresses (addr_province_id);
CREATE INDEX IF NOT EXISTS idx_addresses_city     ON addresses (addr_city_id);
CREATE INDEX IF NOT EXISTS idx_addresses_barangay ON addresses (addr_barangay_id);


ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS cus_address_id INT DEFAULT NULL REFERENCES addresses(addr_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_customers_address_id ON customers (cus_address_id);
