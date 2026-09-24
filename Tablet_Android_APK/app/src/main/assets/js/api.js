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
let _lastCheckAttempt = 0;
let _knownServerDbVersion = null;
let _liveSyncInFlight = null;
let _connectionCheckInFlight = null;
let _autoDiscoverInFlight = null;

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

  const isApk = ua.includes("com.jayraldines") || ua.includes("jayraldinesapk") || (typeof window !== "undefined" && !!window.AndroidNative);
  const typeTag = isApk ? "APK" : "PWA";

  return {
    category,
    osName,
    typeTag,
    hostname: `${osName} ${category}`,
    os_info: `${osName} ${category} (${typeTag})`
  };
}

export function isInstalledApp() {
  if (typeof window === "undefined") return false;
  // 1. Android Native interface injected by MainActivity.java
  if (typeof window.AndroidNative !== "undefined" && window.AndroidNative != null) {
    if (document.documentElement) document.documentElement.classList.add("is-installed-apk");
    return true;
  }
  // 2. Explicit runtime flag
  if (window.IS_INSTALLED_APK === true) {
    if (document.documentElement) document.documentElement.classList.add("is-installed-apk");
    return true;
  }
  // 3. User agent inspection
  const ua = (navigator.userAgent || "").toLowerCase();
  if (ua.includes("com.jayraldines") || ua.includes("jayraldinesapk") || ua.includes("androidnative")) {
    if (document.documentElement) document.documentElement.classList.add("is-installed-apk");
    return true;
  }
  // 4. Android WebView asset loader origin or local file
  const loc = window.location;
  if (loc && (loc.hostname === "appassets.androidplatform.net" || loc.protocol === "file:")) {
    if (document.documentElement) document.documentElement.classList.add("is-installed-apk");
    return true;
  }
  // 5. Standalone display mode (installed PWA / WebAPK / home-screen standalone)
  if (typeof window.matchMedia === "function" && window.matchMedia("(display-mode: standalone)").matches) {
    if (document.documentElement) document.documentElement.classList.add("is-installed-apk");
    return true;
  }
  if (window.navigator && window.navigator.standalone === true) {
    if (document.documentElement) document.documentElement.classList.add("is-installed-apk");
    return true;
  }
  return false;
}

// Immediately evaluate and tag document element if running in installed app
if (typeof window !== "undefined") {
  isInstalledApp();
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
  const saved = (localStorage.getItem("jayraldines_lan_host") || "").trim();
  if (saved) return saved;
  if (typeof window !== "undefined" && window.location && window.location.hostname && !window.location.origin.startsWith("file:")) {
    return window.location.hostname;
  }
  return "";
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

async function _flushPendingMenuItemImageUploads(host, port = 8000) {
  const pending = repo.getPendingMenuItemImageUploads ? repo.getPendingMenuItemImageUploads() : [];
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
        const res = await fetch(`${base}/api/menu/image-upload`, {
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
            mi_id: Number(upload.mi_id),
            name: upload.item_name || "",
            image: upload.image_data || "",
            remove: Number(upload.remove_image || 0) === 1,
          }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.error) {
          throw new Error(data.error || data.detail || `Menu image upload failed with HTTP ${res.status}`);
        }

        repo.markMenuItemImageSynced(Number(upload.mi_id), data.mi_image || "", data.image || "");
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
      const msg = lastErr?.message || "Menu item image upload failed.";
      repo.markMenuItemImageUploadFailed(Number(upload.mi_id), msg);
      summary.failed++;
      summary.errors.push({ mi_id: Number(upload.mi_id), error: msg });
    }
  }

  return summary;
}

async function _proxyPackageWrite(method, path, body) {
  // Calls the REAL REST endpoints on the Central Server PC (port 8000)
  // so edits reach the Central DB server directly and immediately.
  try {
    let host = _getStoredSyncHost();
    if (!host) {
      host = await api.autoDiscoverServer().catch(() => "");
    }
    if (!host) {
      host = localStorage.getItem("jayraldines_lan_host") || localStorage.getItem("jayraldines_central_ip") || (typeof window !== "undefined" && window.location && window.location.hostname ? window.location.hostname : "192.168.1.10");
    }
    const baseUrls = _getSyncBaseUrls(host, 8000);
    if (!baseUrls.some(u => u.includes("192.168.1.10"))) {
      baseUrls.push("http://192.168.1.10:8000");
    }
    const dev = _getTabletDeviceInfo();
    for (const base of baseUrls) {
      try {
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 6000);
        const res = await fetch(`${base}${path}`, {
          method,
          headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "ngrok-skip-browser-warning": "69420",
            "X-Device-Id": dev.device_id,
            "X-Device-Host": dev.hostname,
            "X-Device-OS": dev.os_info,
          },
          body: body !== undefined ? JSON.stringify(body) : undefined,
          signal: controller.signal,
        });
        clearTimeout(tid);
        if (res.ok) {
          const data = await res.json().catch(() => ({}));
          if (data.version) {
            _knownServerDbVersion = Math.max(_knownServerDbVersion || 0, Number(data.version) || 0);
          }
          return true;
        }
      } catch (_) {}
    }
  } catch (_) {}
  return false;
}

async function _proxyServerWrite(sql, params = []) {
  try {
    const host = _getStoredSyncHost();
    if (!host) return false;
    const baseUrls = _getSyncBaseUrls(host, 8000);
    for (const base of baseUrls) {
      try {
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 5000);
        const res = await fetch(`${base}/api/db/write`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sql, params }),
          signal: controller.signal,
        });
        clearTimeout(tid);
        if (res.ok) {
          const data = await res.json().catch(() => ({}));
          if (data.version) {
            _knownServerDbVersion = Math.max(_knownServerDbVersion || 0, Number(data.version) || 0);
          }
          return true;
        }
      } catch (_) {}
    }
  } catch (_) {}
  return false;
}

export const api = {
  async health() { await ready(); return { status: "ok" }; },
  async terms() { await ready(); return termsMod.getTerms(); },

  isInstalledApp() {
    return isInstalledApp();
  },

  isLiveConnected() {
    return _liveDbConnected;
  },

  async ensureLiveConnection(force = false) {
    await ready();
    const now = Date.now();
    if (!force) {
      if (_liveDbConnected && (now - _lastSyncTimestamp < 15000)) {
        return true;
      }
      if (!_liveDbConnected && (now - _lastCheckAttempt < 12000)) {
        return false;
      }
    }
    if (_connectionCheckInFlight) return _connectionCheckInFlight;

    _lastCheckAttempt = now;
    _connectionCheckInFlight = (async () => {
      try {
        const savedHost = (localStorage.getItem("jayraldines_lan_host") || "").trim();
        const configuredPort = parseInt(localStorage.getItem("jayraldines_lan_port") || 8000, 10) || 8000;

        // 1. Check user-configured host first (highest priority)
        if (savedHost) {
          const stat = await api.checkLanStatus(savedHost, configuredPort);
          if (stat && stat.online && (stat.db_connected !== false)) {
            _liveDbConnected = true;
            _lastSyncTimestamp = Date.now();
            api.syncWithServer({ host: savedHost, port: configuredPort })
              .catch((e) => console.warn("[LiveDB] Background sync note:", e));
            window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: savedHost } }));
            return true;
          }
        }

        // 2. Check local/same-host backend on configuredPort (8000)
        let currentHost = "";
        if (typeof window !== "undefined" && window.location && window.location.hostname) {
          currentHost = window.location.hostname;
        }
        if (currentHost && currentHost !== savedHost) {
          const stat = await api.checkLanStatus(currentHost, configuredPort);
          if (stat && stat.online && (stat.db_connected !== false)) {
            _liveDbConnected = true;
            _lastSyncTimestamp = Date.now();
            if (!savedHost) {
              localStorage.setItem("jayraldines_lan_host", currentHost);
            }
            api.syncWithServer({ host: currentHost, port: configuredPort })
              .catch((e) => console.warn("[LiveDB] Background sync note:", e));
            window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: currentHost } }));
            return true;
          }
        }

        // 3. Discover server on LAN (if forced or not connected)
        const host = await api.autoDiscoverServer();
        if (host) {
          _liveDbConnected = true;
          _lastSyncTimestamp = Date.now();
          api.syncWithServer({ host, port: configuredPort })
            .catch((e) => console.warn("[LiveDB] Background sync note:", e));
          window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: true, server: host } }));
          return true;
        }
      } catch (err) {
        console.warn("[LiveDB] Connection check note:", err.message);
      } finally {
        _connectionCheckInFlight = null;
      }

      _liveDbConnected = false;
      window.dispatchEvent(new CustomEvent("jayraldines:live-status", { detail: { connected: false } }));
      return false;
    })();

    return _connectionCheckInFlight;
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

  async getPackageItems(pkgId) {
    await ready();
    return repo.getPackageItems(pkgId);
  },

  async getPackageBuckets(pkgId) {
    await ready();
    return repo.getPackageBuckets(pkgId);
  },

  // Authors a full package definition (package + default dishes + selection
  // buckets) on the Central Server. The server writes to Postgres and the
  // change flows back to every device on the next sync. Returns the server's
  // {ok, pkg_id, buckets, items} response, or throws if the server is unreachable.
  async definePackage({ package: pkg, items = [], buckets = [] } = {}) {
    await ready();
    const host = _getStoredSyncHost();
    if (!host) {
      throw new Error("Central Server host is not configured. Connect to the server, then try again.");
    }
    const baseUrls = _getSyncBaseUrls(host, 8000);
    let lastErr = null;
    for (const base of baseUrls) {
      try {
        const controller = new AbortController();
        const tid = setTimeout(() => controller.abort(), 15000);
        const res = await fetch(`${base}/api/packages/define`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "69420" },
          body: JSON.stringify({ package: pkg || {}, items: items || [], buckets: buckets || [] }),
          signal: controller.signal,
        });
        clearTimeout(tid);
        if (res.ok) {
          const data = await res.json().catch(() => ({}));
          if (data && data.version) {
            _knownServerDbVersion = Math.max(_knownServerDbVersion || 0, Number(data.version) || 0);
          }
          // Pull the authoritative catalog (incl. buckets) back down.
          api.syncWithServer().catch(() => {});
          return data;
        }
        const errData = await res.json().catch(() => ({}));
        lastErr = new Error(errData.error || `HTTP ${res.status}`);
      } catch (err) {
        lastErr = err;
      }
    }
    throw new Error(lastErr?.message || "Could not reach the Central Server to save this package.");
  },

  async createPackage(data) {
    await ready();
    const id = repo.addPackage(data.name, data.description, data.price_per_pax, data.min_pax, data.image);
    const imageChanged = Boolean(data.image_changed || data.imageChanged || data.image);
    if (imageChanged) {
      repo.queuePackageImageUpload(id, data.image || "", !data.image);
    }
    // Await the proxy write before triggering a sync — otherwise the sync's
    // pull-from-Postgres step can race ahead of this edit reaching the
    // kiosk server and pull back the stale price/name.
    await _proxyPackageWrite("POST", "/api/packages", {
      name: data.name, description: data.description || "",
      price_per_pax: data.price_per_pax != null ? Number(data.price_per_pax) : 0, min_pax: Number(data.min_pax) || 30,
    }).catch(() => {});
    api.autoSyncPendingRecords().catch((e) => console.warn("[LiveDB] Package upload queued:", e));
    return { id, image_sync: imageChanged ? "pending" : "none" };
  },
  async updatePackage(id, data) {
    await ready();
    const imageChanged = Boolean(data.image_changed || data.imageChanged);
    const ok = repo.updatePackage(id, data.name, data.description, data.price_per_pax, data.min_pax, imageChanged ? data.image : undefined);
    if (imageChanged) {
      repo.queuePackageImageUpload(id, data.image || "", !data.image);
    }
    // price_per_pax may legitimately be 0 (e.g. a free/promo package) — keep
    // that intact rather than letting `|| 0` mask a real value. Await this
    // before syncing so the sync's pull step doesn't race ahead of the edit
    // and pull back the stale price.
    await _proxyPackageWrite("PUT", `/api/packages/${id}`, {
      name: data.name, description: data.description || "",
      price_per_pax: data.price_per_pax != null ? Number(data.price_per_pax) : 0,
      min_pax: Number(data.min_pax) || 30,
    }).catch(() => {});
    api.autoSyncPendingRecords().catch((e) => console.warn("[LiveDB] Package update note:", e));
    return { ok, image_sync: imageChanged ? "pending" : "unchanged" };
  },
  async deletePackage(id) {
    await ready();
    repo.deletePackage(id);
    _proxyPackageWrite("DELETE", `/api/packages/${id}`).catch(() => {});
    return { ok: true };
  },

  // Landing Slider Images (Central Server Persistence)
  async getLandingSliderImages() {
    try {
      let host = _getStoredSyncHost();
      if (!host) host = await api.autoDiscoverServer().catch(() => "");
      if (!host) host = localStorage.getItem("jayraldines_lan_host") || localStorage.getItem("jayraldines_central_ip") || (typeof window !== "undefined" && window.location && window.location.hostname ? window.location.hostname : "192.168.1.10");
      const baseUrls = _getSyncBaseUrls(host, 8000);
      if (!baseUrls.some(u => u.includes("192.168.1.10"))) {
        baseUrls.push("http://192.168.1.10:8000");
      }
      for (const base of baseUrls) {
        try {
          const controller = new AbortController();
          const tid = setTimeout(() => controller.abort(), 4000);
          const res = await fetch(`${base}/api/landing/slider-images`, {
            headers: { Accept: "application/json", "ngrok-skip-browser-warning": "69420" },
            signal: controller.signal,
          });
          clearTimeout(tid);
          if (res.ok) {
            return await res.json();
          }
        } catch (_) {}
      }
    } catch (_) {}
    return null;
  },

  async saveLandingSliderImages(images, interval = 5000) {
    return _proxyPackageWrite("POST", "/api/landing/slider-images", {
      images: images || [],
      interval: interval || 5000,
    });
  },

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

  // Persists a new admin-defined category display order (drag-and-drop in
  // Settings > Menu Categories) locally, then pushes it to the Central
  // Server so the desktop app and every other tablet pick it up on their
  // next sync. Await the push before syncing — same race-avoidance
  // reasoning as package/menu-item edits.
  async reorderMenuCategories(orderedNames) {
    await ready();
    const ok = repo.reorderMenuCategories(orderedNames);
    let pushed = false;
    try {
      pushed = await _proxyPackageWrite("POST", "/api/menu-categories/reorder", {
        ordered_names: orderedNames || [],
      });
    } catch (_) {}
    api.autoSyncPendingRecords().catch(() => {});
    return { ok, pushed };
  },

  async createMenuItem(data) {
    await ready();
    const id = repo.addMenuItem(data.name, data.category, data.price, data.status, data.description, data.image);
    const imageChanged = Boolean(data.image_changed || data.imageChanged || data.image);
    if (imageChanged) {
      repo.queueMenuItemImageUpload(id, data.image || "", !data.image, data.name);
    }
    // Route through the real /api/menu-items REST endpoint (like packages),
    // not the never-implemented /api/db/write raw-SQL path — otherwise this
    // never reaches the kiosk server or syncs to Postgres/other devices.
    await _proxyPackageWrite("POST", "/api/menu-items", {
      name: data.name, category: data.category || "Main Dish",
      price: data.price != null ? Number(data.price) : 0,
      status: data.status || "Available", description: data.description || "",
    }).catch(() => {});
    api.autoSyncPendingRecords().catch((e) => console.warn("[LiveDB] Menu item upload queued:", e));
    return { id, image_sync: imageChanged ? "pending" : "none" };
  },
  async updateMenuItem(id, data) {
    await ready();
    const imageChanged = Boolean(data.image_changed || data.imageChanged);
    const ok = repo.updateMenuItem(id, data.name, data.category, data.price, data.status, data.description, imageChanged ? data.image : undefined);
    if (imageChanged) {
      repo.queueMenuItemImageUpload(id, data.image || "", !data.image, data.name);
    }
    // price may legitimately be 0 (e.g. a free/promo item) — keep that intact
    // rather than letting `|| 0` mask a real value. Await this before syncing
    // so the sync's pull step doesn't race ahead of the edit and pull back
    // the stale price. Uses the real /api/menu-items/{id} endpoint (like
    // packages), not the never-implemented /api/db/write raw-SQL path.
    await _proxyPackageWrite("PUT", `/api/menu-items/${id}`, {
      name: data.name, category: data.category || "Main Dish",
      price: data.price != null ? Number(data.price) : 0,
      status: data.status || "Available", description: data.description || "",
    }).catch(() => {});
    api.autoSyncPendingRecords().catch((e) => console.warn("[LiveDB] Menu item sync note:", e));
    return { ok, image_sync: imageChanged ? "pending" : "unchanged" };
  },
  async deleteMenuItem(id) {
    await ready();
    repo.deleteMenuItem(id);
    _proxyPackageWrite("DELETE", `/api/menu-items/${id}`).catch(() => {});
    return { ok: true };
  },

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
  async getBookingsByDate(dateStr) {
    await ready();
    const local = repo.getBookingsByDate(dateStr) || [];
    try {
      const host = _getStoredSyncHost();
      if (host) {
        const baseUrls = _getSyncBaseUrls(host, 8000);
        for (const base of baseUrls) {
          try {
            const controller = new AbortController();
            const tid = setTimeout(() => controller.abort(), 2500);
            const res = await fetch(`${base}/api/bookings/by-date?date=${encodeURIComponent(dateStr)}`, {
              signal: controller.signal
            });
            clearTimeout(tid);
            if (res.ok) {
              const rows = await res.json();
              if (Array.isArray(rows)) {
                const sMapped = rows.map(r => ({
                  id: r.id,
                  ref: r.ref,
                  customer: r.customer || "",
                  date: r.date,
                  time: repo.formatEventTime ? repo.formatEventTime(r.time) : (r.time || ""),
                  venue: r.venue || "",
                  occasion: r.occasion || "Event",
                  pax: Number(r.pax || 0),
                  status: r.status || "PENDING"
                }));
                const seen = new Set(local.map(l => l.ref || `${l.date}_${l.time}`));
                for (const sm of sMapped) {
                  const key = sm.ref || `${sm.date}_${sm.time}`;
                  if (!seen.has(key)) {
                    local.push(sm);
                    seen.add(key);
                  }
                }
                return local;
              }
            }
          } catch (_) {}
        }
      }
    } catch (_) {}
    return local;
  },

  async getMonthBookings(year, month) {
    await ready();
    const local = repo.getMonthBookings(year, month) || [];
    try {
      const host = _getStoredSyncHost();
      if (host) {
        const baseUrls = _getSyncBaseUrls(host, 8000);
        for (const base of baseUrls) {
          try {
            const controller = new AbortController();
            const tid = setTimeout(() => controller.abort(), 2500);
            const res = await fetch(`${base}/api/bookings/by-month?year=${encodeURIComponent(year)}&month=${encodeURIComponent(month)}`, {
              signal: controller.signal
            });
            clearTimeout(tid);
            if (res.ok) {
              const rows = await res.json();
              if (Array.isArray(rows)) {
                const sMapped = rows.map(r => ({
                  id: r.id,
                  ref: r.ref,
                  customer: r.customer || "",
                  date: r.date,
                  time: repo.formatEventTime ? repo.formatEventTime(r.time) : (r.time || ""),
                  venue: r.venue || "",
                  occasion: r.occasion || "Event",
                  pax: Number(r.pax || 0),
                  status: r.status || "PENDING"
                }));
                const seen = new Set(local.map(l => l.ref || `${l.date}_${l.time}`));
                for (const sm of sMapped) {
                  const key = sm.ref || `${sm.date}_${sm.time}`;
                  if (!seen.has(key)) {
                    local.push(sm);
                    seen.add(key);
                  }
                }
                return local;
              }
            }
          } catch (_) {}
        }
      }
    } catch (_) {}
    return local;
  },

  async placeOrder(data) {
    await ready();
    // 1. Always record order in local SQLite
    const res = repo.createOrder(data);

    // 2. Push to the central server immediately - this used to be a
    // fire-and-forget call whose result nobody looked at, so a booking
    // could silently sit unsynced (network hiccup, server briefly down)
    // with zero indication to the user beyond a generic "pending" count
    // buried in Settings. Now we wait for the result and report it back so
    // the caller can tell the user whether it actually reached the server.
    let synced = false;
    try {
      const syncResult = await api.autoSyncPendingRecords();
      synced = Boolean(syncResult);
    } catch (e) {
      console.warn("[LiveDB] Auto-sync scheduled for next reconnection:", e);
    }

    return { ...res, _synced: synced };
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
    // Every failure used to be swallowed identically ("Central Server
    // Unreachable", no detail) whether it was a real network timeout, a CORS
    // rejection, or a client-side exception thrown before any request even
    // went out (e.g. the past "non ISO-8859-1 code point" header bug) -
    // making it impossible to tell those apart from the UI alone. Capture
    // and surface the actual last error so the on-screen message (and
    // console) shows the real cause going forward.
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

          const sVer = Number(data.db_version ?? data.version ?? 0);
          if (sVer > 0) {
            if (_knownServerDbVersion === null) {
              _knownServerDbVersion = sVer;
            } else if (sVer > _knownServerDbVersion) {
              console.log(`[AutoSync] Server DB revision changed: ${_knownServerDbVersion} -> ${sVer}. Auto-syncing tablet...`);
              _knownServerDbVersion = sVer;
              api.syncWithServer({ host: base, port }).catch((e) => console.warn("[AutoSync] Background auto-sync failed:", e));
            }
          }

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
      const menuImageSync = await _flushPendingMenuItemImageUploads(host, port);
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

      const sVer = Number(res.version ?? res.db_version ?? 0);
      if (sVer > 0) {
        _knownServerDbVersion = Math.max(_knownServerDbVersion || 0, sVer);
      }

      if (res.packages || res.menu_items || res.customers || res.occasions || res.menu_categories) {
        repo.updateMasterDataFromSync(res.packages || [], res.menu_items || [], res.package_items || [], res.customers || [], res.occasions || [], res.package_buckets || [], res.menu_categories || []);
      }
      if (res.synced_booking_refs || res.synced_customer_names) {
        repo.markRecordsSynced(res.synced_booking_refs || [], res.synced_customer_names || []);
      }
      if (res.deleted_booking_refs && res.deleted_booking_refs.length > 0) {
        repo.purgeDeletedBookings(res.deleted_booking_refs);
      }

      const detail = {
        ...res,
        pushed_package_images: imageSync.synced,
        failed_package_images: imageSync.failed,
        package_image_errors: imageSync.errors,
        pushed_menu_images: menuImageSync.synced,
        failed_menu_images: menuImageSync.failed,
        menu_image_errors: menuImageSync.errors,
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
    if (_autoDiscoverInFlight) return _autoDiscoverInFlight;

    _autoDiscoverInFlight = (async () => {
      const port = parseInt(localStorage.getItem("jayraldines_lan_port") || 8000, 10) || 8000;
      const candidates = [];
      const savedHost = (localStorage.getItem("jayraldines_lan_host") || "").trim();
      if (savedHost) candidates.push(savedHost);

      // Local candidates on port 8000 (NEVER port 8080)
      if (typeof window !== "undefined" && window.location && window.location.hostname) {
        const h = window.location.hostname;
        if (!candidates.includes(h)) candidates.push(h);
      }
      if (!candidates.includes("127.0.0.1")) candidates.push("127.0.0.1");
      if (!candidates.includes("localhost")) candidates.push("localhost");

      const probe = async (target) => {
        try {
          const baseUrls = _getSyncBaseUrls(target, port);
          for (const base of baseUrls) {
            try {
              const controller = new AbortController();
              const tid = setTimeout(() => controller.abort(), 1200);
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

      // 1. Fast check of direct/local candidates (savedHost, current hostname, localhost)
      for (const c of candidates) {
        const found = await probe(c);
        if (found) {
          localStorage.setItem("jayraldines_lan_host", found);
          console.log(`[AutoDiscover] Connected to server at ${found}`);
          return found;
        }
      }

      // 2. Check local subnet only (do not scan random unrouted subnets simultaneously)
      let subnetPrefix = "192.168.1.";
      if (typeof window !== "undefined" && window.location && window.location.hostname) {
        const parts = window.location.hostname.split(".");
        if (parts.length === 4 && window.location.hostname.startsWith("192.168.")) {
          subnetPrefix = `${parts[0]}.${parts[1]}.${parts[2]}.`;
        }
      }

      const octets = [32, 34, 1, 10, 15, 20, 30, 40, 50, 100, 120, 128];
      const lanTargets = octets.map(o => `${subnetPrefix}${o}`).filter(ip => !candidates.includes(ip));

      // Batch scan in chunks of 4 with short timeout to prevent network saturation
      const chunkSize = 4;
      for (let i = 0; i < lanTargets.length; i += chunkSize) {
        const chunk = lanTargets.slice(i, i + chunkSize);
        const results = await Promise.allSettled(chunk.map(probe));
        for (const r of results) {
          if (r.status === "fulfilled" && r.value) {
            localStorage.setItem("jayraldines_lan_host", r.value);
            console.log(`[AutoDiscover] Successfully detected server at ${r.value}`);
            return r.value;
          }
        }
      }

      return savedHost || null;
    })();

    try {
      return await _autoDiscoverInFlight;
    } finally {
      _autoDiscoverInFlight = null;
    }
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
  const targetPort = parseInt(port, 10) || 8000;
  const webPort = (typeof window !== "undefined" && window.location && window.location.port) ? window.location.port : "8080";
  const trimmed = (host || "").trim();

  if (trimmed) {
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
      try {
        const parsed = new URL(trimmed);
        const isTunnel = parsed.hostname.includes(".ngrok") || parsed.hostname.includes(".trycloudflare.com") || parsed.hostname.includes(".loca.lt");
        if (isTunnel) {
          urls.push(`https://${parsed.host}`);
          return urls;
        }

        // If the URL port matches the web frontend port (e.g. 8080), rewrite to target sync port (8000)
        let effectivePort = parsed.port;
        if (!effectivePort || (effectivePort === webPort && webPort !== String(targetPort))) {
          effectivePort = targetPort;
        }
        const cleanUrl = `${parsed.protocol}//${parsed.hostname}:${effectivePort}`;
        if (!urls.includes(cleanUrl)) urls.push(cleanUrl);

        const directTarget = `${parsed.protocol}//${parsed.hostname}:${targetPort}`;
        if (!urls.includes(directTarget)) urls.push(directTarget);
        return urls;
      } catch (_) {
        const clean = trimmed.replace(/\/+$/, "");
        if (!urls.includes(clean)) urls.push(clean);
      }
    } else {
      const rawHost = trimmed.replace(/^https?:\/\//i, "").replace(/\/+$/, "");
      if (rawHost.includes(".ngrok") || rawHost.includes(".trycloudflare.com") || rawHost.includes(".loca.lt")) {
        urls.push(`https://${rawHost}`);
        return urls;
      }

      if (rawHost.includes(":")) {
        const [h, p] = rawHost.split(":");
        const effPort = (p === webPort && webPort !== String(targetPort)) ? targetPort : (parseInt(p, 10) || targetPort);
        urls.push(`http://${h}:${effPort}`);
        return urls;
      }

      urls.push(`http://${rawHost}:${targetPort}`);
      return urls;
    }
  }

  // Fallback when host is empty: use current hostname on target sync port (8000)
  const defaultHost = (typeof window !== "undefined" && window.location && window.location.hostname && !window.location.origin.startsWith("file:"))
    ? window.location.hostname
    : "127.0.0.1";
  const defaultTarget = `http://${defaultHost}:${targetPort}`;
  if (!urls.includes(defaultTarget)) urls.push(defaultTarget);

  // When running in a browser over HTTP/HTTPS, also allow the origin itself (port 8080) as a direct candidate
  if (typeof window !== "undefined" && window.location && window.location.origin && !window.location.origin.startsWith("file:")) {
    const originUrl = window.location.origin.replace(/\/+$/, "");
    if (!urls.includes(originUrl)) {
      urls.push(originUrl);
    }
  }

  // Always include direct localhost and 127.0.0.1 on target sync port (8000) for seamless local testing
  for (const lh of ["127.0.0.1", "localhost"]) {
    const localTarget = `http://${lh}:${targetPort}`;
    if (!urls.includes(localTarget)) urls.push(localTarget);
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

// Background device heartbeat to maintain live presence and auto-detect revision changes in real time
if (typeof window !== "undefined") {
  setInterval(async () => {
    try {
      const savedHost = (localStorage.getItem("jayraldines_lan_host") || "").trim();
      if (savedHost) {
        await api.checkLanStatus(savedHost, 8000);
      } else {
        await api.ensureLiveConnection().catch(() => {});
      }
    } catch (_) {}
  }, 3500);

  // Send immediate offline signal when user closes the app, closes tab, or navigates away
  const markOffline = () => {
    try {
      if (!_liveDbConnected) return;
      const dev = _getTabletDeviceInfo();
      const host = (localStorage.getItem("jayraldines_lan_host") || "").trim();
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
      if (_liveDbConnected) {
        const host = (localStorage.getItem("jayraldines_lan_host") || "").trim();
        if (host) api.checkLanStatus(host, 8000).catch(() => {});
      }
    }
  });
}
