// Business logic — ported 1:1 from the original Tablet app's
// utils/repository.py, operating on the in-browser SQLite database
// (sqlite.js) instead of a server-side one.
import { fetchAll, fetchOne, run, computeInvoiceStatus, getDb } from "./sqlite.js";

const BOOKING_REF_PREFIX = "TB";

// ── Customers ────────────────────────────────────────────────────────

export function searchCustomers(query) {
  query = (query || "").trim();
  let rows;
  if (!query) {
    rows = fetchAll(`
      SELECT cus_id, cus_name, cus_contact, cus_email, cus_address
      FROM customers GROUP BY LOWER(cus_name), cus_contact ORDER BY cus_name LIMIT 100
    `);
  } else {
    const like = `%${query}%`;
    rows = fetchAll(`
      SELECT cus_id, cus_name, cus_contact, cus_email, cus_address
      FROM customers WHERE cus_name LIKE ? OR cus_contact LIKE ?
      GROUP BY LOWER(cus_name), cus_contact ORDER BY cus_name LIMIT 100
    `, [like, like]);
  }
  return rows.map((r) => ({ id: r.cus_id, name: r.cus_name, contact: r.cus_contact || "", email: r.cus_email || "", address: r.cus_address || "" }));
}

export function findPossibleDuplicateCustomer(contact, name) {
  contact = (contact || "").trim();
  if (contact) {
    const row = fetchOne("SELECT * FROM customers WHERE cus_contact = ? AND cus_contact != '' LIMIT 1", [contact]);
    if (row) return { id: row.cus_id, name: row.cus_name, contact: row.cus_contact || "" };
  }
  name = (name || "").trim();
  if (name) {
    const row = fetchOne("SELECT * FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", [name]);
    if (row) return { id: row.cus_id, name: row.cus_name, contact: row.cus_contact || "" };
  }
  return null;
}

export function addCustomer(name, contact = "", email = "", address = "") {
  name = (name || "").trim();
  if (!name) throw new Error("Customer name is required.");
  const contactClean = (contact || "").trim();
  if (contactClean) {
    const existing = fetchOne("SELECT cus_id FROM customers WHERE cus_contact = ? AND cus_contact != '' LIMIT 1", [contactClean]);
    if (existing) return existing.cus_id;
  }
  const existingName = fetchOne("SELECT cus_id FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", [name]);
  if (existingName) return existingName.cus_id;
  return run("INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status) VALUES (?, ?, ?, ?, 'Active')",
    [name, contactClean, (email || "").trim(), (address || "").trim()]);
}

export function updateCustomer(customerId, name, contact = "", email = "", address = "") {
  name = (name || "").trim();
  if (!name || !customerId) return false;
  run("UPDATE customers SET cus_name=?, cus_contact=?, cus_email=?, cus_address=? WHERE cus_id=?",
    [name, (contact || "").trim(), (email || "").trim(), (address || "").trim(), customerId]);
  return true;
}

export function deleteCustomer(customerId) {
  if (!customerId) return false;
  run("DELETE FROM customers WHERE cus_id = ?", [customerId]);
  return true;
}

// ── Entity Images (Local Device Photos) ──────────────────────────────

export function saveEntityImage(entityType, entityId, imageData) {
  if (!entityType || !entityId) return false;
  if (!imageData) {
    run("DELETE FROM entity_images WHERE entity_type = ? AND entity_id = ?", [entityType, entityId]);
    return true;
  }
  run(`
    INSERT INTO entity_images (entity_type, entity_id, image_data, updated_at)
    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(entity_type, entity_id) DO UPDATE SET image_data = excluded.image_data, updated_at = CURRENT_TIMESTAMP
  `, [entityType, entityId, imageData]);
  return true;
}

export function getEntityImage(entityType, entityId) {
  const row = fetchOne("SELECT image_data FROM entity_images WHERE entity_type = ? AND entity_id = ?", [entityType, entityId]);
  return row ? row.image_data : null;
}

// ── Master data: packages / menu ────────────────────────────────────

export function getPackages() {
  const rows = fetchAll(`
    SELECT p.*, ei.image_data AS image
    FROM packages p
    LEFT JOIN entity_images ei ON ei.entity_type = 'package' AND ei.entity_id = p.pkg_id
    ORDER BY p.pkg_price_per_pax ASC
  `);
  return rows.map((r) => ({
    id: r.pkg_id, name: r.pkg_name, description: r.pkg_description || "",
    price_per_pax: Number(r.pkg_price_per_pax), min_pax: Number(r.pkg_min_pax || 30),
    image: r.image || null,
  }));
}

export function addPackage(name, description = "", pricePerPax = 350.0, minPax = 30, imageData = null) {
  name = (name || "").trim();
  if (!name) throw new Error("Package name is required.");
  const pkgId = run("INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax) VALUES (?, ?, ?, ?)",
    [name, (description || "").trim(), Number(pricePerPax) || 0, Number(minPax) || 30]);
  if (imageData) saveEntityImage("package", pkgId, imageData);
  return pkgId;
}

export function updatePackage(pkgId, name, description = "", pricePerPax = 350.0, minPax = 30, imageData = undefined) {
  name = (name || "").trim();
  if (!name || !pkgId) return false;
  run("UPDATE packages SET pkg_name=?, pkg_description=?, pkg_price_per_pax=?, pkg_min_pax=? WHERE pkg_id=?",
    [name, (description || "").trim(), Number(pricePerPax) || 0, Number(minPax) || 30, pkgId]);
  if (imageData !== undefined) saveEntityImage("package", pkgId, imageData);
  return true;
}

export function deletePackage(pkgId) {
  if (!pkgId) return false;
  run("DELETE FROM entity_images WHERE entity_type = 'package' AND entity_id = ?", [pkgId]);
  run("DELETE FROM package_items WHERE pi_package_id = ?", [pkgId]);
  run("DELETE FROM packages WHERE pkg_id = ?", [pkgId]);
  return true;
}

export function getAllMenuItems() {
  const rows = fetchAll(`
    SELECT mi.*, ei.image_data AS image
    FROM menu_items mi
    LEFT JOIN entity_images ei ON ei.entity_type = 'menu_item' AND ei.entity_id = mi.mi_id
    ORDER BY mi.mi_category, mi.mi_name
  `);
  return rows.map((r) => ({
    id: r.mi_id, name: r.mi_name, category: r.mi_category || "Other",
    price: Number(r.mi_price || 0), status: r.mi_status || "Available", description: r.mi_description || "",
    image: r.image || null,
  }));
}

export function addMenuItem(name, category = "Main Dish", price = 0.0, status = "Available", description = "", imageData = null) {
  name = (name || "").trim();
  if (!name) throw new Error("Item name is required.");
  const miId = run("INSERT INTO menu_items (mi_name, mi_category, mi_price, mi_status, mi_description) VALUES (?, ?, ?, ?, ?)",
    [name, (category || "Other").trim(), Number(price) || 0, status, (description || "").trim()]);
  if (imageData) saveEntityImage("menu_item", miId, imageData);
  return miId;
}

export function updateMenuItem(miId, name, category = "Main Dish", price = 0.0, status = "Available", description = "", imageData = undefined) {
  name = (name || "").trim();
  if (!name || !miId) return false;
  run("UPDATE menu_items SET mi_name=?, mi_category=?, mi_price=?, mi_status=?, mi_description=? WHERE mi_id=?",
    [name, (category || "Other").trim(), Number(price) || 0, status, (description || "").trim(), miId]);
  if (imageData !== undefined) saveEntityImage("menu_item", miId, imageData);
  return true;
}

export function deleteMenuItem(miId) {
  if (!miId) return false;
  run("DELETE FROM entity_images WHERE entity_type = 'menu_item' AND entity_id = ?", [miId]);
  run("DELETE FROM menu_items WHERE mi_id = ?", [miId]);
  return true;
}

export function getMenuCategories() {
  const rows = fetchAll("SELECT DISTINCT mi_category FROM menu_items WHERE mi_category IS NOT NULL AND mi_category != '' ORDER BY mi_category");
  const cats = rows.map((r) => r.mi_category);
  const defaults = ["Beef", "Pork", "Chicken", "Fish & Seafood", "Pasta & Noodles", "Vegetables", "Dessert", "Beverage", "Add-on"];
  for (const d of defaults) if (!cats.includes(d)) cats.push(d);
  return cats;
}

export function getPackageMenuChoices() {
  const grouped = {};
  const rows = fetchAll(`
    SELECT mi.*, ei.image_data AS image
    FROM menu_items mi
    LEFT JOIN entity_images ei ON ei.entity_type = 'menu_item' AND ei.entity_id = mi.mi_id
    WHERE mi.mi_status = 'Available'
    ORDER BY mi.mi_category, mi.mi_name
  `);
  for (const r of rows) {
    const cat = r.mi_category || "Main Dish";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push({
      menu_item_id: r.mi_id,
      name: r.mi_name,
      category: cat,
      price: Number(r.mi_price || 0),
      description: r.mi_description || "",
      image: r.image || null,
    });
  }
  return grouped;
}

// ── Order creation (single-shot, atomic write at Confirm) ───────────

function genBookingRef() {
  const row = fetchOne("SELECT COUNT(*) AS c FROM bookings");
  const n = (row ? row.c : 0) + 1;
  return `${BOOKING_REF_PREFIX}-${String(n).padStart(5, "0")}-${Math.floor(Date.now() / 1000) % 100000}`;
}

export function createOrder(order) {
  let customerId = order.customer_id;
  if (!customerId) {
    customerId = addCustomer(order.customer_name, order.contact || "", order.email || "", order.address || "");
  }

  const bookingRef = genBookingRef();
  const baseTotal = Number(order.base_total) || 0;
  const chargesSum = (order.additional_charges || []).reduce((s, c) => s + Number(c.amount), 0);
  const total = baseTotal + chargesSum;
  const downPayment = Number(order.down_payment) || 0;
  const today = new Date().toISOString().slice(0, 10);

  const bookingId = run(`
    INSERT INTO bookings (
      bk_booking_ref, bk_customer_id, bk_customer_name, bk_address, bk_event_date, bk_event_time,
      bk_venue, bk_occasion, bk_pax, bk_total_amount, bk_base_total, bk_payment_mode,
      bk_amount_paid, bk_down_payment, bk_menu_type, bk_package_id, bk_notes, bk_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'package', ?, ?, 'PENDING')
  `, [
    bookingRef, customerId, order.customer_name, order.address || "", order.event_date,
    order.event_time || "18:00", order.venue || "", order.occasion || "", Number(order.pax) || 1,
    total, baseTotal, order.payment_method || "Cash", downPayment, downPayment,
    order.package_id ?? null, order.notes || "",
  ]);

  for (const m of order.menu_selections || []) {
    run(`INSERT INTO booking_menu_items (bmi_booking_id, bmi_item_id, bmi_item_name, bmi_category, bmi_price, bmi_quantity) VALUES (?, ?, ?, ?, ?, ?)`,
      [bookingId, m.menu_item_id ?? null, m.item_name, m.category || "", Number(m.price) || 0, Number(m.quantity) || 1]);
  }

  for (const c of order.additional_charges || []) {
    run(`INSERT INTO booking_additional_charges (ac_booking_id, ac_description, ac_amount, ac_date_added, ac_added_by) VALUES (?, ?, ?, ?, ?)`,
      [bookingId, c.description, Number(c.amount), today, order.actor || "Kiosk PWA"]);
  }

  const status = computeInvoiceStatus(total, downPayment);
  const balance = Math.max(0, total - downPayment);
  const invNum = `INV-${bookingRef}`;
  const invoiceId = run(`
    INSERT INTO invoices (inv_booking_id, inv_invoice_ref, inv_invoice_number, inv_customer_name,
      inv_event_date, inv_total_amount, inv_amount_paid, inv_balance, inv_down_payment, inv_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `, [bookingId, invNum, invNum, order.customer_name, order.event_date, total, downPayment, balance, downPayment, status]);

  if (downPayment > 0) {
    run(`INSERT INTO payment_records (pr_invoice_id, pr_amount, pr_payment_date, pr_payment_method, pr_notes, pr_is_downpayment) VALUES (?, ?, ?, ?, ?, 1)`,
      [invoiceId, downPayment, today, order.payment_method || "Cash", "Down payment recorded via kiosk PWA"]);
  }

  if (order.terms_version) {
    recordTermsAcknowledgement(bookingId, order.terms_version, order.customer_name);
  }

  return { booking_id: bookingId, booking_ref: bookingRef, invoice_id: invoiceId, total, paid: downPayment, balance, status };
}

export function recordTermsAcknowledgement(bookingId, version, customerName) {
  run(`INSERT INTO terms_acknowledgements (ta_booking_id, ta_version, ta_acknowledged, ta_acknowledged_at, ta_customer_name) VALUES (?, ?, 1, ?, ?)`,
    [bookingId, version, new Date().toISOString(), customerName]);
}

export function getOrderDetail(bookingId) {
  const b = fetchOne("SELECT * FROM bookings WHERE bk_id = ?", [bookingId]);
  if (!b) return null;
  const inv = fetchOne("SELECT * FROM invoices WHERE inv_booking_id = ? LIMIT 1", [bookingId]);
  const menuItems = fetchAll("SELECT * FROM booking_menu_items WHERE bmi_booking_id = ?", [bookingId]);
  const charges = fetchAll("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", [bookingId]);
  const payments = inv ? fetchAll("SELECT * FROM payment_records WHERE pr_invoice_id = ?", [inv.inv_id]) : [];
  const terms = fetchOne("SELECT * FROM terms_acknowledgements WHERE ta_booking_id = ? ORDER BY ta_id DESC LIMIT 1", [bookingId]);

  // Lookup customer details (phone, email, full address)
  let cust = null;
  if (b.bk_customer_id) {
    cust = fetchOne("SELECT * FROM customers WHERE cus_id = ?", [b.bk_customer_id]);
  }
  if (!cust && b.bk_customer_name) {
    cust = fetchOne("SELECT * FROM customers WHERE LOWER(cus_name) = LOWER(?) LIMIT 1", [b.bk_customer_name]);
  }

  // Lookup package name
  let pkg = null;
  if (b.bk_package_id) {
    pkg = fetchOne("SELECT * FROM packages WHERE pkg_id = ?", [b.bk_package_id]);
  }

  const baseTotal = Number(b.bk_base_total || 0);
  const addonsTotal = charges.reduce((sum, c) => sum + Number(c.ac_amount || 0), 0);
  const grandTotal = Number(b.bk_total_amount || (baseTotal + addonsTotal));
  const paid = inv ? Number(inv.inv_amount_paid) : Number(b.bk_amount_paid || 0);
  const balance = inv ? Number(inv.inv_balance) : Math.max(0, grandTotal - paid);

  return {
    booking_id: b.bk_id,
    booking_ref: b.bk_booking_ref,
    customer: b.bk_customer_name || (cust ? cust.cus_name : "Walk-in Guest"),
    customer_name: b.bk_customer_name || (cust ? cust.cus_name : "Walk-in Guest"),
    customer_id: b.bk_customer_id || (cust ? cust.cus_id : null),
    contact: (cust ? cust.cus_contact : "") || "",
    email: (cust ? cust.cus_email : "") || "",
    customer_address: (cust ? cust.cus_address : "") || b.bk_address || "",
    address: b.bk_address || (cust ? cust.cus_address : ""),
    event_date: b.bk_event_date,
    event_time: b.bk_event_time || "18:00",
    venue: b.bk_venue || "Catering Venue",
    occasion: b.bk_occasion || "Special Event",
    pax: b.bk_pax || 1,
    package_id: b.bk_package_id,
    package_name: pkg ? pkg.pkg_name : (b.bk_menu_type || "Catering Package"),
    package_subtotal: baseTotal || grandTotal,
    base_total: baseTotal,
    addons_subtotal: addonsTotal,
    total: grandTotal,
    downpayment: Number(b.bk_down_payment || paid),
    paid: paid,
    balance: balance,
    status: inv ? inv.inv_status : (b.bk_status || "Confirmed"),
    menu_selections: menuItems.map((m) => ({
      item_name: m.bmi_item_name,
      category: m.bmi_category,
      price: Number(m.bmi_price || 0),
      quantity: m.bmi_quantity || 1
    })),
    additional_charges: charges.map((c) => ({
      description: c.ac_description,
      amount: Number(c.ac_amount)
    })),
    payments: payments.map((p) => ({
      amount: Number(p.pr_amount),
      date: p.pr_payment_date,
      method: p.pr_payment_method
    })),
    terms_version: terms ? terms.ta_version : null,
    terms_acknowledged_at: terms ? terms.ta_acknowledged_at : null,
    notes: b.bk_notes || "",
    payment_method: b.bk_payment_mode || "Cash",
  };
}

export function getAllOrders(limit = 200) {
  const rows = fetchAll(`
    SELECT b.bk_id, b.bk_booking_ref, b.bk_customer_name, b.bk_event_date, b.bk_total_amount, b.bk_status, b.bk_created_at,
           i.inv_status, i.inv_amount_paid, i.inv_balance
    FROM bookings b LEFT JOIN invoices i ON i.inv_booking_id = b.bk_id
    ORDER BY b.bk_created_at DESC LIMIT ?
  `, [limit]);
  return rows.map((r) => ({
    booking_id: r.bk_id, booking_ref: r.bk_booking_ref, customer: r.bk_customer_name,
    event_date: r.bk_event_date, created_at: r.bk_created_at,
    total: Number(r.bk_total_amount || 0), paid: Number(r.inv_amount_paid || 0),
    balance: Number(r.inv_balance || 0), status: r.inv_status || "Unpaid",
  }));
}

export function clearAllOrders() {
  const row = fetchOne("SELECT COUNT(*) AS c FROM bookings");
  const count = row ? row.c : 0;
  const db = getDb();
  db.run("PRAGMA foreign_keys = OFF;");
  try {
    db.run("DELETE FROM payment_records");
    db.run("DELETE FROM invoices");
    db.run("DELETE FROM booking_additional_charges");
    db.run("DELETE FROM booking_menu_items");
    db.run("DELETE FROM terms_acknowledgements");
    db.run("DELETE FROM bookings");
  } finally {
    db.run("PRAGMA foreign_keys = ON;");
  }
  return count;
}

// ── Built-in address system (Cebu) ──────────────────────────────────

let cebuAddressCache = null;

export function getAllCebuAddresses() {
  if (cebuAddressCache) return cebuAddressCache;
  cebuAddressCache = fetchAll(`
    SELECT b.ab_id AS barangay_id, b.ab_name AS barangay,
           c.ac_id AS city_id, c.ac_name AS city,
           pr.ap_id AS province_id, pr.ap_name AS province,
           (b.ab_name || ', ' || c.ac_name || ', ' || pr.ap_name) AS display_text
    FROM address_barangays b
    JOIN address_cities c ON c.ac_id = b.ab_city_id
    JOIN address_provinces pr ON pr.ap_id = c.ac_province_id
    ORDER BY c.ac_name, b.ab_name
  `);
  return cebuAddressCache;
}

export function searchCebuAddress(query, limit = 15) {
  if (!query || query.trim().length < 1) return [];
  const all = getAllCebuAddresses();
  const tokens = query.trim().toLowerCase().replace(/,/g, " ").split(/\s+/).filter(Boolean);
  const results = [];
  for (const addr of all) {
    const text = addr.display_text.toLowerCase();
    if (tokens.every((t) => text.includes(t))) {
      results.push(addr);
      if (results.length >= limit) break;
    }
  }
  return results;
}
