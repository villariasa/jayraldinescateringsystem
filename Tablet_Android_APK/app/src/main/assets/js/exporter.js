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

export function exportOrderReceiptPdf(order, businessName = "Jayraldine's Catering Services", autoSave = false) {
  const jsPDFClass = (window.jspdf && (window.jspdf.jsPDF || window.jspdf)) || window.jsPDF;
  if (!jsPDFClass) {
    throw new Error("jsPDF library is not loaded.");
  }
  const doc = new jsPDFClass({ unit: "pt", format: "a4" });
  const marginX = 36;
  const contentW = 523; // 595 - 72
  const rightX = marginX + contentW; // 559
  const centerX = 297.64;

  // ──────────────────────────────────────────────────────────────────────────
  // HEADER (Top)
  // ──────────────────────────────────────────────────────────────────────────
  let y = 42;
  doc.setTextColor(225, 29, 72); // Red #E11D48
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text(businessName.toUpperCase(), centerX, y, { align: "center" });

  y += 17;
  doc.setTextColor(15, 23, 42); // Dark #0F172A
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text("BOOKING AGREEMENT", centerX, y, { align: "center" });
  doc.setDrawColor(15, 23, 42);
  doc.setLineWidth(0.8);
  doc.line(centerX - 75, y + 2, centerX + 75, y + 2);

  y += 15;
  const bookingRef = order.booking_ref || order.id || "—";
  const issueDate = order.created_at || new Date().toISOString().slice(0, 10);
  doc.setTextColor(100, 116, 139); // Slate #64748B
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.text(`Booking Ref: ${bookingRef}    ·    Date Issued: ${issueDate}`, centerX, y, { align: "center" });

  y += 8;
  doc.setDrawColor(226, 232, 240);
  doc.setLineWidth(0.7);
  doc.line(marginX, y, rightX, y);

  // ──────────────────────────────────────────────────────────────────────────
  // UPPER SECTION (THE ORDER / RECEIPT) - 2 Sub-Columns
  // ──────────────────────────────────────────────────────────────────────────
  const startOrderY = y + 14;
  const colGap = 16;
  const leftColW = 248;
  const rightColX = marginX + leftColW + colGap; // 300
  const rightColW = rightX - rightColX; // 259

  // Thin column separator
  doc.setDrawColor(241, 245, 249);
  doc.setLineWidth(0.5);
  doc.line(marginX + leftColW + (colGap / 2), startOrderY, marginX + leftColW + (colGap / 2), 435);

  // ── LEFT SUB-COLUMN: Customer, Event Details, Financials, Signatures ──
  let ly = startOrderY;
  const customerName = order.customer_name || order.customer || order.name || "—";
  const address = order.customer_address || order.address || order.venue || "—";
  const contact = order.contact || order.phone || "—";
  const eventDate = order.event_date || "—";
  const eventTime = order.event_time || "—";
  const venue = order.venue || "—";
  const occasion = order.occasion || "—";
  const motif = order.motif || order.color_theme || "Standard Motif";
  const pax = order.pax || 0;
  const pkgName = order.package_name || "Catering Package";

  function drawField(lbl, val, x, curY, lblW = 75, maxW = 170) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(71, 85, 105);
    doc.text(lbl, x, curY);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(15, 23, 42);
    const lines = doc.splitTextToSize(String(val || "—"), maxW);
    doc.text(lines[0], x + lblW, curY);
    return curY + 13;
  }

  ly = drawField("Name:", customerName, marginX, ly, 65, 180);
  ly = drawField("Address:", address, marginX, ly, 65, 180);
  ly = drawField("Contact #:", contact, marginX, ly, 65, 180);
  ly = drawField("Function Date:", `${eventDate}  (${eventTime})`, marginX, ly, 65, 180);
  ly = drawField("Venue:", venue, marginX, ly, 65, 180);
  ly = drawField("Occasion:", `${occasion}  ·  Motif: ${motif}`, marginX, ly, 65, 180);
  ly = drawField("No. of Pax:", `${pax} Guests  @ ${pkgName}`, marginX, ly, 65, 180);

  const notes = order.notes || order.special_instructions || "";
  if (notes) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(71, 85, 105);
    doc.text("Instructions:", marginX, ly);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(15, 23, 42);
    const nLines = doc.splitTextToSize(notes, 175);
    doc.text(nLines.slice(0, 2), marginX + 65, ly);
    ly += Math.min(nLines.length, 2) * 11 + 2;
  } else {
    ly += 4;
  }

  // Financial Breakdown Card (Left)
  ly += 4;
  const total = Number(order.total || 0);
  const paid = Number(order.paid || order.downpayment || 0);
  const balance = Number(order.balance ?? Math.max(0, total - paid));
  const status = String(order.status || (balance === 0 ? "PAID" : paid > 0 ? "PARTIAL" : "PENDING")).toUpperCase();

  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(226, 232, 240);
  doc.roundedRect(marginX, ly, leftColW, 58, 4, 4, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(71, 85, 105);
  doc.text("Total Amount:", marginX + 8, ly + 14);
  doc.setTextColor(15, 23, 42);
  doc.text(peso(total), marginX + leftColW - 8, ly + 14, { align: "right" });

  doc.setTextColor(71, 85, 105);
  doc.text("Downpayment:", marginX + 8, ly + 28);
  doc.setTextColor(22, 163, 74);
  doc.text(peso(paid), marginX + leftColW - 8, ly + 28, { align: "right" });

  doc.setTextColor(71, 85, 105);
  doc.text("Balance Due:", marginX + 8, ly + 42);
  doc.setTextColor(balance > 0 ? 225 : 22, balance > 0 ? 29 : 163, balance > 0 ? 72 : 74);
  doc.setFontSize(9);
  doc.text(peso(balance), marginX + leftColW - 8, ly + 42, { align: "right" });

  doc.setFontSize(7);
  doc.setTextColor(100, 116, 139);
  doc.text(`Status: ${status} · Mode: ${order.payment_method || "Cash"}`, marginX + 8, ly + 53);

  ly += 68;

  // Signatures (CONFORME & NOTED BY)
  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(15, 23, 42);
  doc.text("CONFORME:", marginX, ly);
  doc.setDrawColor(148, 163, 184);
  doc.line(marginX + 55, ly, marginX + 175, ly);
  doc.text("Date:", marginX + 182, ly);
  doc.line(marginX + 205, ly, marginX + leftColW, ly);

  ly += 11;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(6.5);
  doc.setTextColor(100, 116, 139);
  doc.text("Client Signature over Printed Name", marginX + 55, ly);

  ly += 16;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(7.5);
  doc.setTextColor(15, 23, 42);
  doc.text("NOTED BY:", marginX, ly);
  doc.line(marginX + 55, ly, marginX + 175, ly);
  doc.text("Date:", marginX + 182, ly);
  doc.line(marginX + 205, ly, marginX + leftColW, ly);

  ly += 11;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(6.5);
  doc.setTextColor(100, 116, 139);
  doc.text("Jayraldine's Catering Representative", marginX + 55, ly);

  // ── RIGHT SUB-COLUMN: Package, Itemized Menu, Add-ons ──
  let ry = startOrderY;

  // Package header badge
  doc.setFillColor(255, 241, 242); // Rose tint
  doc.setDrawColor(254, 205, 211);
  doc.roundedRect(rightColX, ry - 4, rightColW, 22, 3, 3, "FD");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.5);
  doc.setTextColor(190, 18, 60);
  doc.text(pkgName.toUpperCase(), rightColX + 8, ry + 8);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105);
  doc.text(`Good for ${pax} Guests`, rightX - 8, ry + 8, { align: "right" });

  ry += 28;

  // MENU:
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(15, 23, 42);
  doc.text("MENU:", rightColX, ry);
  doc.line(rightColX, ry + 2, rightColX + 38, ry + 2);

  ry += 13;
  const menuSelections = order.menu_selections || [];
  if (menuSelections.length > 0) {
    doc.setFontSize(8);
    const maxDishes = Math.min(menuSelections.length, 9);
    for (let i = 0; i < maxDishes; i++) {
      const item = menuSelections[i];
      const itemName = item.item_name || item.name || String(item);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(225, 29, 72);
      doc.text(`${i + 1}.`, rightColX + 2, ry);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(15, 23, 42);
      const dishLines = doc.splitTextToSize(itemName, rightColW - 20);
      doc.text(dishLines[0], rightColX + 18, ry);
      ry += 13;
    }
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(8);
    doc.setTextColor(100, 116, 139);
    doc.text("Standard Package Inclusions", rightColX + 8, ry);
    ry += 14;
  }

  // Add-ons & Extras
  const charges = order.additional_charges || [];
  if (charges.length > 0) {
    ry += 4;
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8.5);
    doc.setTextColor(15, 23, 42);
    doc.text("ADD-ONS & EXTRAS:", rightColX, ry);
    doc.line(rightColX, ry + 2, rightColX + 90, ry + 2);
    ry += 12;

    doc.setFontSize(7.5);
    const maxAddons = Math.min(charges.length, 4);
    for (let i = 0; i < maxAddons; i++) {
      const c = charges[i];
      const amt = Number(c.amount || c.ac_amount || 0);
      const amtStr = amt < 0 ? `- ${peso(Math.abs(amt))}` : peso(amt);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(15, 23, 42);
      const descLines = doc.splitTextToSize(`• ${c.description || c.ac_description || "Add-on"}`, rightColW - 75);
      doc.text(descLines[0], rightColX + 4, ry);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(amt < 0 ? 22 : 190, amt < 0 ? 163 : 18, amt < 0 ? 74 : 60);
      doc.text(amtStr, rightX, ry, { align: "right" });
      ry += 12;
    }
  }

  // ──────────────────────────────────────────────────────────────────────────
  // LOWER SECTION (TERMS AND CONDITIONS)
  // ──────────────────────────────────────────────────────────────────────────
  const termsY = 446;
  doc.setDrawColor(225, 29, 72);
  doc.setLineWidth(1.5);
  doc.line(marginX, termsY, rightX, termsY);

  let ty = termsY + 14;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9.5);
  doc.setTextColor(15, 23, 42);
  doc.text("Terms and Conditions", marginX, ty);

  ty += 12;
  const termsList = [
    "The client shall pay 50% downpayment upon reservation of booking and shall pay the full amount 3 days before the date of the event.",
    "Mode of payment. The client shall personally pay in Cash for the downpayment and full payment. If cash is not available, the client shall also pay through Bank Transfer or Gcash.",
    "Failure to pay. A failure to make payment according to the terms of the payment will be considered a cancellation of the event and the provisions for cancellation will apply: (15) days before the event - 20% charge, (7) days - 30%, (3) days - 50%.",
    "Any Food and Drinks or any consumables that is NOT prepared by JAY-RALDINE SERVICES brought by the client will FREE US ON ANY LIABILITIES due to food poisoning and spoilage. We charged Corkage Fee for bringing outside Food and Drinks. Precise time should be place in the BOOKING AGREEMENT and shall be strictly follow to avoid poisoning and spoilage."
  ];

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(51, 65, 85);

  for (const term of termsList) {
    doc.setFont("helvetica", "bold");
    doc.setTextColor(225, 29, 72);
    doc.text("•", marginX + 4, ty);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(51, 65, 85);
    const lines = doc.splitTextToSize(term, contentW - 20);
    doc.text(lines, marginX + 16, ty);
    ty += lines.length * 9.5 + 3.5;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // FOOTER CONTACT CALLOUT BOX
  // ──────────────────────────────────────────────────────────────────────────
  const footerBoxY = Math.max(ty + 6, 736);
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(203, 213, 225);
  doc.setLineWidth(0.8);
  doc.roundedRect(marginX, footerBoxY, contentW, 64, 4, 4, "FD");

  let fy = footerBoxY + 14;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(190, 18, 60);
  doc.text("WE INVITE YOU TO SEE HOW WE CAN HELP YOUR EVENT THE BEST IT CAN POSSIBLY BE!!!", centerX, fy, { align: "center" });

  fy += 12;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(30, 41, 59);
  doc.text("Located at 121 Katipunan St. Brgy Calamba Cebu City", centerX, fy, { align: "center" });

  fy += 11;
  doc.text("Please feel free to call us at (032) 255-3113, (032) 238-9417  ·  Globe 0917-6519555, 0917-1051528", centerX, fy, { align: "center" });

  fy += 11;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(2, 132, 199);
  doc.text("Find us on Facebook: Jayraldine's Catering Services", centerX, fy, { align: "center" });

  const filename = `Booking_Agreement_${order.booking_ref || order.id || "order"}.pdf`;
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
