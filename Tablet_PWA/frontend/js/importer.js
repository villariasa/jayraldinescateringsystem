// Master-data import (PC -> tablet) + template generation, client-side.
// Ported from the original Tablet app's utils/importer.py, using the
// vendored SheetJS (window.XLSX) for .xlsx instead of openpyxl.
import { replaceMasterTables, importMasterDataFromDbBytes, fetchOne } from "./sqlite.js";

export async function importMasterData(file) {
  const name = (file.name || "").toLowerCase();
  const bytes = await file.arrayBuffer();
  if (name.endsWith(".xlsx") || name.endsWith(".xlsm")) {
    return importMasterDataExcel(bytes);
  }
  return importMasterDataFromDbBytes(bytes);
}

function sheetRows(wb, sheetName) {
  if (!wb.SheetNames.includes(sheetName)) return [];
  const ws = wb.Sheets[sheetName];
  const rows = window.XLSX.utils.sheet_to_json(ws, { header: 1, defval: null });
  if (!rows.length) return [];
  const headers = rows[0].map((h) => String(h || "").trim().toLowerCase());
  const out = [];
  for (const r of rows.slice(1)) {
    if (!r.some((v) => v !== null && v !== "")) continue;
    const obj = {};
    headers.forEach((h, i) => { obj[h] = r[i]; });
    out.push(obj);
  }
  return out;
}

function importMasterDataExcel(bytes) {
  const wb = window.XLSX.read(bytes, { type: "array" });
  if (!wb.SheetNames.includes("Packages")) {
    throw new Error("Excel file is missing a 'Packages' sheet. Use the sample template.");
  }

  const pkgRows = sheetRows(wb, "Packages");
  const packages = pkgRows
    .filter((r) => r["package name"])
    .map((r) => ({ name: r["package name"], description: r["description"], price_per_pax: r["price per pax"], min_pax: r["min pax"] }));

  const itemRows = sheetRows(wb, "Menu Items");
  const menuItems = [];
  const packageItems = [];
  const seen = new Set();
  for (const r of itemRows) {
    const itemName = r["item name"];
    if (!itemName) continue;
    const category = r["category"] || "Other";
    const price = r["extra price"] || 0;
    const pkgName = r["package name"];
    const key = `${String(itemName).trim().toLowerCase()}|${String(category).trim().toLowerCase()}`;
    if (!seen.has(key)) {
      menuItems.push({ name: itemName, category, price, status: "Available", description: "" });
      seen.add(key);
    }
    if (pkgName) {
      packageItems.push({ package_name: pkgName, category, item_name: itemName, price, quantity: r["quantity"] || 1 });
    }
  }

  if (!packages.length) throw new Error("No packages found in the 'Packages' sheet.");
  return replaceMasterTables({ packages, menuItems, packageItems });
}

export function generateSampleExcelTemplate() {
  const wbPkg = [
    ["Package Name", "Description", "Price Per Pax", "Min Pax"],
    ["Classic Celebration Package", "Standard buffet with 4 main dishes, rice, dessert, drinks", 350.0, 30],
    ["Premium Grand Feast", "Deluxe buffet with 6 main dishes, lechon belly, 2 desserts", 550.0, 50],
  ];
  const wbItems = [
    ["Package Name", "Category", "Item Name", "Extra Price", "Quantity"],
    ["Classic Celebration Package", "Main Dish", "Chicken BBQ", 0, 1],
    ["Classic Celebration Package", "Main Dish", "Pork Adobo", 0, 1],
    ["Classic Celebration Package", "Rice", "Steamed Rice", 0, 1],
    ["Premium Grand Feast", "Main Dish", "Lechon Belly", 0, 1],
    ["", "Add-on", "Additional Lechon (standalone item, no package)", 2500, 1],
  ];
  const wb = window.XLSX.utils.book_new();
  window.XLSX.utils.book_append_sheet(wb, window.XLSX.utils.aoa_to_sheet(wbPkg), "Packages");
  window.XLSX.utils.book_append_sheet(wb, window.XLSX.utils.aoa_to_sheet(wbItems), "Menu Items");
  const out = window.XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

export function getLastMasterSync() {
  return fetchOne("SELECT * FROM tablet_master_sync ORDER BY tms_id DESC LIMIT 1");
}
