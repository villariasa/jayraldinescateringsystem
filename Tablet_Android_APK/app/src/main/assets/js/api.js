// Facade over the in-browser data layer (sqlite.js / repository.js /
// importer.js / exporter.js). Kept as a single "api" object with the same
// shape the UI modules (wizard.js, settings.js, app.js) already call, so
// swapping the transport (originally: fetch() to a Python server; now:
// direct calls into an in-browser SQLite database) didn't require
// rewriting the UI layer.
import { initDb, exportDbBytes } from "./sqlite.js";
import * as repo from "./repository.js";
import * as importerMod from "./importer.js";
import * as exporterMod from "./exporter.js";
import * as termsMod from "./terms.js";
import { toast } from "./views.js";

let dbReady = null;
function ready() {
  if (!dbReady) dbReady = initDb();
  return dbReady;
}

export const api = {
  async health() { await ready(); return { status: "ok" }; },
  async terms() { await ready(); return termsMod.getTerms(); },

  // Customers
  async searchCustomers(q) { await ready(); return repo.searchCustomers(q); },
  async duplicateCheck(contact, name) { await ready(); return repo.findPossibleDuplicateCustomer(contact, name) || {}; },
  async createCustomer(data) {
    await ready();
    const id = repo.addCustomer(data.name, data.contact, data.email, data.address);
    setTimeout(() => {
      api.autoSyncPendingRecords().catch(() => {});
    }, 300);
    return { id };
  },
  async updateCustomer(id, data) { await ready(); return { ok: repo.updateCustomer(id, data.name, data.contact, data.email, data.address) }; },
  async deleteCustomer(id) { await ready(); repo.deleteCustomer(id); return { ok: true }; },

  // Addresses
  async searchAddress(q) { await ready(); return repo.searchCebuAddress(q); },

  // Packages
  async getPackages() { await ready(); return repo.getPackages(); },
  async createPackage(data) { await ready(); return { id: repo.addPackage(data.name, data.description, data.price_per_pax, data.min_pax, data.image) }; },
  async updatePackage(id, data) { await ready(); return { ok: repo.updatePackage(id, data.name, data.description, data.price_per_pax, data.min_pax, data.image) }; },
  async deletePackage(id) { await ready(); repo.deletePackage(id); return { ok: true }; },

  // Menu items
  async getMenuItems() { await ready(); return repo.getAllMenuItems(); },
  async getMenuItemsGrouped() { await ready(); return repo.getPackageMenuChoices(); },
  async getMenuCategories() { await ready(); return repo.getMenuCategories(); },
  async createMenuItem(data) { await ready(); return { id: repo.addMenuItem(data.name, data.category, data.price, data.status, data.description, data.image) }; },
  async updateMenuItem(id, data) { await ready(); return { ok: repo.updateMenuItem(id, data.name, data.category, data.price, data.status, data.description, data.image) }; },
  async deleteMenuItem(id) { await ready(); repo.deleteMenuItem(id); return { ok: true }; },

  // Orders
  async getOrders() { await ready(); return repo.getAllOrders(); },
  async getOrder(id) { await ready(); return repo.getOrderDetail(id); },
  async placeOrder(data) {
    await ready();
    const res = repo.createOrder(data);
    setTimeout(() => {
      api.autoSyncPendingRecords().catch(() => {});
    }, 300);
    return res;
  },

  async downloadReceipt(bookingId) {
    await ready();
    const order = repo.getOrderDetail(Number(bookingId)) || repo.getOrderDetail(bookingId);
    if (!order) {
      toast("Order record not found.", "error");
      throw new Error("Order not found");
    }
    try {
      const blob = exporterMod.exportOrderReceiptPdf(order, "Jayraldine's Catering", false);
      const filename = `receipt_${order.booking_ref || order.booking_id || bookingId || "order"}.pdf`;
      downloadBlob(blob, filename);
      toast("Receipt PDF downloaded.", "success");
    } catch (err) {
      console.error("PDF Receipt download error:", err);
      toast("Failed to download PDF: " + err.message, "error");
    }
  },

  async archiveAndClear() {
    await ready();
    const { blob, ordersCount } = exporterMod.exportAllOrdersToExcel();
    downloadBlob(blob, `Orders_Archive_${timestamp()}.xlsx`);
    const cleared = repo.clearAllOrders();
    return { archived_orders: ordersCount, cleared_orders: cleared };
  },

  async downloadOrdersExcel() {
    await ready();
    const { blob } = exporterMod.exportAllOrdersToExcel();
    downloadBlob(blob, `Orders_Export_${timestamp()}.xlsx`);
  },

  async downloadDatabase() {
    await ready();
    const bytes = exportDbBytes();
    downloadBlob(new Blob([bytes], { type: "application/octet-stream" }), `catering_pwa_export_${timestamp()}.db`);
  },

  async downloadTemplate() {
    await ready();
    const blob = importerMod.generateSampleExcelTemplate();
    downloadBlob(blob, "master_data_template.xlsx");
  },

  // Sync
  async syncStatus() {
    await ready();
    const last = importerMod.getLastMasterSync();
    return { last_sync: last, packages_count: repo.getPackages().length, menu_items_count: repo.getAllMenuItems().length };
  },
  async importMasterData(file) {
    await ready();
    const stats = await importerMod.importMasterData(file);
    return stats;
  },

  async checkLanStatus(host, port) {
    const urls = _getSyncBaseUrls(host, port);
    const dbPort = (port && parseInt(port, 10) === 5432) ? 5432 : 5432;
    const cleanHost = (host || "").trim().replace(/^https?:\/\//i, "").split(":")[0] || "127.0.0.1";

    for (const base of urls) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3500);
        const q = `?host=${encodeURIComponent(cleanHost)}&port=${dbPort}`;
        const res = await fetch(`${base}/api/sync/lan-status${q}`, {
          signal: controller.signal,
          headers: { "Accept": "application/json" }
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          data._baseUrl = base;
          return data;
        }
      } catch (e) {
        // Fall through to next candidate URL
      }
    }
    return { online: false, pending_bookings: 0, pending_customers: 0 };
  },

  async performLanSync(params) {
    const host = params?.host || "";
    const port = params?.port || 5432;
    const urls = _getSyncBaseUrls(host, port);

    let lastErr = null;
    for (const base of urls) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 20000);
        const res = await fetch(`${base}/api/sync/lan-sync`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Accept": "application/json" },
          body: JSON.stringify(params || {}),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          return await res.json();
        } else {
          const errData = await res.json().catch(() => ({ detail: `HTTP ${res.status}: ${res.statusText}` }));
          throw new Error(errData.detail || `Sync failed with HTTP status ${res.status}`);
        }
      } catch (err) {
        lastErr = err;
      }
    }
    const targetDesc = host ? `${host}` : "Central Server PC";
    throw new Error(
      lastErr?.message ||
      `Could not reach Central Server at ${targetDesc} (port 8000). Ensure the PC is on the same Wi-Fi and Central Server is running.`
    );
  },

  async autoDiscoverServer() {
    const candidates = [];
    const savedHost = (localStorage.getItem("jayraldines_lan_host") || "").trim();
    if (savedHost) candidates.push(savedHost);

    // If testing directly on local PC
    candidates.push("127.0.0.1");

    if (typeof window !== "undefined" && window.location && window.location.hostname) {
      const h = window.location.hostname;
      if (h && !h.includes("androidplatform") && !candidates.includes(h)) {
        candidates.push(h);
      }
    }

    // Common mobile hotspot and LAN gateway IPs
    const commonGateways = ["192.168.1.", "192.168.0.", "192.168.43.", "192.168.137.", "10.105.101."];
    for (const prefix of commonGateways) {
      for (const lastOctet of [1, 2, 5, 10, 15, 20, 50, 100, 120]) {
        const ip = `${prefix}${lastOctet}`;
        if (!candidates.includes(ip)) candidates.push(ip);
      }
    }

    const probe = async (host) => {
      try {
        const clean = host.replace(/^https?:\/\//i, "").split(":")[0];
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 1000);
        const res = await fetch(`http://${clean}:8000/api/sync/lan-status?host=${encodeURIComponent(clean)}&port=5432`, {
          signal: controller.signal,
          headers: { "Accept": "application/json" }
        });
        clearTimeout(tid);
        if (res.ok) {
          const data = await res.json();
          if (data.online) return clean;
        }
      } catch (_) {}
      return null;
    };

    const results = await Promise.allSettled(candidates.map(probe));
    for (const r of results) {
      if (r.status === "fulfilled" && r.value) {
        localStorage.setItem("jayraldines_lan_host", r.value);
        console.log(`[AutoDiscover] Successfully detected server at ${r.value}:8000`);
        return r.value;
      }
    }
    return savedHost || null;
  },

  async autoSyncPendingRecords() {
    await ready();
    let host = localStorage.getItem("jayraldines_lan_host") || "";
    if (!host) {
      host = await api.autoDiscoverServer();
    }
    if (!host) return null;

    const { bookings, customers } = repo.getPendingSyncRecords();
    try {
      const res = await api.performLanSync({
        host,
        port: 5432,
        dbname: localStorage.getItem("jayraldines_lan_dbname") || "jayraldines_catering",
        user: localStorage.getItem("jayraldines_lan_user") || "postgres",
        password: localStorage.getItem("jayraldines_lan_password") || "12345678",
        bookings: bookings || [],
        customers: customers || [],
      });
      if (res.packages || res.menu_items || res.customers) {
        repo.updateMasterDataFromSync(res.packages || [], res.menu_items || [], res.package_items || [], res.customers || []);
      }
      if (res.synced_booking_refs || res.synced_customer_names) {
        repo.markRecordsSynced(res.synced_booking_refs || [], res.synced_customer_names || []);
      }
      return res;
    } catch (e) {
      console.warn("[AutoSync] Background push note:", e);
      return null;
    }
  },

  async autoDiscoverAndSync() {
    const host = await api.autoDiscoverServer();
    if (host) {
      return await api.autoSyncPendingRecords();
    }
    return null;
  },
};

function _getSyncBaseUrls(host, port) {
  const urls = [];
  const rawHost = (host || "").trim().replace(/^https?:\/\//i, "").replace(/\/+$/, "");

  if (rawHost) {
    let cleanHost = rawHost;
    let syncPort = 8000;
    if (rawHost.includes(":")) {
      const parts = rawHost.split(":");
      cleanHost = parts[0];
      syncPort = parseInt(parts[1], 10) || 8000;
      urls.push(`http://${cleanHost}:${syncPort}`);
    } else {
      const p = parseInt(port, 10);
      if (p && p !== 5432) {
        urls.push(`http://${cleanHost}:${p}`);
      }
      urls.push(`http://${cleanHost}:8000`);
      if (p && p === 5432) {
        // Also fallback to default 8000 if user input 5432 (Postgres DB port)
        urls.push(`http://${cleanHost}:8000`);
      }
    }
  }

  // Fallback to current browser origin if not file: or androidplatform
  if (typeof window !== "undefined" && window.location && window.location.origin) {
    const orig = window.location.origin;
    if (!orig.startsWith("file:") && !orig.includes("androidplatform.net")) {
      if (!urls.includes(orig)) urls.push(orig);
    }
  }

  if (urls.length === 0) {
    urls.push("http://127.0.0.1:8000");
  }
  return urls;
}

function timestamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
}

export function downloadBlob(blob, filename) {
  // 1. If running inside Android native APK app, save directly to device Downloads folder
  if (window.AndroidNative && typeof window.AndroidNative.saveBase64File === "function") {
    const reader = new FileReader();
    reader.onloadend = () => {
      const base64 = (reader.result || "").split(",")[1];
      if (base64) {
        window.AndroidNative.saveBase64File(base64, filename, blob.type || "application/pdf");
      }
    };
    reader.readAsDataURL(blob);
    return;
  }

  // 2. Browser blob anchor download with mobile fallbacks
  try {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.style.display = "none";
    a.href = url;
    a.download = filename;
    a.target = "_blank";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      a.remove();
      URL.revokeObjectURL(url);
    }, 15000);
  } catch (err) {
    console.warn("Direct blob download error, falling back to window.open:", err);
    const reader = new FileReader();
    reader.onloadend = () => {
      window.open(reader.result, "_blank");
    };
    reader.readAsDataURL(blob);
  }
}
