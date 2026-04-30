-- =============================================================================
-- Cebu Address System Migration
-- Run this against the jayraldines_catering database AFTER the main schema.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. LOOKUP TABLES
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS address_regions (
    id   SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_provinces (
    id        SERIAL PRIMARY KEY,
    region_id INT NOT NULL REFERENCES address_regions(id) ON DELETE CASCADE,
    name      VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_cities (
    id          SERIAL PRIMARY KEY,
    province_id INT NOT NULL REFERENCES address_provinces(id) ON DELETE CASCADE,
    name        VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS address_barangays (
    id      SERIAL PRIMARY KEY,
    city_id INT NOT NULL REFERENCES address_cities(id) ON DELETE CASCADE,
    name    VARCHAR(120) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_address_barangays_name ON address_barangays (LOWER(name));
CREATE INDEX IF NOT EXISTS idx_address_cities_name    ON address_cities    (LOWER(name));

-- ---------------------------------------------------------------------------
-- 2. STRUCTURED ADDRESSES TABLE
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS addresses (
    id          SERIAL PRIMARY KEY,
    street      VARCHAR(255)    NOT NULL,
    barangay_id INT REFERENCES address_barangays(id),
    city_id     INT REFERENCES address_cities(id),
    province_id INT REFERENCES address_provinces(id),
    zip_code    VARCHAR(10),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Link customers to structured addresses (optional, additive)
ALTER TABLE customers
    ADD COLUMN IF NOT EXISTS address_id INT REFERENCES addresses(id);

-- ---------------------------------------------------------------------------
-- 3. SEED: Region VII (Central Visayas) + Cebu Province
-- ---------------------------------------------------------------------------

INSERT INTO address_regions (name) VALUES ('Region VII - Central Visayas')
    ON CONFLICT DO NOTHING;

INSERT INTO address_provinces (region_id, name)
SELECT r.id, 'Cebu'
FROM address_regions r WHERE r.name = 'Region VII - Central Visayas'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4. SEED: Cities / Municipalities of Cebu
-- ---------------------------------------------------------------------------

DO $$
DECLARE v_prov_id INT;
BEGIN
    SELECT id INTO v_prov_id FROM address_provinces WHERE name = 'Cebu' LIMIT 1;

    INSERT INTO address_cities (province_id, name) VALUES
        (v_prov_id, 'Cebu City'),
        (v_prov_id, 'Lapu-Lapu City'),
        (v_prov_id, 'Mandaue City'),
        (v_prov_id, 'Carcar City'),
        (v_prov_id, 'Danao City'),
        (v_prov_id, 'Naga City'),
        (v_prov_id, 'Talisay City'),
        (v_prov_id, 'Toledo City'),
        (v_prov_id, 'Alcantara'),
        (v_prov_id, 'Alcoy'),
        (v_prov_id, 'Alegria'),
        (v_prov_id, 'Aloguinsan'),
        (v_prov_id, 'Argao'),
        (v_prov_id, 'Asturias'),
        (v_prov_id, 'Badian'),
        (v_prov_id, 'Balamban'),
        (v_prov_id, 'Bantayan'),
        (v_prov_id, 'Barili'),
        (v_prov_id, 'Bogo City'),
        (v_prov_id, 'Boljoon'),
        (v_prov_id, 'Borbon'),
        (v_prov_id, 'Carmen'),
        (v_prov_id, 'Catmon'),
        (v_prov_id, 'Compostela'),
        (v_prov_id, 'Consolacion'),
        (v_prov_id, 'Cordova'),
        (v_prov_id, 'Daanbantayan'),
        (v_prov_id, 'Dalaguete'),
        (v_prov_id, 'Dumanjug'),
        (v_prov_id, 'Ginatilan'),
        (v_prov_id, 'Liloan'),
        (v_prov_id, 'Madridejos'),
        (v_prov_id, 'Malabuyoc'),
        (v_prov_id, 'Medellin'),
        (v_prov_id, 'Minglanilla'),
        (v_prov_id, 'Moalboal'),
        (v_prov_id, 'Oslob'),
        (v_prov_id, 'Pilar'),
        (v_prov_id, 'Pinamungajan'),
        (v_prov_id, 'Poro'),
        (v_prov_id, 'Ronda'),
        (v_prov_id, 'Samboan'),
        (v_prov_id, 'San Fernando'),
        (v_prov_id, 'San Francisco'),
        (v_prov_id, 'San Remigio'),
        (v_prov_id, 'Santa Fe'),
        (v_prov_id, 'Santander'),
        (v_prov_id, 'Sibonga'),
        (v_prov_id, 'Sogod'),
        (v_prov_id, 'Tabogon'),
        (v_prov_id, 'Tabuelan'),
        (v_prov_id, 'Tuburan'),
        (v_prov_id, 'Tudela')
    ON CONFLICT DO NOTHING;
END$$;

-- ---------------------------------------------------------------------------
-- 5. SEED: Barangays
-- ---------------------------------------------------------------------------

DO $$
DECLARE v_city_id INT;
BEGIN

-- ============================================================
-- CEBU CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Cebu City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Adlaon'),(v_city_id,'Agsungot'),(v_city_id,'Apas'),
(v_city_id,'Bacayan'),(v_city_id,'Banilad'),(v_city_id,'Basak Pardo'),
(v_city_id,'Basak San Nicolas'),(v_city_id,'Binaliw'),(v_city_id,'Bonbon'),
(v_city_id,'Budla-an'),(v_city_id,'Buhisan'),(v_city_id,'Bulacao'),
(v_city_id,'Buot-Taup Pardo'),(v_city_id,'Busay'),(v_city_id,'Calamba'),
(v_city_id,'Cambinocot'),(v_city_id,'Capitol Site'),(v_city_id,'Carreta'),
(v_city_id,'Central'),(v_city_id,'Cogon Pardo'),(v_city_id,'Cogon Ramos'),
(v_city_id,'Day-as'),(v_city_id,'Duljo-Fatima'),(v_city_id,'Ermita'),
(v_city_id,'Forecast'),(v_city_id,'Guadalupe'),(v_city_id,'Guba'),
(v_city_id,'Hippodromo'),(v_city_id,'Inayawan'),(v_city_id,'Kalubihan'),
(v_city_id,'Kalunasan'),(v_city_id,'Kamagayan'),(v_city_id,'Kasambagan'),
(v_city_id,'Kinasang-an Pardo'),(v_city_id,'Labangon'),(v_city_id,'Lahug'),
(v_city_id,'Lorega San Miguel'),(v_city_id,'Lusaran'),(v_city_id,'Luz'),
(v_city_id,'Mabini'),(v_city_id,'Mabolo'),(v_city_id,'Malubog'),
(v_city_id,'Mambaling'),(v_city_id,'Pahina Central'),(v_city_id,'Pahina San Nicolas'),
(v_city_id,'Pamutan'),(v_city_id,'Pardo'),(v_city_id,'Pari-an'),
(v_city_id,'Paril'),(v_city_id,'Pasil'),(v_city_id,'Pit-os'),
(v_city_id,'Poblacion Pardo'),(v_city_id,'Pulangbato'),(v_city_id,'Pung-ol-Sibugay'),
(v_city_id,'Punta Princesa'),(v_city_id,'Quiot Pardo'),(v_city_id,'Sambag I'),
(v_city_id,'Sambag II'),(v_city_id,'San Antonio'),(v_city_id,'San Jose'),
(v_city_id,'San Nicolas Central'),(v_city_id,'San Nicolas Proper'),
(v_city_id,'San Roque'),(v_city_id,'Santa Cruz'),(v_city_id,'Santo Nino'),
(v_city_id,'Sapangdaku'),(v_city_id,'Sawang Calero'),(v_city_id,'Sinsin'),
(v_city_id,'Sirao'),(v_city_id,'Suba-basbas'),(v_city_id,'Sudlon I'),
(v_city_id,'Sudlon II'),(v_city_id,'T. Padilla'),(v_city_id,'Tabunan'),
(v_city_id,'Tagbao'),(v_city_id,'Talamban'),(v_city_id,'Taptap'),
(v_city_id,'Tejero'),(v_city_id,'Tinago'),(v_city_id,'Tisa'),
(v_city_id,'To-og'),(v_city_id,'Toong'),(v_city_id,'Tugbongan'),
(v_city_id,'Umapad'),(v_city_id,'Zapatera')
ON CONFLICT DO NOTHING;

-- ============================================================
-- LAPU-LAPU CITY (Opon)
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Lapu-Lapu City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Agus'),(v_city_id,'Babag'),(v_city_id,'Bankal'),
(v_city_id,'Baring'),(v_city_id,'Basak'),(v_city_id,'Buaya'),
(v_city_id,'Calawisan'),(v_city_id,'Canjulao'),(v_city_id,'Caubian'),
(v_city_id,'Caw-oy'),(v_city_id,'Cawhagan'),(v_city_id,'Gun-ob'),
(v_city_id,'Ibo'),(v_city_id,'Looc'),(v_city_id,'Mactan'),
(v_city_id,'Maribago'),(v_city_id,'Marigondon'),(v_city_id,'Pajac'),
(v_city_id,'Pajo'),(v_city_id,'Pangan-an'),(v_city_id,'Poblacion'),
(v_city_id,'Portcat'),(v_city_id,'Punta Engano'),(v_city_id,'Pusok'),
(v_city_id,'Sabang'),(v_city_id,'Santa Rosa'),(v_city_id,'Subabasbas'),
(v_city_id,'Talima'),(v_city_id,'Tingo'),(v_city_id,'Tungasan')
ON CONFLICT DO NOTHING;

-- ============================================================
-- MANDAUE CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Mandaue City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Alang-alang'),(v_city_id,'Bakilid'),(v_city_id,'Banilad'),
(v_city_id,'Basak'),(v_city_id,'Cambaro'),(v_city_id,'Canduman'),
(v_city_id,'Casili'),(v_city_id,'Casuntingan'),(v_city_id,'Centro'),
(v_city_id,'Cubacub'),(v_city_id,'Guizo'),(v_city_id,'Ibabao-Estancia'),
(v_city_id,'Jagobiao'),(v_city_id,'Labogon'),(v_city_id,'Looc'),
(v_city_id,'Maguikay'),(v_city_id,'Mantuyong'),(v_city_id,'Novaliches'),
(v_city_id,'Opao'),(v_city_id,'Pagsabungan'),(v_city_id,'Pakna-an'),
(v_city_id,'Putlod'),(v_city_id,'Subangdaku'),(v_city_id,'Tabok'),
(v_city_id,'Tawason'),(v_city_id,'Tingub'),(v_city_id,'Tipolo'),
(v_city_id,'Umapad')
ON CONFLICT DO NOTHING;

-- ============================================================
-- TALISAY CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Talisay City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Biasong'),(v_city_id,'Bulacao'),(v_city_id,'Cansojong'),
(v_city_id,'Dumlog'),(v_city_id,'Jaclupan'),(v_city_id,'Lagtang'),
(v_city_id,'Lawaan I'),(v_city_id,'Lawaan II'),(v_city_id,'Lawaan III'),
(v_city_id,'Linao'),(v_city_id,'Maghaway'),(v_city_id,'Manipis'),
(v_city_id,'Mohon'),(v_city_id,'Pooc'),(v_city_id,'Poblacion'),
(v_city_id,'San Isidro'),(v_city_id,'San Roque'),(v_city_id,'Tabunok'),
(v_city_id,'Tangke'),(v_city_id,'Tapul')
ON CONFLICT DO NOTHING;

-- ============================================================
-- DANAO CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Danao City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Baliang'),(v_city_id,'Binaliw'),(v_city_id,'Cabungahan'),
(v_city_id,'Cahumayan'),(v_city_id,'Cambanay'),(v_city_id,'Cambubho'),
(v_city_id,'Cogon'),(v_city_id,'Danasan'),(v_city_id,'Dunggoan'),
(v_city_id,'Guinacot'),(v_city_id,'Guinsay'),(v_city_id,'Langosig'),
(v_city_id,'Lawaan'),(v_city_id,'Licos'),(v_city_id,'Looc'),
(v_city_id,'Lugo'),(v_city_id,'Magtagobtob'),(v_city_id,'Malapoc'),
(v_city_id,'Manlayag'),(v_city_id,'Mantija'),(v_city_id,'Masaba'),
(v_city_id,'Maslog'),(v_city_id,'Nangka'),(v_city_id,'Oguis'),
(v_city_id,'Pili'),(v_city_id,'Poblacion'),(v_city_id,'Pondol'),
(v_city_id,'Remedios'),(v_city_id,'Sabang'),(v_city_id,'Suba'),
(v_city_id,'Taboc'),(v_city_id,'Taytay'),(v_city_id,'Togonon'),
(v_city_id,'Tuburan Sur')
ON CONFLICT DO NOTHING;

-- ============================================================
-- CARCAR CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Carcar City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bolinawan'),(v_city_id,'Bolo'),(v_city_id,'Bontod'),
(v_city_id,'Calidngan'),(v_city_id,'Can-asujan'),(v_city_id,'Guadalupe'),
(v_city_id,'Liburon'),(v_city_id,'Napo'),(v_city_id,'Ocana'),
(v_city_id,'Perrelos'),(v_city_id,'Poblacion I'),(v_city_id,'Poblacion II'),
(v_city_id,'Poblacion III'),(v_city_id,'Tuyom'),(v_city_id,'Valencia'),
(v_city_id,'Valladolid')
ON CONFLICT DO NOTHING;

-- ============================================================
-- NAGA CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Naga City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Alfaco'),(v_city_id,'Bairan'),(v_city_id,'Balirong'),
(v_city_id,'Cabungahan'),(v_city_id,'Cantao-an'),(v_city_id,'Central Poblacion'),
(v_city_id,'Colon'),(v_city_id,'East Poblacion'),(v_city_id,'Inayagan'),
(v_city_id,'Inoburan'),(v_city_id,'Janao-an'),(v_city_id,'Lanas'),
(v_city_id,'Langtad'),(v_city_id,'Lutac'),(v_city_id,'Mainit'),
(v_city_id,'Mancap'),(v_city_id,'Naalad'),(v_city_id,'North Poblacion'),
(v_city_id,'Pangdan'),(v_city_id,'Patag'),(v_city_id,'South Poblacion'),
(v_city_id,'Tagjaguimit'),(v_city_id,'Tangke'),(v_city_id,'Tinaan'),
(v_city_id,'Tuyan'),(v_city_id,'Uling'),(v_city_id,'West Poblacion')
ON CONFLICT DO NOTHING;

-- ============================================================
-- TOLEDO CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Toledo City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Awihao'),(v_city_id,'Bagakay'),(v_city_id,'Balangkas'),
(v_city_id,'Bato'),(v_city_id,'Biga'),(v_city_id,'Bulongan'),
(v_city_id,'Cabitoonan'),(v_city_id,'Calongcalong'),(v_city_id,'Cambang-ug'),
(v_city_id,'Camp 8'),(v_city_id,'Canlumampao'),(v_city_id,'Cantabaco'),
(v_city_id,'Capitan Lorenzo'),(v_city_id,'Caraville'),(v_city_id,'Casoy'),
(v_city_id,'Cavite'),(v_city_id,'Daanlungsod'),(v_city_id,'Don Andres Soriano'),
(v_city_id,'Dumlog'),(v_city_id,'Gen. Climaco'),(v_city_id,'Ilihan'),
(v_city_id,'Ibo'),(v_city_id,'Ilihan Norte'),(v_city_id,'Kalubihan'),
(v_city_id,'Loay'),(v_city_id,'Luray I'),(v_city_id,'Luray II'),
(v_city_id,'Matab-ang'),(v_city_id,'Media Once'),(v_city_id,'Pangamihan'),
(v_city_id,'Poblacion'),(v_city_id,'Poog'),(v_city_id,'Putingbato'),
(v_city_id,'Sam-ang'),(v_city_id,'Sangi'),(v_city_id,'Santo Nino'),
(v_city_id,'Subasbas'),(v_city_id,'Talavera'),(v_city_id,'Tilhaong'),
(v_city_id,'Tolosa'),(v_city_id,'Tubod')
ON CONFLICT DO NOTHING;

-- ============================================================
-- BOGO CITY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Bogo City' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Anonang Norte'),(v_city_id,'Anonang Sur'),(v_city_id,'Banban'),
(v_city_id,'Binabag'),(v_city_id,'Bungtod'),(v_city_id,'Carbon'),
(v_city_id,'Cayang'),(v_city_id,'Cogon'),(v_city_id,'Dakit'),
(v_city_id,'Don Pedro Rodriguez'),(v_city_id,'Gairan'),(v_city_id,'Guadalupe'),
(v_city_id,'La Paz'),(v_city_id,'La Purisima Concepcion'),(v_city_id,'Libertad'),
(v_city_id,'Lourdes'),(v_city_id,'Malingin'),(v_city_id,'Marangog'),
(v_city_id,'Nailon'),(v_city_id,'Odlot'),(v_city_id,'Pandan'),(v_city_id,'Polambato'),
(v_city_id,'Sambag'),(v_city_id,'San Vicente'),(v_city_id,'Santo Nino'),
(v_city_id,'Santo Rosario'),(v_city_id,'Siocon'),(v_city_id,'Somosa'),
(v_city_id,'Talbunan'),(v_city_id,'Tapilon'),(v_city_id,'Tigbawan'),
(v_city_id,'Tugas')
ON CONFLICT DO NOTHING;

-- ============================================================
-- CONSOLACION
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Consolacion' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bagacay'),(v_city_id,'Butong'),(v_city_id,'Cansaga'),
(v_city_id,'Casili'),(v_city_id,'Danglag'),(v_city_id,'Garing'),
(v_city_id,'Jugan'),(v_city_id,'Lamac'),(v_city_id,'Lanipga'),
(v_city_id,'Nangka'),(v_city_id,'Panas'),(v_city_id,'Panoypoy'),
(v_city_id,'Pitogo'),(v_city_id,'Poblacion Occidental'),(v_city_id,'Poblacion Oriental'),
(v_city_id,'Pulpog'),(v_city_id,'Sacsac'),(v_city_id,'Tayud'),
(v_city_id,'Tilhaong'),(v_city_id,'Tolotolo'),(v_city_id,'Tugbongan')
ON CONFLICT DO NOTHING;

-- ============================================================
-- LILOAN
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Liloan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Cabadiangan'),(v_city_id,'Calero'),(v_city_id,'Catarman'),
(v_city_id,'Cotcot'),(v_city_id,'Jubay'),(v_city_id,'Lataban'),
(v_city_id,'Mulao'),(v_city_id,'Poblacion'),(v_city_id,'San Roque'),
(v_city_id,'San Vicente'),(v_city_id,'Santa Cruz'),(v_city_id,'Santander'),
(v_city_id,'Science Park'),(v_city_id,'Tabla'),(v_city_id,'Tayud'),
(v_city_id,'Yati')
ON CONFLICT DO NOTHING;

-- ============================================================
-- MINGLANILLA
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Minglanilla' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Cadulawan'),(v_city_id,'Calajunan'),(v_city_id,'Canlaon'),
(v_city_id,'Cogon'),(v_city_id,'Cuanos'),(v_city_id,'Guindaruhan'),
(v_city_id,'Linao'),(v_city_id,'Manduang'),(v_city_id,'Pakigne'),
(v_city_id,'Poblacion Ward I'),(v_city_id,'Poblacion Ward II'),
(v_city_id,'Poblacion Ward III'),(v_city_id,'Poblacion Ward IV'),
(v_city_id,'Tubod'),(v_city_id,'Tulay'),(v_city_id,'Tunghaan'),
(v_city_id,'Tungkop'),(v_city_id,'Vito')
ON CONFLICT DO NOTHING;

-- ============================================================
-- CORDOVA
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Cordova' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Alegria'),(v_city_id,'Bangbang'),(v_city_id,'Buagsong'),
(v_city_id,'Catarman'),(v_city_id,'Cogon'),(v_city_id,'Dapitan'),
(v_city_id,'Day-as'),(v_city_id,'Gabi'),(v_city_id,'Gilutongan'),
(v_city_id,'Ibabao'),(v_city_id,'Pilipog'),(v_city_id,'Poblacion'),
(v_city_id,'San Miguel')
ON CONFLICT DO NOTHING;

-- ============================================================
-- COMPOSTELA
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Compostela' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bagalnga'),(v_city_id,'Basak'),(v_city_id,'Bulukon'),
(v_city_id,'Cabadiangan'),(v_city_id,'Cambayog'),(v_city_id,'Canamucan'),
(v_city_id,'Cogon'),(v_city_id,'Dapdap'),(v_city_id,'Estipona'),
(v_city_id,'Lupa'),(v_city_id,'Magay'),(v_city_id,'Mulao'),
(v_city_id,'Ngall'),(v_city_id,'Nug-as'),(v_city_id,'Oldlungsod'),
(v_city_id,'Poblacion'),(v_city_id,'Tamiao'),(v_city_id,'Tubigan')
ON CONFLICT DO NOTHING;

-- ============================================================
-- CARMEN
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Carmen' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Baring'),(v_city_id,'Cantipay'),(v_city_id,'Cantukong'),
(v_city_id,'Cantumog'),(v_city_id,'Caurasan'),(v_city_id,'Cogon East'),
(v_city_id,'Cogon West'),(v_city_id,'Corte'),(v_city_id,'Dawis Norte'),
(v_city_id,'Dawis Sur'),(v_city_id,'Hagnaya'),(v_city_id,'Ipil'),
(v_city_id,'Lanipga'),(v_city_id,'Liboron'),(v_city_id,'Lower Natimao-an'),
(v_city_id,'Luyang'),(v_city_id,'Manipis'),(v_city_id,'Natimao-an'),
(v_city_id,'Panalipan'),(v_city_id,'Poblacion'),(v_city_id,'San Pedro'),
(v_city_id,'Sandayong Norte'),(v_city_id,'Sandayong Sur'),
(v_city_id,'Santa Filomena'),(v_city_id,'Santander'),(v_city_id,'Simway'),
(v_city_id,'So-ong'),(v_city_id,'Tagaytay'),(v_city_id,'Upper Natimao-an')
ON CONFLICT DO NOTHING;

-- ============================================================
-- BANTAYAN
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Bantayan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Atop-atop'),(v_city_id,'Baigad'),(v_city_id,'Bantigue'),
(v_city_id,'Baod'),(v_city_id,'Binaobao'),(v_city_id,'Botigues'),
(v_city_id,'Doong'),(v_city_id,'Guiwanon'),(v_city_id,'Hilotongan'),
(v_city_id,'Kabac'),(v_city_id,'Kabangbang'),(v_city_id,'Kampingganon'),
(v_city_id,'Kangkaibe'),(v_city_id,'Lipayran'),(v_city_id,'Luyongbaybay'),
(v_city_id,'Mojon'),(v_city_id,'Obo'),(v_city_id,'Patao'),
(v_city_id,'Putian'),(v_city_id,'Sillon'),(v_city_id,'Sungko'),
(v_city_id,'Suba'),(v_city_id,'Sulangan'),(v_city_id,'Tamiao'),
(v_city_id,'Ticad')
ON CONFLICT DO NOTHING;

-- ============================================================
-- DAANBANTAYAN
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Daanbantayan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Aguho'),(v_city_id,'Bagay'),(v_city_id,'Bakhawan'),
(v_city_id,'Bateria'),(v_city_id,'Bitoon'),(v_city_id,'Calape'),
(v_city_id,'Carnaza'),(v_city_id,'Dalingding'),(v_city_id,'Lanao'),
(v_city_id,'Logon'),(v_city_id,'Malbago'),(v_city_id,'Malingin'),
(v_city_id,'Maya'),(v_city_id,'Pajo'),(v_city_id,'Paypay'),
(v_city_id,'Poblacion'),(v_city_id,'Talisay'),(v_city_id,'Tapilon'),
(v_city_id,'Tinubdan'),(v_city_id,'Tomongog')
ON CONFLICT DO NOTHING;

-- ============================================================
-- ARGAO
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Argao' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Alegria'),(v_city_id,'Baliangan'),(v_city_id,'Binlod'),
(v_city_id,'Bulasa'),(v_city_id,'Butong'),(v_city_id,'Calagasan'),
(v_city_id,'Canbantug'),(v_city_id,'Canbanua'),(v_city_id,'Cansuje'),
(v_city_id,'Capio-an'),(v_city_id,'Casay'),(v_city_id,'Catang'),
(v_city_id,'Colawin'),(v_city_id,'Conalum'),(v_city_id,'Guiwanon'),
(v_city_id,'Gutlang'),(v_city_id,'Jampang'),(v_city_id,'Juna'),
(v_city_id,'Lamacan'),(v_city_id,'Langtad'),(v_city_id,'Langub'),
(v_city_id,'Lum-an'),(v_city_id,'Mabasa'),(v_city_id,'Mandilikit'),
(v_city_id,'Mompeller'),(v_city_id,'Panadtaran'),(v_city_id,'Poblacion'),
(v_city_id,'Sua'),(v_city_id,'Sumaguan'),(v_city_id,'Tabayag'),
(v_city_id,'Talaga'),(v_city_id,'Talaytay'),(v_city_id,'Talo-ot'),
(v_city_id,'Tiguib'),(v_city_id,'Tulang'),(v_city_id,'Tulic'),
(v_city_id,'Ubaub'),(v_city_id,'Usmad')
ON CONFLICT DO NOTHING;

-- ============================================================
-- BARILI
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Barili' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Azucena'),(v_city_id,'Bagakay'),(v_city_id,'Balao'),
(v_city_id,'Bolocboloc'),(v_city_id,'Budbud'),(v_city_id,'Bugtong Kawayan'),
(v_city_id,'Cabcaban'),(v_city_id,'Cagay'),(v_city_id,'Campangga'),
(v_city_id,'Candugay'),(v_city_id,'Dakit'),(v_city_id,'Giloctog'),
(v_city_id,'Giwanon'),(v_city_id,'Guibuangan'),(v_city_id,'Gunting'),
(v_city_id,'Hilatongan'),(v_city_id,'Ilaya'),(v_city_id,'Jakop'),
(v_city_id,'Jobtong'),(v_city_id,'Labog'),(v_city_id,'Libo'),
(v_city_id,'Malolos'),(v_city_id,'Mantalongon'),(v_city_id,'Mantayupan'),
(v_city_id,'Mayana'),(v_city_id,'Miting'),(v_city_id,'Molobolo'),
(v_city_id,'Montealegre'),(v_city_id,'Naga'),(v_city_id,'Oas'),
(v_city_id,'Poblacion'),(v_city_id,'Salgued'),(v_city_id,'San Rafael'),
(v_city_id,'Santa Ana'),(v_city_id,'Sayaw'),(v_city_id,'Tal-ot'),
(v_city_id,'Tubod'),(v_city_id,'Vito')
ON CONFLICT DO NOTHING;

-- ============================================================
-- BALAMBAN
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Balamban' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Abucayan'),(v_city_id,'Aliwanay'),(v_city_id,'Arpili'),
(v_city_id,'Baliwagan'),(v_city_id,'Bayong'),(v_city_id,'Biasong'),
(v_city_id,'Buanoy'),(v_city_id,'Cabagdalan'),(v_city_id,'Cabasiangan'),
(v_city_id,'Cambuhawe'),(v_city_id,'Cansomoroy'),(v_city_id,'Cantibas'),
(v_city_id,'Cantuod'),(v_city_id,'Duangan'),(v_city_id,'Gaas'),
(v_city_id,'Ginatilan'),(v_city_id,'Hingatmonan'),(v_city_id,'Lamesa'),
(v_city_id,'Liki'),(v_city_id,'Luca'),(v_city_id,'Matun-og'),
(v_city_id,'Nangka'),(v_city_id,'Pondol'),(v_city_id,'Prensa'),
(v_city_id,'Poblacion'),(v_city_id,'San Isidro'),(v_city_id,'Singsing'),
(v_city_id,'Tabunan'),(v_city_id,'Tagbuanoy'),(v_city_id,'Tagba-o'),
(v_city_id,'Tuwi')
ON CONFLICT DO NOTHING;

-- ============================================================
-- BORBON
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Borbon' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Baganga'),(v_city_id,'Biasong'),(v_city_id,'Bingay'),
(v_city_id,'Cabungahan'),(v_city_id,'Cadaruhan'),(v_city_id,'Cajel'),
(v_city_id,'Calamias'),(v_city_id,'Codia'),(v_city_id,'Cogon'),
(v_city_id,'Dakit'),(v_city_id,'Kabak'),(v_city_id,'Laaw'),
(v_city_id,'Lugo'),(v_city_id,'Managase'),(v_city_id,'Panalipan'),
(v_city_id,'Poblacion'),(v_city_id,'San Jose'),(v_city_id,'Tabunan'),
(v_city_id,'Tagbuanoy'),(v_city_id,'Villahermosa')
ON CONFLICT DO NOTHING;

-- ============================================================
-- ALCOY
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Alcoy' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Atabay'),(v_city_id,'Daan-Lungsod'),(v_city_id,'Guiwanon'),
(v_city_id,'Kahupagan'),(v_city_id,'Kan-irag'),(v_city_id,'Lapyahan'),
(v_city_id,'Lombo'),(v_city_id,'Nug-as'),(v_city_id,'Oslob'),
(v_city_id,'Pasol'),(v_city_id,'Poblacion'),(v_city_id,'Pugalo'),
(v_city_id,'San Agustin')
ON CONFLICT DO NOTHING;

-- ============================================================
-- DALAGUETE
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Dalaguete' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Ablayan'),(v_city_id,'Babayongan'),(v_city_id,'Balud'),
(v_city_id,'Banhigan'),(v_city_id,'Bulak'),(v_city_id,'Caleriohan'),
(v_city_id,'Calogohan'),(v_city_id,'Can-ila'),(v_city_id,'Casay'),
(v_city_id,'Catmomog'),(v_city_id,'Colawin'),(v_city_id,'Culajao'),
(v_city_id,'Cumba'),(v_city_id,'Dakit'),(v_city_id,'Damolog'),
(v_city_id,'Gaan'),(v_city_id,'Gibitngil'),(v_city_id,'Guiwanon'),
(v_city_id,'Ilaya'),(v_city_id,'Lanao'),(v_city_id,'Langkas'),
(v_city_id,'Lumbog'),(v_city_id,'Malones'),(v_city_id,'Mantalongon'),
(v_city_id,'Nalhub'),(v_city_id,'Nug-as'),(v_city_id,'Obong'),
(v_city_id,'Poblacion'),(v_city_id,'Punta'),(v_city_id,'Tapon'),
(v_city_id,'Tawid'),(v_city_id,'Tuburan'),(v_city_id,'Tudela')
ON CONFLICT DO NOTHING;

-- ============================================================
-- SIBONGA
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Sibonga' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Abugon'),(v_city_id,'Bag-o'),(v_city_id,'Banica'),
(v_city_id,'Basak'),(v_city_id,'Binoon'),(v_city_id,'Buhingtubod'),
(v_city_id,'Bunga'),(v_city_id,'Calatagan'),(v_city_id,'Cambaol'),
(v_city_id,'Candaguit'),(v_city_id,'Cantolaroy'),(v_city_id,'Dugyan'),
(v_city_id,'Dumgas'),(v_city_id,'Guimbangco-an'),(v_city_id,'Lamacan'),
(v_city_id,'Langub'),(v_city_id,'Libo'),(v_city_id,'Lindogon'),
(v_city_id,'Magcagong'),(v_city_id,'Manatad'),(v_city_id,'Mangyan'),
(v_city_id,'Papan'),(v_city_id,'Poblacion'),(v_city_id,'Pucahan'),
(v_city_id,'Samboang'),(v_city_id,'San Jose'),(v_city_id,'San Juan'),
(v_city_id,'Simala'),(v_city_id,'Tubigagmanok')
ON CONFLICT DO NOTHING;

-- ============================================================
-- OSLOB
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Oslob' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Ale'),(v_city_id,'Bangcogon'),(v_city_id,'Bonbon'),
(v_city_id,'Caduawan'),(v_city_id,'Canangca-an'),(v_city_id,'Cañorong'),
(v_city_id,'Daanlungsod'),(v_city_id,'Don Virgilio Gonzales'),
(v_city_id,'Gawi'),(v_city_id,'Jabon'),(v_city_id,'Lagunde'),
(v_city_id,'Libo'),(v_city_id,'Luca'),(v_city_id,'Mainit'),
(v_city_id,'Manlayag'),(v_city_id,'Minolos'),(v_city_id,'Namamgo'),
(v_city_id,'Pisong'),(v_city_id,'Poblacion'),(v_city_id,'Punta'),
(v_city_id,'Pungtod'),(v_city_id,'Stan'),(v_city_id,'Sumilon'),
(v_city_id,'Tangbo')
ON CONFLICT DO NOTHING;

-- ============================================================
-- MOALBOAL
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Moalboal' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bala'),(v_city_id,'Balabagon'),(v_city_id,'Basdiot'),
(v_city_id,'Batadbatad'),(v_city_id,'Bugho'),(v_city_id,'Buguil'),
(v_city_id,'Busay'),(v_city_id,'Lanao'),(v_city_id,'Lip-tong'),
(v_city_id,'Litucan'),(v_city_id,'Mainit'),(v_city_id,'Manara'),
(v_city_id,'Owak'),(v_city_id,'Panagsama'),(v_city_id,'Poblacion East'),
(v_city_id,'Poblacion West'),(v_city_id,'Saavedra'),(v_city_id,'Tomonoy'),
(v_city_id,'Tuble'),(v_city_id,'Tunga')
ON CONFLICT DO NOTHING;

-- ============================================================
-- SAN FERNANDO
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'San Fernando' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Balud'),(v_city_id,'Bugho'),(v_city_id,'Buhisan'),
(v_city_id,'Cabatbatan'),(v_city_id,'Greenhills'),(v_city_id,'Ilaya'),
(v_city_id,'Lantawan'),(v_city_id,'Liburon'),(v_city_id,'Magsaysay'),
(v_city_id,'Mahayahay'),(v_city_id,'Malhiao'),(v_city_id,'Manduyong'),
(v_city_id,'Molina'),(v_city_id,'Montserrat'),(v_city_id,'Oslob'),
(v_city_id,'Palanas'),(v_city_id,'Poblacion'),(v_city_id,'Saging'),
(v_city_id,'Sambagon'),(v_city_id,'Sindlan'),(v_city_id,'Tabionan'),
(v_city_id,'Tagnote'),(v_city_id,'Talavera'),(v_city_id,'Tangke'),
(v_city_id,'Tindog')
ON CONFLICT DO NOTHING;

-- ============================================================
-- PINAMUNGAJAN
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Pinamungajan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Aloguinsan'),(v_city_id,'Anopog'),(v_city_id,'Binabag'),
(v_city_id,'Buhingtubod'),(v_city_id,'Daanlungsod'),(v_city_id,'Estaca'),
(v_city_id,'Guimbawian'),(v_city_id,'Lamac'),(v_city_id,'Lut-od'),
(v_city_id,'Manduyong'),(v_city_id,'Mangotocon'),(v_city_id,'Matun-og'),
(v_city_id,'Poblacion'),(v_city_id,'San Vicente'),(v_city_id,'Sinsin'),
(v_city_id,'Talavera'),(v_city_id,'Tungkay')
ON CONFLICT DO NOTHING;

-- ============================================================
-- SAN REMIGIO
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'San Remigio' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Anapog'),(v_city_id,'Argawanon'),(v_city_id,'Bagtic'),
(v_city_id,'Bancasan'),(v_city_id,'Batad'),(v_city_id,'Busogon'),
(v_city_id,'Calambua'),(v_city_id,'Canagahan'),(v_city_id,'Casambalangan'),
(v_city_id,'Kawit'),(v_city_id,'Lungon'),(v_city_id,'Matab-ang'),
(v_city_id,'Pago'),(v_city_id,'Poblacion'),(v_city_id,'Punta'),
(v_city_id,'Saksak'),(v_city_id,'Tampa'),(v_city_id,'Tigbawan'),
(v_city_id,'Tominjao')
ON CONFLICT DO NOTHING;

-- ============================================================
-- TUBURAN
-- ============================================================
SELECT id INTO v_city_id FROM address_cities WHERE name = 'Tuburan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Alegria'),(v_city_id,'Amatugan'),(v_city_id,'Antipolo'),
(v_city_id,'Apalan'),(v_city_id,'Bagasawe'),(v_city_id,'Bakyawan'),
(v_city_id,'Bongdo'),(v_city_id,'Bongdo Gua'),(v_city_id,'Bontod'),
(v_city_id,'Cabadiangan'),(v_city_id,'Cambuhawe'),(v_city_id,'Cansuje'),
(v_city_id,'Caorasan'),(v_city_id,'Casili Norte'),(v_city_id,'Casili Sur'),
(v_city_id,'Catibod'),(v_city_id,'Cavite'),(v_city_id,'Cogon'),
(v_city_id,'Compostela'),(v_city_id,'Daanlungsod'),(v_city_id,'Dalingding Norte'),
(v_city_id,'Dalingding Sur'),(v_city_id,'De la Paz'),(v_city_id,'Estaca Norte'),
(v_city_id,'Estaca Sur'),(v_city_id,'Imelda'),(v_city_id,'Kaibigan'),
(v_city_id,'Lanao'),(v_city_id,'Lataban'),(v_city_id,'Libo'),
(v_city_id,'Macaas'),(v_city_id,'Mangoto'),(v_city_id,'Poog'),
(v_city_id,'Poblacion'),(v_city_id,'Santa Cruz'),(v_city_id,'Santander'),
(v_city_id,'Sirao'),(v_city_id,'Ubay'),(v_city_id,'Villahermosa')
ON CONFLICT DO NOTHING;

-- ============================================================
-- SMALLER MUNICIPALITIES (Poblacion only seed)
-- ============================================================

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Alcantara' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Cabadiangan'),(v_city_id,'Cabil-isan'),(v_city_id,'Candabong'),
(v_city_id,'Lawaan'),(v_city_id,'Manga'),(v_city_id,'Palanas'),
(v_city_id,'Poblacion'),(v_city_id,'Polo'),(v_city_id,'Salagpongan'),
(v_city_id,'San Roque'),(v_city_id,'Tubod')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Alegria' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Compostela'),(v_city_id,'Guadalupe'),(v_city_id,'Legaspi'),
(v_city_id,'Lepanto'),(v_city_id,'Lombo'),(v_city_id,'Malaguit'),
(v_city_id,'Malones'),(v_city_id,'Montañeza'),(v_city_id,'Poblacion'),
(v_city_id,'Santa Filomena')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Aloguinsan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Angilan'),(v_city_id,'Bojo'),(v_city_id,'Bonbon'),
(v_city_id,'Cebu II'),(v_city_id,'Dagsa'),(v_city_id,'Liki'),
(v_city_id,'Looc'),(v_city_id,'Nacat'),(v_city_id,'Poblacion'),
(v_city_id,'Sungsong')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Asturias' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bago'),(v_city_id,'Bairan'),(v_city_id,'Banban'),
(v_city_id,'Baye'),(v_city_id,'Calogo'),(v_city_id,'Casion'),
(v_city_id,'Casoy'),(v_city_id,'Cawit'),(v_city_id,'Cogon'),
(v_city_id,'Cogor'),(v_city_id,'Dakit'),(v_city_id,'General Arceo'),
(v_city_id,'Lanao'),(v_city_id,'Langub'),(v_city_id,'Looc'),
(v_city_id,'Lubo'),(v_city_id,'Poblacion Norte'),(v_city_id,'Poblacion Sur'),
(v_city_id,'Tagsa'),(v_city_id,'Tugas'),(v_city_id,'Tungkay')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Badian' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Alawijao'),(v_city_id,'Balhaan'),(v_city_id,'Banhigan'),
(v_city_id,'Basak'),(v_city_id,'Basiao'),(v_city_id,'Bato'),
(v_city_id,'Bugas'),(v_city_id,'Calangcang'),(v_city_id,'Candiis'),
(v_city_id,'Dagohoy'),(v_city_id,'Daan-Lungsod'),(v_city_id,'Gawisan'),
(v_city_id,'Lambug'),(v_city_id,'Malhiao'),(v_city_id,'Manduyong'),
(v_city_id,'Matutinao'),(v_city_id,'Patong'),(v_city_id,'Poblacion'),
(v_city_id,'Sanlagan'),(v_city_id,'Santa Cruz'),(v_city_id,'Sonog'),
(v_city_id,'Sur'),(v_city_id,'Talayong'),(v_city_id,'Taytay'),
(v_city_id,'Tigbao'),(v_city_id,'Tiguib'),(v_city_id,'Tubod')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Binaliw' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Binaliw') ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Boljoon' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Arbor'),(v_city_id,'Baclayan'),(v_city_id,'Bongdo'),
(v_city_id,'Camburoy'),(v_city_id,'Colase'),(v_city_id,'Comadog'),
(v_city_id,'Gahoy'),(v_city_id,'Lo-oc'),(v_city_id,'Nangka'),
(v_city_id,'Poblacion'),(v_city_id,'Southern Poblacion')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Catmon' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Agsuwao'),(v_city_id,'Amancion'),(v_city_id,'Anapog'),
(v_city_id,'Bactas'),(v_city_id,'Basak'),(v_city_id,'Binongkalan'),
(v_city_id,'Bongyas'),(v_city_id,'Cabunga'),(v_city_id,'Cambanay'),
(v_city_id,'Cambayog'),(v_city_id,'Canchunos'),(v_city_id,'Corazon'),
(v_city_id,'Duyan'),(v_city_id,'Flores'),(v_city_id,'Ginabucan'),
(v_city_id,'Macaas'),(v_city_id,'Panalipan'),(v_city_id,'Poblacion'),
(v_city_id,'San Jose'),(v_city_id,'Tabili'),(v_city_id,'Tuwak')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Dumanjug' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Balaygtiki'),(v_city_id,'Bitoon'),(v_city_id,'Bulak'),
(v_city_id,'Bulak Butlosan'),(v_city_id,'Cabiangon'),(v_city_id,'Camboang'),
(v_city_id,'Candabong'),(v_city_id,'Cogon'),(v_city_id,'Colonia'),
(v_city_id,'Daan-Lungsod'),(v_city_id,'Dalingding'),(v_city_id,'Dayhagon'),
(v_city_id,'Don Virgilio Gonzales'),(v_city_id,'Gibitngil'),(v_city_id,'Guadalupe'),
(v_city_id,'Ilaya'),(v_city_id,'Kabangkalan'),(v_city_id,'Lamak'),
(v_city_id,'Lawaan'),(v_city_id,'Luk-ob'),(v_city_id,'Mahanlud'),
(v_city_id,'Manlapay'),(v_city_id,'Masa'),(v_city_id,'Matalid'),
(v_city_id,'Motherlode'),(v_city_id,'Notop'),(v_city_id,'Obong'),
(v_city_id,'Oslob'),(v_city_id,'Pisaan'),(v_city_id,'Poblacion'),
(v_city_id,'Tangil'),(v_city_id,'Tapon'),(v_city_id,'Tubigan'),
(v_city_id,'Tubod')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Ginatilan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Anao'),(v_city_id,'Cagsing'),(v_city_id,'Calabawan'),
(v_city_id,'Cambadbad'),(v_city_id,'Canunsong'),(v_city_id,'Capio-an'),
(v_city_id,'Casay'),(v_city_id,'Cawit'),(v_city_id,'Guiwanon'),
(v_city_id,'Looc'),(v_city_id,'Malapoc Norte'),(v_city_id,'Mangaco'),
(v_city_id,'Palanas'),(v_city_id,'Poblacion'),(v_city_id,'Salamanca'),
(v_city_id,'San Roque')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Madridejos' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bunakan'),(v_city_id,'Kangwayan'),(v_city_id,'Kaongkod'),
(v_city_id,'Kodia'),(v_city_id,'Maalat'),(v_city_id,'Malbago'),
(v_city_id,'Mano'),(v_city_id,'Poblacion'),(v_city_id,'Tabagak'),
(v_city_id,'Talangnan'),(v_city_id,'Tarong'),(v_city_id,'Tugas')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Malabuyoc' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Armeña'),(v_city_id,'Barangay I'),(v_city_id,'Barangay II'),
(v_city_id,'Barangay III'),(v_city_id,'Barangay IV'),(v_city_id,'Barangay V'),
(v_city_id,'Lombo'),(v_city_id,'Looc'),(v_city_id,'Nug-as'),
(v_city_id,'Tuburan')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Medellin' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Antipolo'),(v_city_id,'Canhabagat'),(v_city_id,'Caputatan Norte'),
(v_city_id,'Caputatan Sur'),(v_city_id,'Curva'),(v_city_id,'Daanlungsod'),
(v_city_id,'Dayhagon'),(v_city_id,'Gibitngil'),(v_city_id,'Ilihan'),
(v_city_id,'Kawit'),(v_city_id,'Lamintak Norte'),(v_city_id,'Lamintak Sur'),
(v_city_id,'Luy-a'),(v_city_id,'Maharuhay'),(v_city_id,'Mahayahay'),
(v_city_id,'Poblacion'),(v_city_id,'Tindog'),(v_city_id,'Tolosa')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Pilar' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Biking'),(v_city_id,'Cawit'),(v_city_id,'Dapdap'),
(v_city_id,'Esperanza'),(v_city_id,'Gracia'),(v_city_id,'Guiwanon'),
(v_city_id,'Lanao'),(v_city_id,'Montserrat'),(v_city_id,'Poblacion'),
(v_city_id,'Punta'),(v_city_id,'Tabahab'),(v_city_id,'Teguis')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Poro' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Adela'),(v_city_id,'Altavista'),(v_city_id,'Cagcagan'),
(v_city_id,'Caosian'),(v_city_id,'Daan Paz'),(v_city_id,'Eastern Poblacion'),
(v_city_id,'Esperanza'),(v_city_id,'Libertad'),(v_city_id,'Mabini'),
(v_city_id,'Montserrat'),(v_city_id,'Paz'),(v_city_id,'Rizal'),
(v_city_id,'San Jose'),(v_city_id,'Teguis'),(v_city_id,'Western Poblacion')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Ronda' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Butong'),(v_city_id,'Can-abuhon'),(v_city_id,'Canduling'),
(v_city_id,'Cansalonoy'),(v_city_id,'Cansumbol'),(v_city_id,'Dugyan'),
(v_city_id,'Gibitngil'),(v_city_id,'Libo'),(v_city_id,'Mabogo'),
(v_city_id,'Palanas'),(v_city_id,'Poblacion'),(v_city_id,'Sacsac'),
(v_city_id,'Sambagon'),(v_city_id,'Sudlon'),(v_city_id,'Sulod')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Samboan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Basak'),(v_city_id,'Bonbon'),(v_city_id,'Calatagan'),
(v_city_id,'Camburoy'),(v_city_id,'Canorong'),(v_city_id,'Colase'),
(v_city_id,'Dalang'),(v_city_id,'Guiwanon'),(v_city_id,'Looc'),
(v_city_id,'Mainit'),(v_city_id,'Malalay'),(v_city_id,'Poblacion'),
(v_city_id,'Santa Cruz'),(v_city_id,'Taglobo')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'San Francisco' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Cabunga'),(v_city_id,'Cagcagan'),(v_city_id,'Compostela'),
(v_city_id,'Eastern Poblacion'),(v_city_id,'Esperanza'),(v_city_id,'Libertad'),
(v_city_id,'Mabini'),(v_city_id,'Montserrat'),(v_city_id,'Northern Poblacion'),
(v_city_id,'Rizal'),(v_city_id,'San Jose'),(v_city_id,'Southern Poblacion'),
(v_city_id,'Teguis'),(v_city_id,'Western Poblacion')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Santa Fe' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Balidbid'),(v_city_id,'Hagdan'),(v_city_id,'Hilantagaan'),
(v_city_id,'Kinatarcan'),(v_city_id,'Langub'),(v_city_id,'Libertad'),
(v_city_id,'Maricaban'),(v_city_id,'Okoy'),(v_city_id,'Poblacion'),
(v_city_id,'Pooc'),(v_city_id,'Talisay')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Santander' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bunlan'),(v_city_id,'Cahasan'),(v_city_id,'Canlumampao'),
(v_city_id,'Liloan'),(v_city_id,'Lip-tong'),(v_city_id,'Looc'),
(v_city_id,'Pasil'),(v_city_id,'Poblacion'),(v_city_id,'Talisay')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Sogod' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Ampongol'),(v_city_id,'Bagakay'),(v_city_id,'Bagatayam'),
(v_city_id,'Bawo'),(v_city_id,'Cabalawan'),(v_city_id,'Cabcaban'),
(v_city_id,'Cagay'),(v_city_id,'Cambadbad'),(v_city_id,'Canmano'),
(v_city_id,'Canungao'),(v_city_id,'Catig'),(v_city_id,'Daanlungsod'),
(v_city_id,'Gawi'),(v_city_id,'Guimbaoyan Norte'),(v_city_id,'Guimbaoyan Sur'),
(v_city_id,'Guiwanon'),(v_city_id,'Liki'),(v_city_id,'Luca'),
(v_city_id,'Mohon'),(v_city_id,'Panas'),(v_city_id,'Poblacion'),
(v_city_id,'Salmeron'),(v_city_id,'Sorsogon'),(v_city_id,'Tananas'),
(v_city_id,'Tibadlonon'),(v_city_id,'Tulic'),(v_city_id,'Usocan')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Tabogon' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Cadunan'),(v_city_id,'Canamucan'),(v_city_id,'Cogon'),
(v_city_id,'Ibo'),(v_city_id,'Ilihan'),(v_city_id,'Lanao'),
(v_city_id,'Loong'),(v_city_id,'Mabunao'),(v_city_id,'Malobago'),
(v_city_id,'Manguiao'),(v_city_id,'New Bago'),(v_city_id,'Poblacion'),
(v_city_id,'San Isidro'),(v_city_id,'Somosa'),(v_city_id,'Tabunok'),
(v_city_id,'Tapilon'),(v_city_id,'Tigbawan'),(v_city_id,'Tilhaong'),
(v_city_id,'Tulang'),(v_city_id,'Villahermosa')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Tabuelan' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Bagong Silang'),(v_city_id,'Bongdo'),(v_city_id,'Buenavista'),
(v_city_id,'Cabungahan'),(v_city_id,'Cadaruhan Norte'),(v_city_id,'Cadaruhan Sur'),
(v_city_id,'Cagay'),(v_city_id,'Cambance'),(v_city_id,'Cansundo'),
(v_city_id,'Ilihan'),(v_city_id,'Looc'),(v_city_id,'Managase'),
(v_city_id,'Owak'),(v_city_id,'Poblacion'),(v_city_id,'Santa Cruz'),
(v_city_id,'Siocon'),(v_city_id,'Tagaytay'),(v_city_id,'Tuble'),
(v_city_id,'Tubod'),(v_city_id,'Villahermosa')
ON CONFLICT DO NOTHING;

SELECT id INTO v_city_id FROM address_cities WHERE name = 'Tudela' LIMIT 1;
INSERT INTO address_barangays (city_id, name) VALUES
(v_city_id,'Cagcagan'),(v_city_id,'Daan Paz'),(v_city_id,'Hilantagaan'),
(v_city_id,'Libertad'),(v_city_id,'Lugo'),(v_city_id,'Mediana'),
(v_city_id,'Poblacion'),(v_city_id,'San Agustin'),(v_city_id,'San Miguel'),
(v_city_id,'San Pedro')
ON CONFLICT DO NOTHING;

END$$;

-- ---------------------------------------------------------------------------
-- 6. SEARCH STORED PROCEDURE
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_search_cebu_address(p_query TEXT, p_limit INT DEFAULT 10)
RETURNS TABLE (
    barangay_id  INT,
    barangay     TEXT,
    city_id      INT,
    city         TEXT,
    province_id  INT,
    province     TEXT,
    display_text TEXT
)
LANGUAGE plpgsql AS $$
DECLARE v_q TEXT;
BEGIN
    v_q := '%' || LOWER(TRIM(p_query)) || '%';
    RETURN QUERY
    SELECT
        b.id                                                    AS barangay_id,
        b.name::TEXT                                            AS barangay,
        c.id                                                    AS city_id,
        c.name::TEXT                                            AS city,
        pr.id                                                   AS province_id,
        pr.name::TEXT                                           AS province,
        (b.name || ', ' || c.name || ', ' || pr.name)::TEXT    AS display_text
    FROM address_barangays b
    JOIN address_cities    c  ON c.id  = b.city_id
    JOIN address_provinces pr ON pr.id = c.province_id
    WHERE LOWER(b.name) LIKE v_q
       OR LOWER(c.name) LIKE v_q
    ORDER BY
        CASE WHEN LOWER(b.name) LIKE LOWER(TRIM(p_query)) || '%' THEN 0 ELSE 1 END,
        b.name
    LIMIT p_limit;
END;
$$;

-- ---------------------------------------------------------------------------
-- 7. SAVE ADDRESS STORED PROCEDURE
-- ---------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE sp_save_address(
    IN  p_street      TEXT,
    IN  p_barangay_id INT,
    IN  p_city_id     INT,
    IN  p_province_id INT,
    IN  p_zip_code    TEXT,
    OUT p_address_id  INT
)
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO addresses (street, barangay_id, city_id, province_id, zip_code)
    VALUES (p_street, p_barangay_id, p_city_id, p_province_id, NULLIF(p_zip_code,''))
    RETURNING id INTO p_address_id;
END;
$$;
