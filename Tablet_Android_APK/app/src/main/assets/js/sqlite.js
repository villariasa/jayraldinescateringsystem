// In-browser SQLite (via sql.js / WASM) — the tablet's actual local
// database, persisted to IndexedDB as raw .db bytes. Schema is a byte-for-
// byte port of the original Tablet app's utils/sqlite_schema.py so the
// exported .db file drops straight into the PC app's existing "Merge
// Backup File Into This Database" import feature — no server involved
// anywhere in this flow.
const IDB_NAME = "jc_kiosk_sqlite";
const IDB_STORE = "dbfile";
const IDB_KEY = "catering_pwa.db";

const SCHEMA_SQL = `
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    cus_id INTEGER PRIMARY KEY AUTOINCREMENT,
    cus_name TEXT NOT NULL,
    cus_contact TEXT,
    cus_email TEXT,
    cus_address TEXT,
    cus_address_id INTEGER,
    cus_loyalty_tier TEXT DEFAULT 'Bronze',
    cus_total_events INTEGER DEFAULT 0,
    cus_total_spent REAL DEFAULT 0.0,
    cus_status TEXT DEFAULT 'Active',
    cus_notes TEXT,
    cus_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS menu_categories (
    mc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mc_name TEXT NOT NULL UNIQUE,
    mc_is_active INTEGER DEFAULT 1,
    mc_sort INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS menu_items (
    mi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    mi_name TEXT NOT NULL,
    name TEXT,
    mi_category TEXT NOT NULL,
    category TEXT,
    mi_package_tier TEXT DEFAULT 'Standard',
    mi_package TEXT DEFAULT 'Standard',
    package_tier TEXT DEFAULT 'Standard',
    package TEXT DEFAULT 'Standard',
    mi_price REAL NOT NULL,
    price REAL,
    mi_status TEXT DEFAULT 'Available',
    status TEXT DEFAULT 'Available',
    mi_description TEXT,
    description TEXT,
    mi_image TEXT DEFAULT '',
    image TEXT DEFAULT '',
    mi_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS packages (
    pkg_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pkg_name TEXT NOT NULL UNIQUE,
    pkg_description TEXT,
    pkg_price_per_pax REAL NOT NULL,
    pkg_min_pax INTEGER DEFAULT 30,
    pkg_image TEXT DEFAULT '',
    image TEXT DEFAULT '',
    pkg_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS package_items (
    pi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pi_package_id INTEGER NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
    pi_menu_item_id INTEGER REFERENCES menu_items(mi_id),
    pi_item_name TEXT,
    pi_category TEXT,
    pi_custom_price REAL DEFAULT 0.0,
    pi_quantity INTEGER DEFAULT 1,
    pi_bucket_id INTEGER
);

CREATE TABLE IF NOT EXISTS package_buckets (
    pb_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pb_package_id INTEGER NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
    pb_name TEXT NOT NULL,
    pb_limit INTEGER NOT NULL DEFAULT 1,
    pb_categories TEXT NOT NULL DEFAULT '[]',
    pb_sort INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS bookings (
    bk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bk_booking_ref TEXT NOT NULL UNIQUE,
    bk_customer_id INTEGER REFERENCES customers(cus_id),
    bk_customer_name TEXT NOT NULL,
    bk_address TEXT,
    bk_event_date DATE NOT NULL,
    bk_event_time TIME DEFAULT '18:00',
    bk_event_end_time TIME,
    bk_venue TEXT,
    bk_occasion TEXT,
    bk_pax INTEGER NOT NULL,
    bk_total_amount REAL NOT NULL,
    bk_base_total REAL,
    bk_payment_mode TEXT DEFAULT 'Cash',
    bk_amount_paid REAL DEFAULT 0.0,
    bk_down_payment REAL DEFAULT 0.0,
    bk_down_payment_status TEXT DEFAULT 'PENDING',
    bk_menu_type TEXT DEFAULT 'package',
    bk_package_id INTEGER REFERENCES packages(pkg_id),
    bk_notes TEXT,
    bk_status TEXT DEFAULT 'PENDING',
    bk_color_theme TEXT DEFAULT '#2563EB',
    bk_cancellation_reason TEXT,
    bk_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_menu_items (
    bmi_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bmi_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    bmi_item_id INTEGER REFERENCES menu_items(mi_id),
    bmi_item_name TEXT,
    bmi_category TEXT,
    bmi_price REAL DEFAULT 0.0,
    bmi_quantity INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS invoices (
    inv_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inv_booking_id INTEGER REFERENCES bookings(bk_id) ON DELETE CASCADE,
    inv_invoice_ref TEXT UNIQUE,
    inv_invoice_number TEXT,
    inv_customer_name TEXT,
    inv_event_date DATE,
    inv_total_amount REAL,
    inv_amount_paid REAL DEFAULT 0.0,
    inv_balance REAL,
    inv_status TEXT DEFAULT 'Unpaid',
    inv_down_payment REAL DEFAULT 0.0,
    inv_payment_verified INTEGER DEFAULT 0,
    inv_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_records (
    pr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_invoice_id INTEGER REFERENCES invoices(inv_id) ON DELETE CASCADE,
    pr_amount REAL NOT NULL,
    pr_payment_date DATE NOT NULL,
    pr_payment_method TEXT DEFAULT 'Cash',
    pr_method TEXT DEFAULT 'Cash',
    pr_reference_number TEXT,
    pr_notes TEXT,
    pr_note TEXT,
    pr_is_downpayment INTEGER DEFAULT 0,
    pr_is_verified INTEGER DEFAULT 0,
    pr_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS booking_additional_charges (
    ac_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ac_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ac_description TEXT NOT NULL,
    ac_amount REAL NOT NULL DEFAULT 0.0,
    ac_date_added DATE NOT NULL,
    ac_added_by TEXT,
    ac_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS address_provinces (
    ap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ap_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS address_cities (
    ac_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ac_province_id INTEGER REFERENCES address_provinces(ap_id),
    ac_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS address_barangays (
    ab_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ab_city_id INTEGER REFERENCES address_cities(ac_id),
    ab_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS addresses (
    ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_street TEXT,
    ad_barangay_id INTEGER REFERENCES address_barangays(ab_id),
    ad_city_id INTEGER REFERENCES address_cities(ac_id),
    ad_province_id INTEGER REFERENCES address_provinces(ap_id),
    ad_zip_code TEXT
);

CREATE TABLE IF NOT EXISTS customer_addresses (
    ca_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ca_customer_id INTEGER REFERENCES customers(cus_id) ON DELETE CASCADE,
    ca_address_id INTEGER REFERENCES addresses(ad_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS terms_acknowledgements (
    ta_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ta_booking_id INTEGER NOT NULL REFERENCES bookings(bk_id) ON DELETE CASCADE,
    ta_version TEXT NOT NULL,
    ta_acknowledged INTEGER DEFAULT 0,
    ta_acknowledged_at DATETIME,
    ta_customer_name TEXT,
    ta_created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tablet_master_sync (
    tms_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tms_source_export_version TEXT,
    tms_imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    tms_packages_count INTEGER DEFAULT 0,
    tms_menu_items_count INTEGER DEFAULT 0,
    tms_customers_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS occasions (
    occ_id INTEGER PRIMARY KEY AUTOINCREMENT,
    occ_name TEXT NOT NULL UNIQUE,
    occ_description TEXT,
    occ_is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS entity_images (
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    image_data TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS pending_package_images (
    pkg_id INTEGER PRIMARY KEY,
    image_data TEXT,
    remove_image INTEGER DEFAULT 0,
    sync_status TEXT DEFAULT 'pending',
    last_error TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pending_menu_images (
    mi_id INTEGER PRIMARY KEY,
    item_name TEXT DEFAULT '',
    image_data TEXT,
    remove_image INTEGER DEFAULT 0,
    sync_status TEXT DEFAULT 'pending',
    last_error TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
`;

const CEBU_CITIES = [
  ["Cebu City", ["Apas", "Banilad", "Basak San Nicolas", "Busay", "Camputhaw", "Capitol Site", "Guadalupe", "Kasambagan", "Lahug", "Mabolo", "Pardo", "Punta Princesa", "Sambag I", "Sambag II", "Talamban", "Tisa", "Zapatera"]],
  ["Mandaue City", ["Alang-alang", "Bakilid", "Banilad", "Cabancalan", "Centro", "Guizo", "Ibabao-Estancia", "Maguikay", "Paknaan", "Subangdaku", "Tipolo"]],
  ["Lapu-Lapu City", ["Basak", "Gun-ob", "Ibo", "Mactan", "Maribago", "Marigondon", "Pajac", "Pajo", "Poblacion", "Pusok", "Subabasbas"]],
  ["Talisay City", ["Bulacao", "Cansojong", "Dumlog", "Lawaan I", "Lawaan II", "Mohon", "Poblacion", "San Roque", "Tabunok", "Tangke"]],
  ["Consolacion", ["Casili", "Cansaga", "Danlag", "Jugan", "Nangka", "Pitogo", "Poblacion", "Tayud"]],
  ["Liloan", ["Catarman", "Cotcot", "Jubay", "Poblacion", "San Roque", "San Vicente", "Yati"]],
];

// STRICT LIVE DB REQUIREMENT:
// All packages, menu items, and customer data MUST come strictly from the
// Live PostgreSQL Database over LAN sync. No mock or fallback records allowed.

let SQL = null;
let db = null;
let saveTimer = null;

function idbOpen() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(IDB_STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbLoad() {
  const idb = await idbOpen();
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, "readonly");
    const req = tx.objectStore(IDB_STORE).get(IDB_KEY);
    req.onsuccess = () => resolve(req.result || null);
    req.onerror = () => reject(req.error);
  });
}

async function idbSave(bytes) {
  const idb = await idbOpen();
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, "readwrite");
    tx.objectStore(IDB_STORE).put(bytes, IDB_KEY);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    const bytes = db.export();
    idbSave(bytes).catch((err) => console.error("DB save failed:", err));
  }, 300);
}

function seedDefaults() {
  const countOf = (table) => db.exec(`SELECT COUNT(*) FROM ${table}`)[0].values[0][0];

  if (countOf("address_provinces") === 0) {
    db.run("INSERT OR IGNORE INTO address_provinces (ap_name) VALUES ('Cebu')");
    const provId = db.exec("SELECT ap_id FROM address_provinces WHERE ap_name='Cebu'")[0].values[0][0];
    for (const [cityName, barangays] of CEBU_CITIES) {
      db.run("INSERT INTO address_cities (ac_province_id, ac_name) VALUES (?, ?)", [provId, cityName]);
      const cityId = db.exec("SELECT last_insert_rowid()")[0].values[0][0];
      for (const b of barangays) {
        db.run("INSERT INTO address_barangays (ab_city_id, ab_name) VALUES (?, ?)", [cityId, b]);
      }
    }
  }

  // Seed Default Offline Packages if empty
  try {
    if (countOf("packages") === 0) {
      const defaultPkgs = [
        ["Classic Celebration Package", "Standard catering buffet package with 4 main dishes, rice, dessert, and drinks.", 350.0, 30],
        ["Premium Grand Feast", "Deluxe buffet with 6 main dishes, roast pork lechon belly, 2 desserts, and beverage bar.", 550.0, 50],
        ["Executive VIP Buffet", "Top-tier package with live carving station, 7 signature mains, seafood, and full dessert table.", 850.0, 50],
      ];
      for (const [name, desc, price, min_pax] of defaultPkgs) {
        db.run("INSERT OR IGNORE INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax) VALUES (?, ?, ?, ?)", [name, desc, price, min_pax]);
      }
    }
  } catch (err) {
    console.warn("[SQLite] Package seed note:", err);
  }

  // Seed Default Offline Menu Items if empty
  try {
    if (countOf("menu_items") === 0) {
      const defaultItems = [
        ["Special Pork Humba", "Main Course", "Standard", 450.0, "Available", "Slow cooked pork belly with banana blossoms"],
        ["Lechon Belly Roast", "Main Course", "Premium", 1200.0, "Available", "Crispy rolled pork belly with herbs"],
        ["Chicken Pandan", "Main Course", "Standard", 380.0, "Available", "Wrapped savory fried chicken"],
        ["Garlic Butter Buttered Shrimp", "Main Course", "Premium", 550.0, "Available", "Fresh prawns in savory garlic butter"],
        ["Sweet & Sour Fish Fillet", "Main Course", "Standard", 360.0, "Available", "Crispy fish fillet in pineapple sweet sauce"],
        ["Beef with Broccoli", "Main Course", "Standard", 480.0, "Available", "Tender beef slices in oyster glaze"],
        ["Biko with Latik", "Dessert", "Standard", 250.0, "Available", "Traditional sweet sticky rice"],
        ["Mango Tapioca", "Dessert", "Standard", 220.0, "Available", "Chilled mango cubes with sago pearls"],
        ["Refillable Iced Tea", "Drinks", "Standard", 150.0, "Available", "House blend lemon iced tea"],
      ];
      for (const [name, cat, pkg, price, status, desc] of defaultItems) {
        db.run("INSERT OR IGNORE INTO menu_items (mi_name, name, mi_category, category, mi_package_tier, mi_package, mi_price, price, mi_status, status, mi_description, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [name, name, cat, cat, pkg, pkg, price, price, status, status, desc, desc]);
      }
    }
  } catch (err) {
    console.warn("[SQLite] Menu items seed note:", err);
  }

  // Seed Default Package Items if empty
  try {
    if (countOf("package_items") === 0) {
      const pkgs = db.exec("SELECT pkg_id FROM packages")[0]?.values || [];
      const items = db.exec("SELECT mi_id, mi_name, mi_category FROM menu_items")[0]?.values || [];
      for (const [pkgId] of pkgs) {
        for (const [miId, miName, miCat] of items) {
          db.run("INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_item_name, pi_category, pi_quantity) VALUES (?, ?, ?, ?, 1)", [pkgId, miId, miName, miCat]);
        }
      }
    }
  } catch (err) {
    console.warn("[SQLite] Package items seed note:", err);
  }

  // Seed Menu Categories strictly from existing menu items only if empty (NO predefined categories!)
  try {
    // Clean up any stale predefined categories if they have no dishes in menu_items
    const stalePredefined = ["Beef", "Pork", "Chicken", "Fish & Seafood", "Pasta & Noodles", "Vegetables", "Dessert", "Beverage", "Add-on"];
    for (const cat of stalePredefined) {
      const cnt = db.exec("SELECT COUNT(*) FROM menu_items WHERE mi_category = ?", [cat])[0]?.values[0][0] || 0;
      if (cnt === 0) {
        db.run("DELETE FROM menu_categories WHERE mc_name = ?", [cat]);
      }
    }

    if (countOf("menu_categories") === 0) {
      const existingCats = db.exec("SELECT DISTINCT mi_category FROM menu_items WHERE mi_category IS NOT NULL AND TRIM(mi_category) != ''")[0]?.values || [];
      let nextSort = 0;
      for (const [cat] of existingCats) {
        const c = String(cat || "").trim();
        if (c) {
          db.run("INSERT OR IGNORE INTO menu_categories (mc_name, mc_sort, mc_is_active) VALUES (?, ?, 1)", [c, nextSort++]);
        }
      }
    }
  } catch (err) {
    console.warn("[SQLite] Menu categories seed note:", err);
  }

  // Seed Default Occasions if empty
  try {
    if (countOf("occasions") === 0) {
      const defaultOccasions = [
        "Wedding", "Birthday", "Debut", "Corporate Event", "Anniversary",
        "Christening", "Graduation", "Holiday Party"
      ];
      for (const occ of defaultOccasions) {
        db.run("INSERT OR IGNORE INTO occasions (occ_name, occ_is_active) VALUES (?, 1)", [occ]);
      }
    }
  } catch (err) {
    console.warn("[SQLite] Occasions seed note:", err);
  }
}

export async function initDb() {
  if (db) return db;
  SQL = await window.initSqlJs({ locateFile: (f) => `vendor/${f}` });
  let existing = await idbLoad();


  db = existing ? new SQL.Database(new Uint8Array(existing)) : new SQL.Database();
  db.run(SCHEMA_SQL);
  try { db.run("ALTER TABLE bookings ADD COLUMN sync_status TEXT DEFAULT 'pending';"); } catch (_) {}
  try { db.run("ALTER TABLE bookings ADD COLUMN bk_event_end_time TIME;"); } catch (_) {}
  try { db.run("ALTER TABLE customers ADD COLUMN sync_status TEXT DEFAULT 'pending';"); } catch (_) {}
  try { db.run("ALTER TABLE packages ADD COLUMN pkg_image TEXT DEFAULT '';"); } catch (_) {}
  try { db.run("ALTER TABLE packages ADD COLUMN image TEXT DEFAULT '';"); } catch (_) {}
  try { db.run("ALTER TABLE menu_items ADD COLUMN mi_image TEXT DEFAULT '';"); } catch (_) {}
  try { db.run("ALTER TABLE menu_items ADD COLUMN image TEXT DEFAULT '';"); } catch (_) {}
  try { db.run("ALTER TABLE occasions ADD COLUMN occ_is_active INTEGER DEFAULT 1;"); } catch (_) {}
  try { db.run("ALTER TABLE package_items ADD COLUMN pi_bucket_id INTEGER;"); } catch (_) {}
  try {
    db.run(`
      CREATE TABLE IF NOT EXISTS package_buckets (
        pb_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pb_package_id INTEGER NOT NULL REFERENCES packages(pkg_id) ON DELETE CASCADE,
        pb_name TEXT NOT NULL,
        pb_limit INTEGER NOT NULL DEFAULT 1,
        pb_categories TEXT NOT NULL DEFAULT '[]',
        pb_sort INTEGER DEFAULT 0
      );
    `);
  } catch (_) {}
  try {
    db.run(`
      CREATE TABLE IF NOT EXISTS pending_package_images (
        pkg_id INTEGER PRIMARY KEY,
        image_data TEXT,
        remove_image INTEGER DEFAULT 0,
        sync_status TEXT DEFAULT 'pending',
        last_error TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
  } catch (_) {}
  try {
    db.run(`
      CREATE TABLE IF NOT EXISTS pending_menu_images (
        mi_id INTEGER PRIMARY KEY,
        item_name TEXT DEFAULT '',
        image_data TEXT,
        remove_image INTEGER DEFAULT 0,
        sync_status TEXT DEFAULT 'pending',
        last_error TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
    `);
  } catch (_) {}
  seedDefaults();
  scheduleSave();
  return db;
}

export function getDb() {
  if (!db) throw new Error("Database not initialized — call initDb() first.");
  return db;
}

/** Rows as plain objects, like Python's sqlite3.Row -> dict. */
export function fetchAll(sql, params = []) {
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const rows = [];
  while (stmt.step()) rows.push(stmt.getAsObject());
  stmt.free();
  return rows;
}

export function fetchOne(sql, params = []) {
  const rows = fetchAll(sql, params);
  return rows.length ? rows[0] : null;
}

/** INSERT/UPDATE/DELETE. Returns last_insert_rowid() for inserts. */
export function run(sql, params = []) {
  db.run(sql, params);
  scheduleSave();
  return db.exec("SELECT last_insert_rowid()")[0].values[0][0];
}

export function computeInvoiceStatus(totalAmount, amountPaid) {
  totalAmount = totalAmount || 0;
  amountPaid = amountPaid || 0;
  const remaining = totalAmount - amountPaid;
  if (totalAmount > 0 && remaining <= 0) return "Paid";
  if (amountPaid > 0) return "Partial";
  return "Unpaid";
}

/** Raw bytes of the current database — this IS the Tablet -> PC export
 * (see module docstring): schema-identical to the PC app's tables, so this
 * file can be handed directly to the PC app's "Merge Backup File" import. */
export function exportDbBytes() {
  return db.export();
}

/** Replace all master-data tables (packages/menu/package_items) — used by
 * master-data import from a PC-exported .db or .xlsx. Safe against
 * historical orders because bookings snapshot their own prices at the time
 * they were placed (booking_menu_items/bk_base_total/booking_additional_
 * charges never reference packages/menu_items live). */
export function replaceMasterTablesWithDbIds({ packages = [], menuItems = [], packageItems = [], packageBuckets = [], customers = [] }) {
  const stats = { packages: 0, menu_items: 0, package_items: 0, package_buckets: 0, customers: 0 };
  db.run("PRAGMA foreign_keys = OFF;");
  try {
    if (packages && packages.length > 0) {
      db.run("DELETE FROM package_buckets");
      db.run("DELETE FROM package_items");
      db.run("DELETE FROM packages");
      for (const p of packages) {
        const name = (p.pkg_name || p.name || "").trim();
        if (!name) continue;
        const id = p.pkg_id || p.id;
        const desc = p.pkg_description || p.description || "";
        const price = p.pkg_price_per_pax != null ? Number(p.pkg_price_per_pax) : (p.price_per_pax != null ? Number(p.price_per_pax) : 0);
        const minPax = Number(p.pkg_min_pax ?? p.min_pax) || 30;
        const img = p.image || p.pkg_image || "";
        if (id) {
          db.run("INSERT INTO packages (pkg_id, pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax, pkg_image, image) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [id, name, desc, price, minPax, img, img]);
        } else {
          db.run("INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax, pkg_image, image) VALUES (?, ?, ?, ?, ?, ?)",
            [name, desc, price, minPax, img, img]);
        }
        const assignedId = id || db.exec("SELECT last_insert_rowid()")[0].values[0][0];
        if (img) {
          db.run("INSERT OR REPLACE INTO entity_images (entity_type, entity_id, image_data, updated_at) VALUES ('package', ?, ?, CURRENT_TIMESTAMP)",
            [assignedId, img]);
        }
        stats.packages++;
      }
    }

    if (menuItems && menuItems.length > 0) {
      db.run("DELETE FROM menu_items");
      for (const m of menuItems) {
        const name = (m.mi_name || m.name || "").trim();
        if (!name) continue;
        const id = m.mi_id || m.id;
        const cat = m.mi_category || m.category || "Main Course";
        const price = Number(m.mi_price ?? m.price) || 0;
        const status = m.mi_status || m.status || "Available";
        const desc = m.mi_description || m.description || "";
        const img = m.image || m.mi_image || "";
        if (id) {
          db.run("INSERT INTO menu_items (mi_id, mi_name, mi_category, mi_price, mi_status, mi_description, mi_image, image) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [id, name, cat, price, status, desc, img, img]);
        } else {
          db.run("INSERT INTO menu_items (mi_name, mi_category, mi_price, mi_status, mi_description, mi_image, image) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [name, cat, price, status, desc, img, img]);
        }
        const assignedId = id || db.exec("SELECT last_insert_rowid()")[0].values[0][0];
        if (img) {
          db.run("INSERT OR REPLACE INTO entity_images (entity_type, entity_id, image_data, updated_at) VALUES ('menu_item', ?, ?, CURRENT_TIMESTAMP)",
            [assignedId, img]);
        }
        stats.menu_items++;
      }
    }

    if (packageItems && packageItems.length > 0) {
      for (const pi of packageItems) {
        const pkgId = pi.pi_package_id || pi.package_id;
        const itmName = (pi.pi_item_name || pi.item_name || "").trim();
        if (!pkgId || !itmName) continue;
        const bucketId = (pi.pi_bucket_id ?? pi.bucket_id);
        db.run("INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_item_name, pi_category, pi_custom_price, pi_quantity, pi_bucket_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
          [pkgId, pi.pi_menu_item_id || null, itmName, pi.pi_category || "", Number(pi.pi_custom_price || 0), Number(pi.pi_quantity || 1), (bucketId === undefined || bucketId === null || bucketId === "") ? null : Number(bucketId)]);
        stats.package_items++;
      }
    }

    if (packageBuckets && packageBuckets.length > 0) {
      for (const pb of packageBuckets) {
        const pkgId = pb.pb_package_id || pb.package_id;
        const name = (pb.pb_name || pb.name || "").trim();
        if (!pkgId || !name) continue;
        // pb_categories arrives as a JSON string from the server; normalize to a JSON string.
        let catsJson = "[]";
        const rawCats = (pb.pb_categories !== undefined ? pb.pb_categories : pb.categories);
        try {
          if (Array.isArray(rawCats)) catsJson = JSON.stringify(rawCats.map((c) => String(c)));
          else if (typeof rawCats === "string" && rawCats.trim()) catsJson = JSON.stringify(JSON.parse(rawCats).map((c) => String(c)));
        } catch (_) { catsJson = "[]"; }
        const limit = Number(pb.pb_limit ?? pb.limit) || 1;
        const sort = Number(pb.pb_sort ?? pb.sort) || 0;
        const id = pb.pb_id || pb.id;
        if (id) {
          db.run("INSERT INTO package_buckets (pb_id, pb_package_id, pb_name, pb_limit, pb_categories, pb_sort) VALUES (?, ?, ?, ?, ?, ?)",
            [id, pkgId, name, limit, catsJson, sort]);
        } else {
          db.run("INSERT INTO package_buckets (pb_package_id, pb_name, pb_limit, pb_categories, pb_sort) VALUES (?, ?, ?, ?, ?)",
            [pkgId, name, limit, catsJson, sort]);
        }
        stats.package_buckets++;
      }
    }

    if (customers && customers.length > 0) {
      // Remove any previously synced customers to accurately match database state
      db.run("DELETE FROM customers WHERE sync_status = 'synced' OR sync_status IS NULL");
      for (const c of customers) {
        const name = (c.cus_name || c.name || "").trim();
        if (!name) continue;
        const contact = (c.cus_contact || c.contact || "").trim();
        const email = (c.cus_email || c.email || "").trim();
        const address = (c.cus_address || c.address || "").trim();
        const tier = (c.cus_loyalty_tier || c.loyalty_tier || "Bronze").trim();
        const status = (c.cus_status || c.status || "Active").trim();
        const events = Number(c.cus_total_events ?? c.total_events) || 0;
        const spent = Number(c.cus_total_spent ?? c.total_spent) || 0.0;
        const notes = (c.cus_notes || c.notes || "").trim();
        const id = c.cus_id || c.id;

        if (id) {
          db.run("INSERT INTO customers (cus_id, cus_name, cus_contact, cus_email, cus_address, cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes, sync_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced')",
            [id, name, contact, email, address, tier, events, spent, status, notes]);
        } else {
          db.run("INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, cus_notes, sync_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced')",
            [name, contact, email, address, tier, events, spent, status, notes]);
        }
        stats.customers++;
      }
    }

    db.run("INSERT INTO tablet_master_sync (tms_source_export_version, tms_packages_count, tms_menu_items_count, tms_customers_count) VALUES ('Live-PG-Sync', ?, ?, ?)",
      [stats.packages, stats.menu_items, stats.customers]);
  } finally {
    db.run("PRAGMA foreign_keys = ON;");
  }
  scheduleSave();
  return stats;
}

export function replaceMasterTables({ packages = [], menuItems = [], packageItems = [], customers = [] }) {
  const stats = { packages: 0, menu_items: 0, package_items: 0, customers: 0 };
  db.run("PRAGMA foreign_keys = OFF;");
  try {
    db.run("DELETE FROM package_items");
    db.run("DELETE FROM packages");
    db.run("DELETE FROM menu_items");

    const pkgIdByName = {};
    for (const p of packages) {
      const name = (p.name || "").trim();
      if (!name) continue;
      db.run("INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax) VALUES (?, ?, ?, ?)",
        [name, p.description || "", Number(p.price_per_pax) || 0, Number(p.min_pax) || 30]);
      pkgIdByName[name.toLowerCase()] = db.exec("SELECT last_insert_rowid()")[0].values[0][0];
      stats.packages++;
    }

    for (const m of menuItems) {
      const name = (m.name || "").trim();
      if (!name) continue;
      db.run("INSERT INTO menu_items (mi_name, mi_category, mi_price, mi_status, mi_description) VALUES (?, ?, ?, ?, ?)",
        [name, m.category || "Other", Number(m.price) || 0, m.status || "Available", m.description || ""]);
      stats.menu_items++;
    }

    for (const pi of packageItems) {
      const pkgId = pkgIdByName[(pi.package_name || "").trim().toLowerCase()];
      const itemName = (pi.item_name || "").trim();
      if (!pkgId || !itemName) continue;
      db.run("INSERT INTO package_items (pi_package_id, pi_item_name, pi_category, pi_custom_price, pi_quantity) VALUES (?, ?, ?, ?, ?)",
        [pkgId, itemName, pi.category || "Other", Number(pi.price) || 0, Number(pi.quantity) || 1]);
      stats.package_items++;
    }

    if (customers.length) {
      for (const c of customers) {
        const name = (c.name || "").trim();
        if (!name) continue;
        const contact = (c.contact || "").trim();
        const existing = contact
          ? fetchOne("SELECT cus_id FROM customers WHERE cus_contact = ? AND cus_contact != ''", [contact])
          : fetchOne("SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(?)", [name]);
        if (existing) {
          db.run("UPDATE customers SET cus_name=?, cus_contact=?, cus_email=?, cus_address=? WHERE cus_id=?",
            [name, contact, c.email || "", c.address || "", existing.cus_id]);
        } else {
          db.run("INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status) VALUES (?, ?, ?, ?, 'Active')",
            [name, contact, c.email || "", c.address || ""]);
        }
        stats.customers++;
      }
    }

    db.run("INSERT INTO tablet_master_sync (tms_source_export_version, tms_packages_count, tms_menu_items_count, tms_customers_count) VALUES (?, ?, ?, ?)",
      [new Date().toISOString(), stats.packages, stats.menu_items, stats.customers]);
  } finally {
    db.run("PRAGMA foreign_keys = ON;");
  }
  scheduleSave();
  return stats;
}

/** Import master data from a .db file's raw bytes (a PC-exported SQLite
 * file — opened as a second in-memory database, never touching the live
 * one until we've read out of it). */
export function importMasterDataFromDbBytes(bytes) {
  const srcDb = new SQL.Database(new Uint8Array(bytes));
  try {
    const srcAll = (sql) => {
      try {
        const stmt = srcDb.prepare(sql);
        const rows = [];
        while (stmt.step()) rows.push(stmt.getAsObject());
        stmt.free();
        return rows;
      } catch (_) { return []; }
    };
    const srcPackages = srcAll("SELECT * FROM packages");
    const srcItems = srcAll("SELECT * FROM menu_items");
    const srcPkgItems = srcAll("SELECT * FROM package_items");
    const srcCustomers = srcAll("SELECT * FROM customers");

    const pkgNameById = {};
    for (const p of srcPackages) pkgNameById[p.pkg_id] = p.pkg_name;

    return replaceMasterTables({
      packages: srcPackages.map((p) => ({ name: p.pkg_name, description: p.pkg_description, price_per_pax: p.pkg_price_per_pax, min_pax: p.pkg_min_pax })),
      menuItems: srcItems.map((m) => ({ name: m.mi_name, category: m.mi_category, price: m.mi_price, status: m.mi_status, description: m.mi_description })),
      packageItems: srcPkgItems.map((pi) => ({ package_name: pkgNameById[pi.pi_package_id], category: pi.pi_category, item_name: pi.pi_item_name, price: pi.pi_custom_price, quantity: pi.pi_quantity })),
      customers: srcCustomers.map((c) => ({ name: c.cus_name, contact: c.cus_contact, email: c.cus_email, address: c.cus_address })),
    });
  } finally {
    srcDb.close();
  }
}
