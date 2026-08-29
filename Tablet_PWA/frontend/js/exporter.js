// Receipt PDF + orders Excel archive export, client-side. Ported from the
// original Tablet app's utils/exporter.py — jsPDF (window.jspdf.jsPDF)
// instead of reportlab, SheetJS (window.XLSX) instead of openpyxl.
import { fetchAll } from "./sqlite.js";

const RED = "#E11D48";
const DARK = "#0B1220";
const GRAY = "#6B7280";
const GREEN = "#22C55E";
const AMBER = "#F59E0B";
const DANGER = "#EF4444";

function peso(n) {
  return "PHP " + Number(n || 0).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function exportOrderReceiptPdf(order, businessName = "Jayraldine's Catering", autoSave = false) {
  const jsPDFClass = (window.jspdf && (window.jspdf.jsPDF || window.jspdf)) || window.jsPDF;
  if (!jsPDFClass) {
    throw new Error("jsPDF library is not loaded.");
  }
  const doc = new jsPDFClass({ unit: "pt", format: "a4" });
  const marginX = 42;
  let y = 50;

  doc.setTextColor(RED);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text(businessName, marginX, y);
  y += 16;
  doc.setTextColor(GRAY);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text("Order Receipt (Kiosk PWA)", marginX, y);
  y += 10;
  doc.setDrawColor(RED);
  doc.setLineWidth(2);
  doc.line(marginX, y, 553, y);
  y += 20;

  const infoRows = [
    ["Order Ref", order.booking_ref || "—"],
    ["Customer", order.customer_name || "—"],
    ["Event Date", order.event_date || "—"],
    ["Venue / Occasion", `${order.venue || "—"} / ${order.occasion || "—"}`],
    ["Guests", String(order.pax ?? "—")],
  ];
  doc.setFontSize(9.5);
  for (const [label, value] of infoRows) {
    doc.setTextColor(GRAY);
    doc.setFont("helvetica", "bold");
    doc.text(label, marginX, y);
    doc.setTextColor(DARK);
    doc.setFont("helvetica", "normal");
    doc.text(String(value), marginX + 110, y);
    y += 16;
  }
  y += 8;

  const menuSelections = order.menu_selections || [];
  if (menuSelections.length) {
    doc.setTextColor(GRAY);
    doc.setFont("helvetica", "bold");
    doc.text("Selected Menu", marginX, y);
    y += 14;
    doc.setFont("helvetica", "normal");
    doc.setTextColor(DARK);
    for (const m of menuSelections) {
      doc.text(`${m.category || ""} — ${m.item_name || ""}`, marginX, y);
      y += 14;
    }
    y += 6;
  }

  const charges = order.additional_charges || [];
  if (charges.length) {
    doc.setTextColor(GRAY);
    doc.setFont("helvetica", "bold");
    doc.text("Additional Charges / Discounts", marginX, y);
    y += 14;
    doc.setFont("helvetica", "normal");
    for (const c of charges) {
      const amt = Number(c.amount);
      const amtText = amt < 0 ? `- ${peso(Math.abs(amt))}` : peso(amt);
      doc.setTextColor(DARK);
      doc.text(String(c.description), marginX, y);
      doc.text(amtText, 470, y, { align: "right" });
      y += 14;
    }
    y += 6;
  }

  const total = Number(order.total || 0);
  const paid = Number(order.paid || 0);
  const balance = Number(order.balance ?? Math.max(0, total - paid));
  const status = order.status || "Unpaid";
  const statusColor = status === "Paid" ? GREEN : status === "Partial" ? AMBER : DANGER;

  y += 6;
  doc.setDrawColor(220, 220, 220);
  doc.setLineWidth(0.5);
  doc.line(marginX, y, 553, y);
  y += 20;

  doc.setTextColor(GRAY);
  doc.setFont("helvetica", "bold");
  doc.text("Total Amount", marginX, y);
  doc.setTextColor(DARK);
  doc.setFont("helvetica", "normal");
  doc.text(peso(total), 470, y, { align: "right" });
  y += 16;

  doc.setTextColor(GRAY);
  doc.setFont("helvetica", "bold");
  doc.text("Amount Paid", marginX, y);
  doc.setTextColor(GREEN);
  doc.text(peso(paid), 470, y, { align: "right" });
  y += 18;

  doc.setTextColor(DARK);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("Remaining Balance", marginX, y);
  doc.setTextColor(balance > 0 ? DANGER : GREEN);
  doc.setFontSize(13);
  doc.text(peso(balance), 470, y, { align: "right" });
  y += 20;

  doc.setFontSize(10.5);
  doc.setTextColor(GRAY);
  doc.text("Payment Status", marginX, y);
  doc.setTextColor(statusColor);
  doc.text(status.toUpperCase(), 470, y, { align: "right" });
  y += 30;

  doc.setDrawColor(220, 220, 220);
  doc.line(marginX, y, 553, y);
  y += 16;
  doc.setFontSize(7.5);
  doc.setTextColor(GRAY);
  doc.setFont("helvetica", "normal");
  const printed = new Date().toLocaleString("en-US", { month: "long", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
  doc.text(`Printed: ${printed} · Thank you for choosing ${businessName}!`, 297, y, { align: "center" });

  const filename = `receipt_${order.booking_ref || order.id || "order"}.pdf`;
  if (autoSave) {
    try {
      doc.save(filename);
    } catch (e) {
      console.warn("doc.save fallback:", e);
    }
  }

  return doc.output("blob");
}

export function exportAllOrdersToExcel() {
  const bookings = fetchAll(`
    SELECT b.*, i.inv_id, i.inv_invoice_number, i.inv_total_amount, i.inv_amount_paid, i.inv_balance, i.inv_status
    FROM bookings b LEFT JOIN invoices i ON i.inv_booking_id = b.bk_id
    ORDER BY b.bk_created_at DESC
  `);

  const orderHeaders = [
    "Booking Ref", "Customer Name", "Contact Number", "Email Address", "Delivery / Billing Address",
    "Event Date", "Event Time", "Venue", "Occasion", "Pax", "Package",
    "Base Total (PHP)", "Total Amount (PHP)", "Amount Paid (PHP)", "Balance Due (PHP)",
    "Status", "Payment Mode", "Date Created", "Notes",
  ];
  const orderRows = bookings.map((b) => [
    b.bk_booking_ref || `TB-${String(b.bk_id).padStart(5, "0")}`,
    b.bk_customer_name || "", b.bk_contact || "", b.bk_email || "", b.bk_address || "",
    b.bk_event_date || "", b.bk_event_time || "", b.bk_venue || "", b.bk_occasion || "", b.bk_pax || 0,
    b.bk_package_name || "Custom Package",
    Number(b.bk_base_total || 0), Number(b.bk_total_amount || 0),
    Number(b.inv_amount_paid || b.bk_amount_paid || 0), Number(b.inv_balance || 0),
    b.inv_status || b.bk_status || "PENDING", b.bk_payment_mode || "Cash", b.bk_created_at || "", b.bk_notes || "",
  ]);

  const menuItems = fetchAll(`
    SELECT bmi.*, b.bk_booking_ref, b.bk_customer_name FROM booking_menu_items bmi
    JOIN bookings b ON b.bk_id = bmi.bmi_booking_id ORDER BY b.bk_id, bmi.bmi_category
  `);
  const menuRows = menuItems.map((m) => [m.bk_booking_ref || "", m.bk_customer_name || "", m.bmi_item_name || "", m.bmi_category || "", m.bmi_quantity || 1, Number(m.bmi_price || 0)]);

  const charges = fetchAll(`
    SELECT ac.*, b.bk_booking_ref, b.bk_customer_name FROM booking_additional_charges ac
    JOIN bookings b ON b.bk_id = ac.ac_booking_id ORDER BY b.bk_id, ac.ac_date_added
  `);
  const chargeRows = charges.map((c) => [c.bk_booking_ref || "", c.bk_customer_name || "", c.ac_description || "", Number(c.ac_amount || 0), c.ac_date_added || "", c.ac_added_by || "Staff"]);

  const payments = fetchAll(`
    SELECT pr.*, i.inv_invoice_number, b.bk_booking_ref, b.bk_customer_name FROM payment_records pr
    JOIN invoices i ON i.inv_id = pr.pr_invoice_id
    JOIN bookings b ON b.bk_id = i.inv_booking_id ORDER BY pr.pr_payment_date DESC
  `);
  const paymentRows = payments.map((p) => [
    p.bk_booking_ref || "", p.bk_customer_name || "", p.inv_invoice_number || "", Number(p.pr_amount || 0),
    p.pr_payment_date || "", p.pr_payment_method || p.pr_method || "Cash",
    p.pr_is_downpayment ? "Yes" : "No", p.pr_notes || p.pr_note || "",
  ]);

  const wb = window.XLSX.utils.book_new();
  const wsOrders = window.XLSX.utils.aoa_to_sheet([
    ["JAYRALDINE'S CATERING — KIOSK ORDERS ARCHIVE"],
    [`Export Date & Time: ${new Date().toLocaleString()}`],
    [],
    orderHeaders,
    ...orderRows,
  ]);
  window.XLSX.utils.book_append_sheet(wb, wsOrders, "Orders Summary");
  window.XLSX.utils.book_append_sheet(wb, window.XLSX.utils.aoa_to_sheet([["Booking Ref", "Customer Name", "Dish Name", "Category", "Quantity", "Extra Price (PHP)"], ...menuRows]), "Menu Selections");
  window.XLSX.utils.book_append_sheet(wb, window.XLSX.utils.aoa_to_sheet([["Booking Ref", "Customer Name", "Charge Description", "Amount (PHP)", "Date Added", "Added By"], ...chargeRows]), "Additional Charges");
  window.XLSX.utils.book_append_sheet(wb, window.XLSX.utils.aoa_to_sheet([["Booking Ref", "Customer Name", "Invoice Ref", "Payment Amount (PHP)", "Payment Date", "Payment Method", "Is Downpayment", "Notes"], ...paymentRows]), "Payment Records");

  const out = window.XLSX.write(wb, { type: "array", bookType: "xlsx" });
  return { blob: new Blob([out], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }), ordersCount: bookings.length };
}
