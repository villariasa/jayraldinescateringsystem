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
    pi_quantity INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bookings (
    bk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bk_booking_ref TEXT NOT NULL UNIQUE,
    bk_customer_id INTEGER REFERENCES customers(cus_id),
    bk_customer_name TEXT NOT NULL,
    bk_address TEXT,
    bk_event_date DATE NOT NULL,
    bk_event_time TIME DEFAULT '18:00',
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

CREATE TABLE IF NOT EXISTS entity_images (
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    image_data TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (entity_type, entity_id)
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

const DEFAULT_PACKAGES = [
  ["Budget Fiesta Package", "Affordable complete catering package perfect for intimate birthdays and family gatherings.", 350.0, 30],
  ["Standard Celebration Package", "Most popular catering option for debuts, baptismals, anniversaries, and reunions.", 550.0, 50],
  ["Grand Fiesta Package", "Grand banquet package featuring Lechon de Cebu, full buffet setup, and table skirts.", 850.0, 80],
  ["VIP Executive Package", "Top-tier luxury experience for corporate galas and high-end weddings with waiter service.", 1200.0, 100],
];

const DEFAULT_MENU_ITEMS = [
  ["Lechon de Cebu (Whole Roast Pig)", "Main Course", 8500.0, "Available", "Crispy skin, roasted with lemongrass, garlic, and native herbs."],
  ["Beef Caldereta Special", "Main Course", 280.0, "Available", "Tender beef chunks stewed in rich tomato liver sauce with bell peppers."],
  ["Pork Humba Bisaya", "Main Course", 240.0, "Available", "Slow-cooked pork belly in soy-vinegar sauce with banana blossoms."],
  ["Chicken Inasal Bacolod", "Main Course", 210.0, "Available", "Grilled marinated chicken quarters brushed with annatto oil."],
  ["Kare-Kare with Homemade Bagoong", "Main Course", 260.0, "Available", "Rich peanut stew with ox tripe, vegetables, and savory shrimp paste."],
  ["Fish Fillet in Tartar Sauce", "Main Course", 220.0, "Available", "Crispy golden dory fillets served with creamy homemade tartar sauce."],
  ["Sweet & Sour Pork Ribs", "Main Course", 250.0, "Available", "Crispy pork ribs tossed in vibrant sweet and sour pineapple glaze."],
  ["Garlic Butter Shrimp", "Main Course", 320.0, "Available", "Fresh tiger prawns sauteed in rich garlic butter and herbs."],
  ["Beef Broccoli in Oyster Sauce", "Main Course", 270.0, "Available", "Tender sliced beef sirloin sauteed with fresh broccoli florets."],
  ["Pancit Canton Special", "Noodles", 160.0, "Available", "Stir-fried egg noodles with pork, chicken liver, and mixed vegetables."],
  ["Pancit Palabok Supreme", "Noodles", 180.0, "Available", "Rice noodles topped with shrimp sauce, crushed chicharon, and boiled eggs."],
  ["Creamy Carbonara with Bacon", "Noodles", 190.0, "Available", "Fettuccine in rich cream sauce topped with crispy bacon bits."],
  ["Baked Macaroni Cheese Delight", "Noodles", 200.0, "Available", "Elbow macaroni baked in rich meat sauce and topped with melted cheese."],
  ["Sinigang na Baboy sa Sampalok", "Soup", 180.0, "Available", "Pork ribs in sour tamarind broth with kangkong, radish, and taro."],
  ["Classic Chicken Tinola sa Gabi", "Soup", 150.0, "Available", "Native chicken in ginger papaya soup with chili leaves."],
  ["Cream of Mushroom Soup", "Soup", 130.0, "Available", "Velvety mushroom soup served with garlic croutons."],
  ["Special Pinakbet sa Bagoong", "Vegetables", 140.0, "Available", "Sauteed squash, eggplant, okra, and ampalaya with crispy pork bagnet."],
  ["Chopsuey Special with Seafood", "Vegetables", 160.0, "Available", "Crispy stir-fried vegetables with shrimp, squid balls, and quail eggs."],
  ["Biko sa Latik", "Dessert", 90.0, "Available", "Sticky sweet rice cake topped with caramelized coconut cream latik."],
  ["Buko Pandan Salad", "Dessert", 110.0, "Available", "Young coconut strips and pandan jelly cubes in sweetened cream."],
  ["Leche Flan Supreme", "Dessert", 120.0, "Available", "Rich and silky caramel custard cooked with fresh egg yolks."],
  ["Mango Float Deluxe", "Dessert", 130.0, "Available", "Chilled Graham crackers layered with fresh Cebu mangoes and cream."],
  ["Unli Steamed Jasmine Rice", "Other", 50.0, "Available", "Fragrant steamed white Jasmine rice."],
  ["Signature Iced Tea (Per Gallon)", "Drinks", 150.0, "Available", "House-blend citrus iced tea served chilled."]
];

const DEFAULT_CUSTOMERS = [
  ["Alexander Wright", "09170001111", "alexander@example.com", "Cebu Business Park", "Silver", 1, 50000.0, "Active"],
  ["Beatriz Mendoza", "09180002222", "beatriz@example.com", "Mandaue City", "Bronze", 1, 35000.0, "Active"],
  ["Capt. Juanito Dela Cruz", "09182223344", "juanito.dc@example.com", "Mandaue City", "Bronze", 1, 28000.0, "Active"],
  ["Carlos De Guzman", "09190003333", "carlos@example.com", "Talisay City", "Bronze", 1, 20000.0, "Active"],
  ["Engr. Rodrigo Tan", "09178889900", "rodrigo.tan@example.com", "Cebu City", "Bronze", 1, 45000.0, "Active"],
  ["Larry", "09234234032", "4234@gmail.com", "street, Apas, Cebu City, Cebu", "Bronze", 1, 27000.0, "Active"]
];

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

  // Clear legacy placeholder tables if present
  try {
    const legacyPkg = db.exec("SELECT COUNT(*) FROM packages WHERE pkg_name LIKE '%Silver Buffet%'")[0]?.values[0][0];
    if (legacyPkg > 0) {
      db.run("DELETE FROM package_items");
      db.run("DELETE FROM packages");
      db.run("DELETE FROM menu_items");
      db.run("DELETE FROM customers WHERE cus_name LIKE '%Ichigo%' OR cus_name LIKE '%Angela Reyes%'");
    }
  } catch (_) {}

  if (countOf("packages") === 0) {
    for (const [name, desc, price, minPax] of DEFAULT_PACKAGES) {
      db.run("INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax) VALUES (?, ?, ?, ?)", [name, desc, price, minPax]);
    }
  }

  if (countOf("menu_items") === 0) {
    for (const [name, category, price, status, desc] of DEFAULT_MENU_ITEMS) {
      db.run("INSERT INTO menu_items (mi_name, mi_category, mi_price, mi_status, mi_description) VALUES (?, ?, ?, ?, ?)", [name, category, price, status, desc]);
    }
  }

  if (countOf("customers") === 0) {
    for (const [name, contact, email, address, tier, events, spent, status] of DEFAULT_CUSTOMERS) {
      db.run("INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_loyalty_tier, cus_total_events, cus_total_spent, cus_status, sync_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'synced')",
        [name, contact, email, address, tier, events, spent, status]);
    }
  }
}

export async function initDb() {
  if (db) return db;
  SQL = await window.initSqlJs({ locateFile: (f) => `vendor/${f}` });
  const existing = await idbLoad();
  db = existing ? new SQL.Database(new Uint8Array(existing)) : new SQL.Database();
  db.run(SCHEMA_SQL);
  try { db.run("ALTER TABLE bookings ADD COLUMN sync_status TEXT DEFAULT 'pending';"); } catch (_) {}
  try { db.run("ALTER TABLE customers ADD COLUMN sync_status TEXT DEFAULT 'pending';"); } catch (_) {}
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
export function replaceMasterTablesWithDbIds({ packages = [], menuItems = [], packageItems = [], customers = [] }) {
  const stats = { packages: 0, menu_items: 0, package_items: 0, customers: 0 };
  db.run("PRAGMA foreign_keys = OFF;");
  try {
    if (packages && packages.length > 0) {
      db.run("DELETE FROM package_items");
      db.run("DELETE FROM packages");
      for (const p of packages) {
        const name = (p.pkg_name || p.name || "").trim();
        if (!name) continue;
        const id = p.pkg_id || p.id;
        const desc = p.pkg_description || p.description || "";
        const price = Number(p.pkg_price_per_pax ?? p.price_per_pax) || 0;
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
        db.run("INSERT INTO package_items (pi_package_id, pi_menu_item_id, pi_item_name, pi_category, pi_custom_price, pi_quantity) VALUES (?, ?, ?, ?, ?, ?)",
          [pkgId, pi.pi_menu_item_id || null, itmName, pi.pi_category || "", Number(pi.pi_custom_price || 0), Number(pi.pi_quantity || 1)]);
        stats.package_items++;
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
