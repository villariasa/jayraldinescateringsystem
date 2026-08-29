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
  async createCustomer(data) { await ready(); return { id: repo.addCustomer(data.name, data.contact, data.email, data.address) }; },
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
  async placeOrder(data) { await ready(); return repo.createOrder(data); },

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
};

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
