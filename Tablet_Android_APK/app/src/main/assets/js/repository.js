// Business logic — ported 1:1 from the original Tablet app's
// utils/repository.py, operating on the in-browser SQLite database
// (sqlite.js) instead of a server-side one.
import { fetchAll, fetchOne, run, computeInvoiceStatus, getDb, replaceMasterTablesWithDbIds } from "./sqlite.js";

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

export function formatEventTime(timeStr) {
  if (!timeStr) return "To be followed";
  const str = String(timeStr).trim();
  if (str.toLowerCase().includes("to be follow") || str.toUpperCase() === "TBF" || str.toUpperCase() === "TBA") {
    return "To be followed";
  }
  if (str.includes("AM") || str.includes("PM") || str.includes("am") || str.includes("pm")) {
    return str;
  }
  const parts = str.split(":");
  if (parts.length >= 2) {
    let hours = parseInt(parts[0], 10);
    const minutes = parts[1].padStart(2, "0").slice(0, 2);
    if (isNaN(hours)) return str;
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    if (hours === 0) hours = 12;
    return `${hours}:${minutes} ${ampm}`;
  }
  return str;
}

export function addCustomer(name, contact = "", email = "", address = "") {
  name = (name || "").trim();
  if (!name) throw new Error("Customer name is required.");
  const contactClean = (contact || "").trim();
  const emailClean = (email || "").trim();
  const addrClean = (address || "").trim();

  // If contact was given, check by contact
  if (contactClean) {
    const existing = fetchOne("SELECT cus_id, cus_email, cus_address FROM customers WHERE cus_contact = ? AND cus_contact != '' LIMIT 1", [contactClean]);
    if (existing) {
      if (emailClean || addrClean) {
        run("UPDATE customers SET cus_email = COALESCE(NULLIF(?, ''), cus_email), cus_address = COALESCE(NULLIF(?, ''), cus_address) WHERE cus_id = ?",
          [emailClean, addrClean, existing.cus_id]);
      }
      return existing.cus_id;
    }
  }

  // Check by name
  const existingName = fetchOne("SELECT cus_id, cus_contact, cus_email, cus_address FROM customers WHERE LOWER(TRIM(cus_name)) = LOWER(TRIM(?)) LIMIT 1", [name]);
  if (existingName) {
    if (contactClean || emailClean || addrClean) {
      run("UPDATE customers SET cus_contact = COALESCE(NULLIF(?, ''), cus_contact), cus_email = COALESCE(NULLIF(?, ''), cus_email), cus_address = COALESCE(NULLIF(?, ''), cus_address) WHERE cus_id = ?",
        [contactClean, emailClean, addrClean, existingName.cus_id]);
    }
    return existingName.cus_id;
  }

  return run("INSERT INTO customers (cus_name, cus_contact, cus_email, cus_address, cus_status, sync_status) VALUES (?, ?, ?, ?, 'Active', 'pending')",
    [name, contactClean, emailClean, addrClean]);
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

export function queuePackageImageUpload(pkgId, imageData = "", removeImage = false) {
  if (!pkgId) return false;
  const img = removeImage ? "" : (imageData || "");
  run(`
    INSERT INTO pending_package_images (pkg_id, image_data, remove_image, sync_status, last_error, updated_at)
    VALUES (?, ?, ?, 'pending', '', CURRENT_TIMESTAMP)
    ON CONFLICT(pkg_id) DO UPDATE SET
      image_data = excluded.image_data,
      remove_image = excluded.remove_image,
      sync_status = 'pending',
      last_error = '',
      updated_at = CURRENT_TIMESTAMP
  `, [pkgId, img, removeImage ? 1 : 0]);
  run("UPDATE packages SET pkg_image = ?, image = ? WHERE pkg_id = ?", [img, img, pkgId]);
  saveEntityImage("package", pkgId, img);
  return true;
}

export function getPendingPackageImageUploads() {
  try {
    return fetchAll(`
      SELECT pkg_id, image_data, remove_image, sync_status, last_error, updated_at
      FROM pending_package_images
      WHERE sync_status = 'pending' OR sync_status = 'failed' OR sync_status IS NULL
      ORDER BY updated_at ASC
    `);
  } catch (_) {
    return [];
  }
}

function getPendingPackageImageMap() {
  const map = new Map();
  for (const row of getPendingPackageImageUploads()) {
    map.set(Number(row.pkg_id), row);
  }
  return map;
}

export function markPackageImageSynced(pkgId, serverPath = "", serverImage = "") {
  if (!pkgId) return false;
  run("DELETE FROM pending_package_images WHERE pkg_id = ?", [pkgId]);
  const img = serverImage || serverPath || "";
  run("UPDATE packages SET pkg_image = ?, image = ? WHERE pkg_id = ?", [serverPath || img, img, pkgId]);
  saveEntityImage("package", pkgId, img);
  return true;
}

export function markPackageImageUploadFailed(pkgId, error = "") {
  if (!pkgId) return false;
  run(`
    UPDATE pending_package_images
    SET sync_status = 'failed', last_error = ?, updated_at = CURRENT_TIMESTAMP
    WHERE pkg_id = ?
  `, [String(error || "Upload failed.").slice(0, 500), pkgId]);
  return true;
}

export function queueMenuItemImageUpload(miId, imageData = "", removeImage = false, itemName = "") {
  if (!miId) return false;
  const img = removeImage ? "" : (imageData || "");
  run(`
    INSERT INTO pending_menu_images (mi_id, item_name, image_data, remove_image, sync_status, last_error, updated_at)
    VALUES (?, ?, ?, ?, 'pending', '', CURRENT_TIMESTAMP)
    ON CONFLICT(mi_id) DO UPDATE SET
      item_name = excluded.item_name,
      image_data = excluded.image_data,
      remove_image = excluded.remove_image,
      sync_status = 'pending',
      last_error = '',
      updated_at = CURRENT_TIMESTAMP
  `, [miId, itemName || "", img, removeImage ? 1 : 0]);
  run("UPDATE menu_items SET mi_image = ?, image = ? WHERE mi_id = ?", [img, img, miId]);
  saveEntityImage("menu_item", miId, img);
  return true;
}

export function getPendingMenuItemImageUploads() {
  try {
    return fetchAll(`
      SELECT mi_id, item_name, image_data, remove_image, sync_status, last_error, updated_at
      FROM pending_menu_images
      WHERE sync_status = 'pending' OR sync_status = 'failed' OR sync_status IS NULL
      ORDER BY updated_at ASC
    `);
  } catch (_) {
    return [];
  }
}

function getPendingMenuItemImageMap() {
  const map = new Map();
  for (const row of getPendingMenuItemImageUploads()) {
    map.set(Number(row.mi_id), row);
  }
  return map;
}

export function markMenuItemImageSynced(miId, serverPath = "", serverImage = "") {
  if (!miId) return false;
  run("DELETE FROM pending_menu_images WHERE mi_id = ?", [miId]);
  const img = serverImage || serverPath || "";
  run("UPDATE menu_items SET mi_image = ?, image = ? WHERE mi_id = ?", [serverPath || img, img, miId]);
  saveEntityImage("menu_item", miId, img);
  return true;
}

export function markMenuItemImageUploadFailed(miId, error = "") {
  if (!miId) return false;
  run(`
    UPDATE pending_menu_images
    SET sync_status = 'failed', last_error = ?, updated_at = CURRENT_TIMESTAMP
    WHERE mi_id = ?
  `, [String(error || "Upload failed.").slice(0, 500), miId]);
  return true;
}

// ── Master data: packages / menu ────────────────────────────────────

export function getPackages() {
  let rows = [];
  try {
    rows = fetchAll(`
      SELECT p.*, COALESCE(NULLIF(ei.image_data, ''), '') AS entity_image_data
      FROM packages p
      LEFT JOIN entity_images ei ON ei.entity_type = 'package' AND ei.entity_id = p.pkg_id
      ORDER BY p.pkg_price_per_pax ASC
    `);
  } catch (e) {
    try {
      rows = fetchAll("SELECT * FROM packages ORDER BY pkg_price_per_pax ASC");
    } catch (_) {
      rows = [];
    }
  }

  return rows.map((r) => ({
    id: r.pkg_id,
    name: r.pkg_name,
    description: r.pkg_description || "",
    price_per_pax: Number(r.pkg_price_per_pax),
    min_pax: Number(r.pkg_min_pax || 30),
    image: r.entity_image_data || r.image || r.pkg_image || null,
  }));
}

export function addPackage(name, description = "", pricePerPax = 350.0, minPax = 30, imageData = null) {
  name = (name || "").trim();
  if (!name) throw new Error("Package name is required.");
  const img = imageData || "";
  const pkgId = run("INSERT INTO packages (pkg_name, pkg_description, pkg_price_per_pax, pkg_min_pax, pkg_image, image) VALUES (?, ?, ?, ?, ?, ?)",
    [name, (description || "").trim(), Number(pricePerPax) || 0, Number(minPax) || 30, img, img]);
  if (imageData) saveEntityImage("package", pkgId, imageData);
  return pkgId;
}

export function updatePackage(pkgId, name, description = "", pricePerPax = 350.0, minPax = 30, imageData = undefined) {
  name = (name || "").trim();
  if (!name || !pkgId) return false;
  run("UPDATE packages SET pkg_name=?, pkg_description=?, pkg_price_per_pax=?, pkg_min_pax=? WHERE pkg_id=?",
    [name, (description || "").trim(), Number(pricePerPax) || 0, Number(minPax) || 30, pkgId]);
  if (imageData !== undefined) {
    const img = imageData || "";
    run("UPDATE packages SET pkg_image = ?, image = ? WHERE pkg_id = ?", [img, img, pkgId]);
    saveEntityImage("package", pkgId, img);
  }
  return true;
}

export function deletePackage(pkgId) {
  if (!pkgId) return false;
  run("DELETE FROM entity_images WHERE entity_type = 'package' AND entity_id = ?", [pkgId]);
  run("DELETE FROM package_items WHERE pi_package_id = ?", [pkgId]);
  run("DELETE FROM packages WHERE pkg_id = ?", [pkgId]);
  return true;
}

export function getPackageItems(pkgId) {
  try {
    const rows = fetchAll(`
      SELECT pi.*, mi.mi_name, mi.mi_category, mi.mi_price
      FROM package_items pi
      LEFT JOIN menu_items mi ON mi.mi_id = pi.pi_menu_item_id
      WHERE pi.pi_package_id = ?
    `, [pkgId]);
    return rows.map((r) => ({
      id: r.pi_id,
      package_id: r.pi_package_id,
      menu_item_id: r.pi_menu_item_id,
      name: r.pi_item_name || r.mi_name || "Dish",
      item_name: r.pi_item_name || r.mi_name || "Dish",
      category: r.pi_category || r.mi_category || "Main Course",
      price: Number(r.pi_custom_price || r.mi_price || 0),
    }));
  } catch (e) {
    try {
      const rows = fetchAll("SELECT * FROM package_items WHERE pi_package_id = ?", [pkgId]);
      return rows.map((r) => ({
        id: r.pi_id,
        package_id: r.pi_package_id,
        menu_item_id: r.pi_menu_item_id,
        name: r.pi_item_name || "Dish",
        item_name: r.pi_item_name || "Dish",
        category: r.pi_category || "Main Course",
        price: Number(r.pi_custom_price || 0),
      }));
    } catch (_) {
      return [];
    }
  }
}

export function getPackageBuckets(pkgId) {
  if (!pkgId) return [];
  try {
    const rows = fetchAll(
      "SELECT pb_id, pb_name, pb_limit, pb_categories, pb_sort FROM package_buckets WHERE pb_package_id = ? ORDER BY pb_sort, pb_id",
      [pkgId]
    );
    return rows.map((r) => {
      let cats = [];
      try {
        const raw = r.pb_categories;
        if (Array.isArray(raw)) cats = raw.map((c) => String(c));
        else if (typeof raw === "string" && raw.trim()) cats = JSON.parse(raw).map((c) => String(c));
      } catch (_) { cats = []; }
      return {
        id: r.pb_id,
        name: r.pb_name || "",
        limit: Number(r.pb_limit || 0),
        categories: cats,
        sort: Number(r.pb_sort || 0),
      };
    });
  } catch (_) {
    return [];
  }
}

export function getBookingsByDate(dateStr) {
  try {
    const rows = fetchAll(`
      SELECT bk_id, bk_booking_ref, bk_customer_name, bk_event_date, bk_event_time, bk_event_end_time,
             bk_venue, bk_occasion, bk_pax, bk_status
      FROM bookings
      WHERE bk_event_date = ? AND bk_status != 'CANCELLED'
      ORDER BY bk_event_time ASC
    `, [dateStr]);
    return rows.map((r) => ({
      id: r.bk_id,
      ref: r.bk_booking_ref,
      customer: r.bk_customer_name,
      date: r.bk_event_date,
      time: formatEventTime(r.bk_event_time),
      endTime: r.bk_event_end_time ? formatEventTime(r.bk_event_end_time) : "",
      venue: r.bk_venue || "To be followed",
      occasion: r.bk_occasion || "Event",
      pax: Number(r.bk_pax || 0),
      status: r.bk_status || "PENDING",
    }));
  } catch (_) {
    return [];
  }
}

export function getMonthBookings(year, month) {
  try {
    const mStr = String(month).padStart(2, "0");
    const prefix = `${year}-${mStr}-%`;
    const rows = fetchAll(`
      SELECT bk_id, bk_booking_ref, bk_customer_name, bk_event_date, bk_event_time, bk_event_end_time,
             bk_venue, bk_occasion, bk_pax, bk_status
      FROM bookings
      WHERE bk_event_date LIKE ? AND bk_status != 'CANCELLED'
      ORDER BY bk_event_date ASC, bk_event_time ASC
    `, [prefix]);
    return rows.map((r) => ({
      id: r.bk_id,
      ref: r.bk_booking_ref,
      customer: r.bk_customer_name,
      date: r.bk_event_date,
      time: formatEventTime(r.bk_event_time),
      endTime: r.bk_event_end_time ? formatEventTime(r.bk_event_end_time) : "",
      venue: r.bk_venue || "To be followed",
      occasion: r.bk_occasion || "Event",
      pax: Number(r.bk_pax || 0),
      status: r.bk_status || "PENDING",
    }));
  } catch (_) {
    return [];
  }
}

export function getAllMenuItems() {
  let rows = [];
  try {
    rows = fetchAll(`
      SELECT mi.*, COALESCE(NULLIF(ei.image_data, ''), '') AS entity_image_data
      FROM menu_items mi
      LEFT JOIN entity_images ei ON ei.entity_type = 'menu_item' AND ei.entity_id = mi.mi_id
      ORDER BY mi.mi_category, mi.mi_name
    `);
  } catch (e) {
    try {
      rows = fetchAll("SELECT * FROM menu_items ORDER BY mi_category, mi_name");
    } catch (_) {
      rows = [];
    }
  }

  return rows.map((r) => ({
    id: r.mi_id,
    name: r.mi_name,
    category: r.mi_category || "Other",
    price: Number(r.mi_price || 0),
    status: r.mi_status || "Available",
    description: r.mi_description || "",
    image: r.entity_image_data || r.image || r.mi_image || null,
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
  // Admin-defined display order (mc_sort, then mc_id as tiebreak) — this is
  // what the dashboard/ordering category bars and Settings > Menu
  // Categories reorder UI both read.
  const rows = fetchAll(
    "SELECT mc_name FROM menu_categories WHERE mc_is_active = 1 OR mc_is_active IS NULL "
    + "ORDER BY COALESCE(mc_sort, 0), mc_id"
  );
  const cats = rows.map((r) => r.mc_name);
  const known = new Set(cats.map((c) => c.toLowerCase()));

  // Any category only present on a menu item (e.g. imported data) but not
  // yet in menu_categories gets appended so it isn't silently hidden.
  const extra = fetchAll("SELECT DISTINCT mi_category FROM menu_items WHERE mi_category IS NOT NULL AND mi_category != ''");
  let nextSort = cats.length;
  for (const r of extra) {
    const cat = r.mi_category;
    if (cat && !known.has(cat.toLowerCase())) {
      cats.push(cat);
      known.add(cat.toLowerCase());
      try { run("INSERT OR IGNORE INTO menu_categories (mc_name, mc_sort) VALUES (?, ?)", [cat, nextSort++]); } catch (_) {}
    }
  }
  return cats;
}

export function reorderMenuCategories(orderedNames) {
  (orderedNames || []).forEach((name, i) => {
    name = (name || "").trim();
    if (!name) return;
    run("INSERT OR IGNORE INTO menu_categories (mc_name, mc_sort) VALUES (?, ?)", [name, i]);
    run("UPDATE menu_categories SET mc_sort = ? WHERE mc_name = ?", [i, name]);
  });
  return true;
}

export function getPackageMenuChoices() {
  const grouped = {};
  const rows = fetchAll(`
    SELECT mi.*, COALESCE(NULLIF(ei.image_data, ''), NULLIF(mi.image, ''), NULLIF(mi.mi_image, '')) AS image
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
      bk_booking_ref, bk_customer_id, bk_customer_name, bk_address, bk_event_date, bk_event_time, bk_event_end_time,
      bk_venue, bk_occasion, bk_pax, bk_total_amount, bk_base_total, bk_payment_mode,
      bk_amount_paid, bk_down_payment, bk_menu_type, bk_package_id, bk_notes, bk_color_theme, bk_status, sync_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'package', ?, ?, ?, 'PENDING', 'pending')
  `, [
    bookingRef, customerId, order.customer_name, order.address || "", order.event_date,
    order.event_time || "To be followed", order.event_end_time || null, order.venue || "To be followed", order.occasion || "General Event", Number(order.pax) || 1,
    total, baseTotal, order.payment_method || "Cash", downPayment, downPayment,
    order.package_id ?? null, order.notes || "", order.motif || order.color_theme || "Standard",
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
  const b = fetchOne("SELECT * FROM bookings WHERE bk_id = ? OR bk_booking_ref = ?", [bookingId, String(bookingId)]);
  if (!b) return null;
  const inv = fetchOne("SELECT * FROM invoices WHERE inv_booking_id = ? LIMIT 1", [b.bk_id]);
  const menuItems = fetchAll("SELECT * FROM booking_menu_items WHERE bmi_booking_id = ?", [b.bk_id]);
  const charges = fetchAll("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", [b.bk_id]);
  const payments = inv ? fetchAll("SELECT * FROM payment_records WHERE pr_invoice_id = ?", [inv.inv_id]) : [];
  const terms = fetchOne("SELECT * FROM terms_acknowledgements WHERE ta_booking_id = ? ORDER BY ta_id DESC LIMIT 1", [b.bk_id]);

  // Lookup customer details (phone, email, full address)
  let cust = null;
  if (b.bk_customer_id) {
    cust = fetchOne("SELECT * FROM customers WHERE cus_id = ?", [b.bk_customer_id]);
  }
  if (!cust && b.bk_customer_name) {
    cust = fetchOne("SELECT * FROM customers WHERE LOWER(TRIM(cus_name)) = LOWER(TRIM(?)) LIMIT 1", [b.bk_customer_name]);
  }

  // Lookup package name
  let pkg = null;
  if (b.bk_package_id) {
    pkg = fetchOne("SELECT * FROM packages WHERE pkg_id = ?", [b.bk_package_id]);
  }

  const baseTotal = Number(b.bk_base_total || 0);
  const addonsTotal = charges.reduce((sum, c) => sum + Number(c.ac_amount || 0), 0);
  const grandTotal = Number(b.bk_total_amount || (baseTotal + addonsTotal));

  // Compute actual paid and balance accurately
  const rawBalance = inv && inv.inv_balance != null ? Number(inv.inv_balance) : null;
  const paid = Math.max(
    Number(b.bk_amount_paid || 0),
    Number(b.bk_down_payment || 0),
    Number(inv ? inv.inv_amount_paid : 0),
    Number(inv ? inv.inv_down_payment : 0),
    rawBalance !== null ? Math.max(0, grandTotal - rawBalance) : 0
  );
  const balance = rawBalance !== null ? rawBalance : Math.max(0, grandTotal - paid);

  const customerName = b.bk_customer_name || (cust ? cust.cus_name : "") || "Walk-in Guest";
  const contact = (cust ? cust.cus_contact : "") || "";
  const email = (cust ? cust.cus_email : "") || "";
  const address = b.bk_address || (cust ? cust.cus_address : "") || "";

  return {
    booking_id: b.bk_id,
    booking_ref: b.bk_booking_ref,
    customer: customerName,
    customer_name: customerName,
    name: customerName,
    contact: contact,
    phone: contact,
    email: email,
    customer_address: address,
    address: address,
    event_date: b.bk_event_date,
    event_time: formatEventTime(b.bk_event_time),
    venue: b.bk_venue || "Catering Venue",
    occasion: b.bk_occasion || "Special Event",
    pax: Number(b.bk_pax || 1),
    package_id: b.bk_package_id,
    package_name: pkg ? pkg.pkg_name : (b.bk_menu_type || "Catering Package"),
    package_subtotal: baseTotal || (grandTotal - addonsTotal),
    base_total: baseTotal,
    addons_subtotal: addonsTotal,
    total: grandTotal,
    downpayment: paid,
    paid: paid,
    balance: balance,
    status: inv ? inv.inv_status : (b.bk_status || (balance === 0 ? "PAID" : paid > 0 ? "PARTIAL" : "PENDING")),
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
    motif: b.bk_color_theme || "Standard",
    color_theme: b.bk_color_theme || "Standard",
    bk_color_theme: b.bk_color_theme || "Standard",
  };
}

export function getAllOrders(limit = 200) {
  const rows = fetchAll(`
    SELECT b.bk_id, b.bk_booking_ref, b.bk_customer_name, b.bk_event_date, b.bk_event_time,
           b.bk_pax, b.bk_total_amount, b.bk_base_total, b.bk_amount_paid, b.bk_down_payment,
           b.bk_status, b.bk_created_at, b.bk_venue, b.bk_occasion, b.bk_payment_mode,
           p.pkg_name,
           c.cus_contact, c.cus_email, c.cus_address,
           i.inv_status, i.inv_amount_paid, i.inv_balance, i.inv_down_payment
    FROM bookings b
    LEFT JOIN customers c ON c.cus_id = b.bk_customer_id
    LEFT JOIN packages p ON p.pkg_id = b.bk_package_id
    LEFT JOIN invoices i ON i.inv_booking_id = b.bk_id
    ORDER BY b.bk_created_at DESC LIMIT ?
  `, [limit]);

  return rows.map((r) => {
    const total = Number(r.bk_total_amount || 0);
    const rawBalance = r.inv_balance != null ? Number(r.inv_balance) : null;
    const paid = Math.max(
      Number(r.bk_amount_paid || 0),
      Number(r.bk_down_payment || 0),
      Number(r.inv_amount_paid || 0),
      Number(r.inv_down_payment || 0),
      rawBalance !== null ? Math.max(0, total - rawBalance) : 0
    );
    const balance = rawBalance !== null ? rawBalance : Math.max(0, total - paid);

    return {
      booking_id: r.bk_id,
      booking_ref: r.bk_booking_ref,
      customer: r.bk_customer_name || "Walk-in Guest",
      customer_name: r.bk_customer_name || "Walk-in Guest",
      contact: r.cus_contact || "",
      email: r.cus_email || "",
      address: r.cus_address || r.bk_address || "",
      event_date: r.bk_event_date,
      event_time: formatEventTime(r.bk_event_time),
      pax: Number(r.bk_pax || 60),
      package_name: r.pkg_name || "Buffet Package",
      created_at: r.bk_created_at,
      total: total,
      paid: paid,
      downpayment: paid,
      balance: balance,
      status: r.inv_status || r.bk_status || (balance === 0 ? "PAID" : paid > 0 ? "PARTIAL" : "PENDING"),
    };
  });
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

// ── LAN Sync Data Helpers ───────────────────────────────────────────

export function getPendingSyncRecords() {
  let bookings = [];
  try {
    bookings = fetchAll("SELECT * FROM bookings WHERE sync_status = 'pending' OR sync_status IS NULL OR bk_id IN (SELECT DISTINCT ac_booking_id FROM booking_additional_charges)");
  } catch (_) {
    bookings = fetchAll("SELECT * FROM bookings");
  }

  const enrichedBookings = bookings.map((b) => {
    let items = [];
    let inv = null;
    let charges = [];
    try {
      items = fetchAll("SELECT * FROM booking_menu_items WHERE bmi_booking_id = ?", [b.bk_id]);
    } catch (_) {}
    try {
      inv = fetchOne("SELECT * FROM invoices WHERE inv_booking_id = ?", [b.bk_id]);
    } catch (_) {}
    try {
      charges = fetchAll("SELECT * FROM booking_additional_charges WHERE ac_booking_id = ?", [b.bk_id]);
    } catch (_) {}
    return {
      ...b,
      menu_items: items,
      invoice: inv,
      additional_charges: charges,
    };
  });

  let customers = [];
  try {
    customers = fetchAll("SELECT * FROM customers WHERE sync_status = 'pending' OR sync_status IS NULL");
  } catch (_) {
    customers = fetchAll("SELECT * FROM customers");
  }

  return { bookings: enrichedBookings, customers };
}

export function markRecordsSynced(bookingRefs = [], customerNames = []) {
  if (bookingRefs && bookingRefs.length > 0) {
    for (const ref of bookingRefs) {
      try {
        run("UPDATE bookings SET sync_status = 'synced' WHERE bk_booking_ref = ? OR bk_id = ?", [ref, ref]);
      } catch (_) {}
    }
  }
  if (customerNames && customerNames.length > 0) {
    for (const name of customerNames) {
      try {
        run("UPDATE customers SET sync_status = 'synced' WHERE cus_name = ? OR cus_id = ?", [name, name]);
      } catch (_) {}
    }
  }
}

export function updateMasterDataFromSync(packages = [], menuItems = [], packageItems = [], customers = [], occasions = [], packageBuckets = [], menuCategories = []) {
  const pendingPackageImages = getPendingPackageImageMap();
  const pendingMenuItemImages = getPendingMenuItemImageMap();

  if ((packages && packages.length > 0) || (menuItems && menuItems.length > 0) || (customers && customers.length > 0)) {
    replaceMasterTablesWithDbIds({
      packages: packages || [],
      menuItems: menuItems || [],
      packageItems: packageItems || [],
      packageBuckets: packageBuckets || [],
      customers: customers || []
    });
  }

  if (pendingPackageImages.size > 0) {
    for (const [pkgId, pending] of pendingPackageImages.entries()) {
      try {
        const exists = fetchOne("SELECT pkg_id FROM packages WHERE pkg_id = ?", [pkgId]);
        if (!exists) continue;
        const img = Number(pending.remove_image || 0) ? "" : (pending.image_data || "");
        run("UPDATE packages SET pkg_image = ?, image = ? WHERE pkg_id = ?", [img, img, pkgId]);
        saveEntityImage("package", pkgId, img);
      } catch (_) {}
    }
  }

  if (pendingMenuItemImages.size > 0) {
    for (const [miId, pending] of pendingMenuItemImages.entries()) {
      try {
        const exists = fetchOne("SELECT mi_id FROM menu_items WHERE mi_id = ?", [miId]);
        if (!exists) continue;
        const img = Number(pending.remove_image || 0) ? "" : (pending.image_data || "");
        run("UPDATE menu_items SET mi_image = ?, image = ? WHERE mi_id = ?", [img, img, miId]);
        saveEntityImage("menu_item", miId, img);
      } catch (_) {}
    }
  }

  if (menuCategories && menuCategories.length > 0) {
    try { reorderMenuCategories(menuCategories); } catch (_) {}
  }

  if (occasions && occasions.length > 0) {
    for (const occ of occasions) {
      const name = (occ.occ_name || occ.name || "").trim();
      if (name) {
        try {
          if (occ.occ_id) {
            run("INSERT OR REPLACE INTO occasions (occ_id, occ_name, occ_is_active) VALUES (?, ?, 1)", [occ.occ_id, name]);
          } else {
            run("INSERT OR IGNORE INTO occasions (occ_name, occ_is_active) VALUES (?, 1)", [name]);
          }
        } catch (_) {}
      }
    }
  }

  if (typeof window !== "undefined") {
    if (typeof window.__clearWizardCaches === "function") {
      window.__clearWizardCaches();
    }
    if (typeof window.__onMasterDataUpdated === "function") {
      window.__onMasterDataUpdated();
    }
    window.dispatchEvent(new CustomEvent("jayraldines:sync-completed", {
      detail: { packages, menu_items: menuItems, package_items: packageItems, package_buckets: packageBuckets, customers, occasions }
    }));
  }
}

// ── Occasions / Event Types ──────────────────────────────────────────

export function getAllOccasions() {
  try {
    const rows = fetchAll("SELECT occ_id, occ_name, occ_is_active FROM occasions WHERE occ_is_active = 1 OR occ_is_active IS NULL ORDER BY occ_name COLLATE NOCASE ASC");
    if (rows && rows.length > 0) {
      return rows.map((r) => ({ id: r.occ_id, name: r.occ_name, is_active: r.occ_is_active }));
    }
  } catch (err) {
    console.warn("[repository] getAllOccasions error:", err);
  }
  return [
    { id: 1, name: "Wedding", is_active: 1 },
    { id: 2, name: "Birthday", is_active: 1 },
    { id: 3, name: "Debut", is_active: 1 },
    { id: 4, name: "Corporate Event", is_active: 1 },
    { id: 5, name: "Anniversary", is_active: 1 },
    { id: 6, name: "Christening", is_active: 1 },
    { id: 7, name: "Graduation", is_active: 1 },
    { id: 8, name: "Holiday Party", is_active: 1 }
  ];
}

export function addOccasion(name) {
  name = (name || "").trim();
  if (!name) throw new Error("Event type name cannot be empty.");
  run("INSERT OR REPLACE INTO occasions (occ_name, occ_is_active) VALUES (?, 1)", [name]);
  return getAllOccasions();
}

export function updateOccasion(id, newName) {
  newName = (newName || "").trim();
  if (!newName) throw new Error("Event type name cannot be empty.");
  run("UPDATE occasions SET occ_name = ? WHERE occ_id = ?", [newName, id]);
  return getAllOccasions();
}

export function deleteOccasion(id) {
  run("DELETE FROM occasions WHERE occ_id = ?", [id]);
  return getAllOccasions();
}

export function purgeDeletedBookings(refs = []) {
  if (!refs || refs.length === 0) return;
  for (const ref of refs) {
    try {
      const b = fetchOne("SELECT bk_id FROM bookings WHERE bk_booking_ref = ?", [ref]);
      if (b && b.bk_id) {
        run("DELETE FROM booking_menu_items WHERE bmi_booking_id = ?", [b.bk_id]);
        run("DELETE FROM invoices WHERE inv_booking_id = ?", [b.bk_id]);
        run("DELETE FROM bookings WHERE bk_id = ?", [b.bk_id]);
      }
    } catch (_) {}
  }
}

