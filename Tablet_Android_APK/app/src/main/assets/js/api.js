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

let _liveDbConnected = false;
let _lastSyncTimestamp = 0;
let _liveSyncInFlight = null;

function _detectDeviceType() {
  const ua = (typeof navigator !== "undefined" ? navigator.userAgent : "") || "";
  const isAndroid = /Android/i.test(ua) || ua.includes("com.jayraldines");
  const isIos = /iPhone|iPad|iPod/i.test(ua);
  const isIpad = /iPad/i.test(ua) || (typeof navigator !== "undefined" && navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const isIphone = /iPhone|iPod/i.test(ua);

  let minDimension = 0;
  if (typeof window !== "undefined" && window.screen) {
    minDimension = Math.min(window.screen.width || 0, window.screen.height || 0);
  }

  // An Android browser on a phone always sends "Mobile" in the UA. Tablets omit "Mobile".
  // Mobile phones also have screen width < 600 CSS pixels.
  const hasMobileToken = /Mobile/i.test(ua);
  const isSmallScreen = minDimension > 0 && minDimension < 600;

  let category = "Mobile Phone";
  if (isIpad || (!hasMobileToken && isAndroid && !isSmallScreen) || minDimension >= 600) {
    category = "Tablet";
  } else if (hasMobileToken || isIphone || isSmallScreen) {
    category = "Mobile Phone";
  }

  let osName = "Android";
  if (isIos) osName = "iOS";
  else if (/Windows/i.test(ua)) osName = "Windows";
  else if (/Mac/i.test(ua) && !isIpad) osName = "macOS";
  else if (/Linux/i.test(ua) && !isAndroid) osName = "Linux";
  else if (isAndroid) osName = "Android";

  const isApk = ua.includes("com.jayraldines") || (typeof window !== "undefined" && !!window.AndroidNative);
  const typeTag = isApk ? "APK" : "PWA";

  return {
    category,
    osName,
    typeTag,
    // NOTE: must stay pure ASCII/Latin-1 - sent verbatim as the raw
    // "X-Device-Host" HTTP header (see performLanSync/checkLanStatus). A
    // non-Latin1 character here makes fetch() throw before any request is
    // even sent, which looks like a connection/CORS failure but isn't.
    hostname: `${osName} ${category}`,
    os_info: `${osName} ${category} (${typeTag})`
  };
}

function _getTabletDeviceInfo() {
  const detected = _detectDeviceType();
  let devId = localStorage.getItem("jayraldines_tablet_device_id");
  const prefix = detected.category === "Mobile Phone" ? "phone-" : "tablet-";

  if (!devId) {
    devId = prefix + Math.random().toString(36).substring(2, 10);
    localStorage.setItem("jayraldines_tablet_device_id", devId);
  } else {
    // If device was previously misidentified as tablet or phone, correct prefix
    if (detected.category === "Mobile Phone" && devId.startsWith("tablet-")) {
      devId = devId.replace("tablet-", "phone-");
      localStorage.setItem("jayraldines_tablet_device_id", devId);
    } else if (detected.category === "Tablet" && devId.startsWith("phone-")) {
      devId = devId.replace("phone-", "tablet-");
      localStorage.setItem("jayraldines_tablet_device_id", devId);
    }
  }

  return {
    device_id: devId,
    hostname: detected.hostname,
    os_info: detected.os_info,
    app_version: "v1.26.13",
    active_module: "Customer Booking Kiosk"
  };
}

function _getStoredSyncHost() {
  return (localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.origin : "") || "").trim();
}

async function _flushPendingPackageImageUploads(host, port = 8000) {
  const pending = repo.getPendingPackageImageUploads ? repo.getPendingPackageImageUploads() : [];
  const summary = { total: pending.length, synced: 0, failed: 0, errors: [] };
  if (!pending.length) return summary;

  const urls = _getSyncBaseUrls(host || _getStoredSyncHost(), port);
  const dev = _getTabletDeviceInfo();

  for (const upload of pending) {
    let uploaded = false;
    let lastErr = null;

    for (const base of urls) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);
        const res = await fetch(`${base}/api/packages/image-upload`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "ngrok-skip-browser-warning": "69420",
            "X-Device-Id": dev.device_id,
            "X-Device-Host": dev.hostname,
            "X-Device-OS": dev.os_info
          },
          body: JSON.stringify({
            ...dev,
            pkg_id: Number(upload.pkg_id),
            image: upload.image_data || "",
            remove: Number(upload.remove_image || 0) === 1,
          }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.error) {
          throw new Error(data.error || data.detail || `Image upload failed with HTTP ${res.status}`);
        }

        repo.markPackageImageSynced(Number(upload.pkg_id), data.pkg_image || "", data.image || "");
        _liveDbConnected = true;
        _lastSyncTimestamp = Date.now();
        localStorage.setItem("jayraldines_lan_host", base);
        window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: base } }));
        summary.synced++;
        uploaded = true;
        break;
      } catch (err) {
        lastErr = err;
      }
    }

    if (!uploaded) {
      const msg = lastErr?.message || "Package image upload failed.";
      repo.markPackageImageUploadFailed(Number(upload.pkg_id), msg);
      summary.failed++;
      summary.errors.push({ pkg_id: Number(upload.pkg_id), error: msg });
    }
  }

  return summary;
}

export const api = {
  async health() { await ready(); return { status: "ok" }; },
  async terms() { await ready(); return termsMod.getTerms(); },

  isLiveConnected() {
    return _liveDbConnected;
  },

  async ensureLiveConnection(force = false) {
    await ready();
    const now = Date.now();
    if (!force && _liveDbConnected && (now - _lastSyncTimestamp < 15000)) {
      return true;
    }

    try {
      // 1. Check user-configured host first (highest priority, e.g. 192.168.1.32)
      const savedHost = (localStorage.getItem("jayraldines_lan_host") || "").trim();
      if (savedHost) {
        const stat = await api.checkLanStatus(savedHost, 8000);
        if (stat && stat.online && (stat.db_connected !== false)) {
          _liveDbConnected = true;
          _lastSyncTimestamp = Date.now();
          api.syncWithServer({ host: savedHost, port: 8000 })
            .catch((e) => console.warn("[LiveDB] Background sync note:", e));
          window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: savedHost } }));
          return true;
        }
      }

      // 2. Fallback to browser URL origin only if no savedHost is configured or if savedHost is unreachable
      let currentOrigin = "";
      if (typeof window !== "undefined" && window.location && window.location.origin) {
        const orig = window.location.origin;
        if (orig.startsWith("http://") || orig.startsWith("https://")) {
          currentOrigin = orig;
        }
      }

      if (currentOrigin && currentOrigin !== savedHost) {
        const stat = await api.checkLanStatus(currentOrigin, 8000);
        if (stat && stat.online && (stat.db_connected !== false)) {
          _liveDbConnected = true;
          _lastSyncTimestamp = Date.now();
          if (!savedHost) {
            localStorage.setItem("jayraldines_lan_host", currentOrigin);
          }
          api.syncWithServer({ host: currentOrigin, port: 8000 })
            .catch((e) => console.warn("[LiveDB] Background sync note:", e));
          window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: currentOrigin } }));
          return true;
        }
      }

      // 3. Discover server on LAN
      const host = await api.autoDiscoverServer();
      if (host) {
        _liveDbConnected = true;
        _lastSyncTimestamp = Date.now();
        api.syncWithServer({ host, port: 8000 })
          .catch((e) => console.warn("[LiveDB] Background sync note:", e));
        window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: host } }));
        return true;
      }
    } catch (err) {
      console.warn("[LiveDB] Connection check note:", err.message);
    }

    _liveDbConnected = false;
    window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: false } }));
    return false;
  },

  // Customers (Offline-first with background sync)
  async searchCustomers(q) {
    await ready();
    return repo.searchCustomers(q);
  },

  async duplicateCheck(contact, name) {
    await ready();
    return repo.findPossibleDuplicateCustomer(contact, name) || {};
  },

  async createCustomer(data) {
    await ready();
    const id = repo.addCustomer(data.name, data.contact, data.email, data.address);
    api.autoSyncPendingRecords().catch(() => {});
    return { id };
  },

  async updateCustomer(id, data) { await ready(); return { ok: repo.updateCustomer(id, data.name, data.contact, data.email, data.address) }; },
  async deleteCustomer(id) { await ready(); repo.deleteCustomer(id); return { ok: true }; },

  // Addresses
  async searchAddress(q) { await ready(); return repo.searchCebuAddress(q); },

  // Packages (Offline-first: returns local SQLite packages; syncs if online)
  async getPackages() {
    await ready();
    api.ensureLiveConnection().catch(() => {});
    return repo.getPackages();
  },

  async createPackage(data) {
    await ready();
    const id = repo.addPackage(data.name, data.description, data.price_per_pax, data.min_pax, data.image);
    const imageChanged = Boolean(data.image_changed || data.imageChanged || data.image);
    if (imageChanged) {
      repo.queuePackageImageUpload(id, data.image || "", !data.image);
      api.autoSyncPendingRecords().catch((e) => console.warn("[LiveDB] Package image upload queued:", e));
    }
    return { id, image_sync: imageChanged ? "pending" : "none" };
  },
  async updatePackage(id, data) {
    await ready();
    const imageChanged = Boolean(data.image_changed || data.imageChanged);
    const ok = repo.updatePackage(id, data.name, data.description, data.price_per_pax, data.min_pax, imageChanged ? data.image : undefined);
    if (imageChanged) {
      repo.queuePackageImageUpload(id, data.image || "", !data.image);
      api.autoSyncPendingRecords().catch((e) => console.warn("[LiveDB] Package image upload queued:", e));
    }
    return { ok, image_sync: imageChanged ? "pending" : "unchanged" };
  },
  async deletePackage(id) { await ready(); repo.deletePackage(id); return { ok: true }; },

  // Menu items (Offline-first: returns local SQLite menu items)
  async getMenuItems() {
    await ready();
    api.ensureLiveConnection().catch(() => {});
    return repo.getAllMenuItems();
  },

  async getMenuItemsGrouped() {
    await ready();
    api.ensureLiveConnection().catch(() => {});
    return repo.getPackageMenuChoices();
  },

  async getMenuCategories() {
    await ready();
    return repo.getMenuCategories();
  },

  async createMenuItem(data) { await ready(); return { id: repo.addMenuItem(data.name, data.category, data.price, data.status, data.description, data.image) }; },
  async updateMenuItem(id, data) { await ready(); return { ok: repo.updateMenuItem(id, data.name, data.category, data.price, data.status, data.description, data.image) }; },
  async deleteMenuItem(id) { await ready(); repo.deleteMenuItem(id); return { ok: true }; },

  // Occasions / Event Types
  async getOccasions() {
    await ready();
    return repo.getAllOccasions();
  },

  async createOccasion(data) {
    await ready();
    const name = typeof data === "string" ? data : (data.name || "");
    const res = repo.addOccasion(name);
    try {
      const savedHost = (localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.origin : "")).trim();
      if (savedHost) {
        fetch(`${savedHost}/api/db/write`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sql: "INSERT OR REPLACE INTO occasions (occ_name, occ_is_active) VALUES (?, 1)",
            params: [name]
          })
        }).catch(() => {});
      }
    } catch (_) {}
    return res;
  },

  async updateOccasion(id, data) {
    await ready();
    const name = typeof data === "string" ? data : (data.name || "");
    const res = repo.updateOccasion(id, name);
    try {
      const savedHost = (localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.origin : "")).trim();
      if (savedHost) {
        fetch(`${savedHost}/api/db/write`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sql: "UPDATE occasions SET occ_name = ? WHERE occ_id = ?",
            params: [name, id]
          })
        }).catch(() => {});
      }
    } catch (_) {}
    return res;
  },

  async deleteOccasion(id, name = "") {
    await ready();
    const res = repo.deleteOccasion(id);
    try {
      const savedHost = (localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.origin : "")).trim();
      if (savedHost) {
        fetch(`${savedHost}/api/db/write`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sql: "DELETE FROM occasions WHERE occ_id = ?" + (name ? " OR occ_name = ?" : ""),
            params: name ? [id, name] : [id]
          })
        }).catch(() => {});
      }
    } catch (_) {}
    return res;
  },

  // Orders (Offline-first: saves locally in SQLite, syncs immediately if online)
  async getOrders() {
    await ready();
    api.ensureLiveConnection().catch(() => {});
    return repo.getAllOrders();
  },

  async getOrder(id) { await ready(); return repo.getOrderDetail(id); },

  async placeOrder(data) {
    await ready();
    // 1. Always record order in local SQLite
    const res = repo.createOrder(data);

    // 2. If connected, push to Live Central DB immediately; if offline, keep pending
    try {
      api.autoSyncPendingRecords().catch((e) => {
        console.warn("[LiveDB] Auto-sync scheduled for next reconnection:", e);
      });
    } catch (_) {}

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

  async checkLanStatus(host, port = 8000) {
    const urls = _getSyncBaseUrls(host, port);
    const cleanHost = (host || "").trim().replace(/^https?:\/\//i, "").split(":")[0] || "127.0.0.1";
    const dev = _getTabletDeviceInfo();
    let lastError = null;

    for (const base of urls) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3500);
        const q = `?host=${encodeURIComponent(cleanHost)}&port=${encodeURIComponent(port)}&device_id=${encodeURIComponent(dev.device_id)}&hostname=${encodeURIComponent(dev.hostname)}&os_info=${encodeURIComponent(dev.os_info)}&app_version=${encodeURIComponent(dev.app_version)}&active_module=${encodeURIComponent(dev.active_module)}`;
        const res = await fetch(`${base}/api/sync/lan-status${q}`, {
          signal: controller.signal,
          headers: {
            "Accept": "application/json",
            "X-Device-Id": dev.device_id,
            "X-Device-Host": dev.hostname,
            "X-Device-OS": dev.os_info
          }
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          data._baseUrl = base;
          const isLive = Boolean(data.online && (data.db_connected !== false));
          _liveDbConnected = isLive;
          _lastSyncTimestamp = Date.now();
          localStorage.setItem("jayraldines_lan_host", base);
          window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: isLive, server: base } }));
          return data;
        }
        lastError = `HTTP ${res.status} from ${base}`;
      } catch (e) {
        lastError = `${e.name || "Error"}: ${e.message || e}`;
        console.error(`[checkLanStatus] fetch to ${base} failed:`, e);
        // Fall through to next candidate URL
      }
    }
    _liveDbConnected = false;
    window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: false, error: lastError } }));
    return { online: false, db_connected: false, pending_bookings: 0, pending_customers: 0, error: lastError };
  },

  async performLanSync(params) {
    const host = params?.host || (typeof window !== "undefined" && window.location && window.location.origin ? window.location.origin : "");
    const port = params?.port || 8000;
    const urls = _getSyncBaseUrls(host, port);
    const dev = _getTabletDeviceInfo();
    const payload = Object.assign({}, dev, params || {});

    let lastErr = null;
    for (const base of urls) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 45000);
        const res = await fetch(`${base}/api/sync/lan-sync`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "ngrok-skip-browser-warning": "69420",
            "X-Device-Id": dev.device_id,
            "X-Device-Host": dev.hostname,
            "X-Device-OS": dev.os_info
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          _liveDbConnected = true;
          _lastSyncTimestamp = Date.now();
          window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: base } }));
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

  async syncWithServer(params = {}) {
    if (_liveSyncInFlight) return _liveSyncInFlight;

    _liveSyncInFlight = (async () => {
      await ready();
      let host = params.host || _getStoredSyncHost();
      const port = params.port || Number(localStorage.getItem("jayraldines_lan_port") || 8000) || 8000;
      if (!host) {
        host = await api.autoDiscoverServer();
      }
      if (!host) {
        throw new Error("Central Server host is not configured.");
      }

      const imageSync = await _flushPendingPackageImageUploads(host, port);
      const { bookings, customers } = repo.getPendingSyncRecords();
      const res = await api.performLanSync({
        ...params,
        host,
        port,
        dbname: params.dbname || localStorage.getItem("jayraldines_lan_dbname") || "catering.db",
        user: params.user || localStorage.getItem("jayraldines_lan_user") || "admin",
        password: params.password || localStorage.getItem("jayraldines_lan_password") || "12345678",
        bookings: params.bookings || bookings || [],
        customers: params.customers || customers || [],
      });

      if (res.packages || res.menu_items || res.customers || res.occasions) {
        repo.updateMasterDataFromSync(res.packages || [], res.menu_items || [], res.package_items || [], res.customers || [], res.occasions || []);
      }
      if (res.synced_booking_refs || res.synced_customer_names) {
        repo.markRecordsSynced(res.synced_booking_refs || [], res.synced_customer_names || []);
      }

      const detail = {
        ...res,
        pushed_package_images: imageSync.synced,
        failed_package_images: imageSync.failed,
        package_image_errors: imageSync.errors,
      };
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("jayraldines:sync-completed", { detail }));
      }
      return detail;
    })();

    try {
      return await _liveSyncInFlight;
    } finally {
      _liveSyncInFlight = null;
    }
  },

  async autoDiscoverServer() {
    const candidates = [];
    const savedHost = (localStorage.getItem("jayraldines_lan_host") || "").trim();
    if (savedHost) candidates.push(savedHost);

    // If opened via browser URL, add origin after savedHost
    if (typeof window !== "undefined" && window.location && window.location.origin) {
      const orig = window.location.origin;
      if (!orig.startsWith("file:") && !orig.includes("androidplatform")) {
        if (!candidates.includes(orig)) candidates.push(orig);
      }
    }

    // Common mobile hotspot and LAN gateway IPs (including 32, 34, 10, etc.)
    const commonGateways = ["192.168.1.", "192.168.0.", "192.168.4.", "192.168.43.", "192.168.137.", "10.105.101."];
    const octets = [32, 34, 1, 2, 5, 10, 15, 20, 30, 31, 33, 35, 40, 50, 100, 120, 128];
    for (const prefix of commonGateways) {
      for (const lastOctet of octets) {
        const ip = `${prefix}${lastOctet}`;
        if (!candidates.includes(ip)) candidates.push(ip);
      }
    }

    // Localhost fallback
    candidates.push("http://127.0.0.1:8000");
    candidates.push("127.0.0.1");

    const probe = async (target) => {
      try {
        const baseUrls = _getSyncBaseUrls(target, 8000);
        for (const base of baseUrls) {
          try {
            const controller = new AbortController();
            const tid = setTimeout(() => controller.abort(), 2000);
            const res = await fetch(`${base}/api/sync/lan-status`, {
              signal: controller.signal,
              headers: {
                "Accept": "application/json",
                "ngrok-skip-browser-warning": "69420"
              }
            });
            clearTimeout(tid);
            if (res.ok) {
              const data = await res.json();
              if (data.online && (data.db_connected !== false)) {
                return base;
              }
            }
          } catch (_) {}
        }
      } catch (_) {}
      return null;
    };

    // First check high-priority candidates quickly
    for (const c of candidates.slice(0, 4)) {
      const found = await probe(c);
      if (found) {
        localStorage.setItem("jayraldines_lan_host", found);
        console.log(`[AutoDiscover] Connected to server at ${found}`);
        return found;
      }
    }

    const results = await Promise.allSettled(candidates.map(probe));
    for (const r of results) {
      if (r.status === "fulfilled" && r.value) {
        localStorage.setItem("jayraldines_lan_host", r.value);
        console.log(`[AutoDiscover] Successfully detected server at ${r.value}`);
        return r.value;
      }
    }
    return savedHost || null;
  },

  async autoSyncPendingRecords() {
    await ready();
    let host = _getStoredSyncHost();
    if (!host) {
      host = await api.autoDiscoverServer();
    }
    if (!host) return null;

    try {
      return await api.syncWithServer({
        host,
        port: Number(localStorage.getItem("jayraldines_lan_port") || 8000) || 8000,
        dbname: localStorage.getItem("jayraldines_lan_dbname") || "catering.db",
        user: localStorage.getItem("jayraldines_lan_user") || "admin",
        password: localStorage.getItem("jayraldines_lan_password") || "12345678",
      });
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

function _getSyncBaseUrls(host, port = 8000) {
  const urls = [];
  const trimmed = (host || "").trim();

  if (trimmed) {
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
      const cleanUrl = trimmed.replace(/\/+$/, "");
      urls.push(cleanUrl);
      // If already a complete HTTPS URL without custom port, prioritize it directly
      const colonCount = (cleanUrl.match(/:/g) || []).length;
      if (cleanUrl.startsWith("https://") && colonCount === 1) {
        return urls;
      }
    }

    const rawHost = trimmed.replace(/^https?:\/\//i, "").replace(/\/+$/, "");
    if (rawHost) {
      if (rawHost.includes(".ngrok") || rawHost.includes(".trycloudflare.com") || rawHost.includes(".loca.lt")) {
        if (!urls.includes(`https://${rawHost}`)) urls.unshift(`https://${rawHost}`);
      } else if (rawHost.includes(":")) {
        const p = `http://${rawHost}`;
        if (!urls.includes(p)) urls.push(p);
      } else {
        const p = parseInt(port, 10);
        if (p && p !== 8000) {
          const u = `http://${rawHost}:${p}`;
          if (!urls.includes(u)) urls.push(u);
        }
        const defU = `http://${rawHost}:8000`;
        if (!urls.includes(defU)) urls.push(defU);
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

// Background device heartbeat to maintain live presence in the Desktop App's Device Monitoring panel
if (typeof window !== "undefined") {
  setInterval(async () => {
    try {
      const savedHost = (localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.origin : "")).trim();
      if (savedHost) {
        await api.checkLanStatus(savedHost, 8000);
      }
    } catch (_) {}
  }, 15000);

  // Send immediate offline signal when user closes the app, closes tab, or navigates away
  const markOffline = () => {
    try {
      const dev = _getTabletDeviceInfo();
      const host = (localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.origin : "")).trim();
      if (dev.device_id && host) {
        const urls = _getSyncBaseUrls(host, 8000);
        for (const base of urls) {
          const endpoint = `${base}/api/sync/device-offline?device_id=${encodeURIComponent(dev.device_id)}`;
          if (navigator.sendBeacon) {
            navigator.sendBeacon(endpoint);
          } else {
            fetch(endpoint, { keepalive: true, method: "GET" }).catch(() => {});
          }
        }
      }
    } catch (_) {}
  };

  window.addEventListener("pagehide", markOffline);
  window.addEventListener("beforeunload", markOffline);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      markOffline();
    } else if (document.visibilityState === "visible") {
      const host = (localStorage.getItem("jayraldines_lan_host") || (typeof window !== "undefined" && window.location ? window.location.origin : "")).trim();
      if (host) api.checkLanStatus(host, 8000).catch(() => {});
    }
  });
}
