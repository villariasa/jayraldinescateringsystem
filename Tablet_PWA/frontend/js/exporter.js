// Receipt PDF + orders Excel archive export, client-side. Ported from the
// original Tablet app's utils/exporter.py — jsPDF (window.jspdf.jsPDF)
// instead of reportlab, SheetJS (window.XLSX) instead of openpyxl.
import { fetchAll } from "./sqlite.js";
import { RECEIPT_LOGO_BASE64 } from "./receipt_logo_b64.js";

const RED = "#DC2626"; // Crimson Red #DC2626
const RED_DARK = "#BE123C";
const DARK = "#0F172A"; // Slate 900
const TEXT_MUTED = "#64748B"; // Slate 500
const TEXT_LABEL = "#334155"; // Slate 700
const BORDER_COLOR = "#CBD5E1"; // Slate 300
const BORDER_LIGHT = "#E2E8F0"; // Slate 200
const GREEN = "#16A34A"; // Emerald Green #16A34A

function peso(n) {
  return "PHP " + Number(n || 0).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDateIssued(dRaw) {
  if (!dRaw) {
    return new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  }
  try {
    const d = new Date(dRaw);
    if (isNaN(d.getTime())) return String(dRaw);
    return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  } catch (_) {
    return String(dRaw);
  }
}

// ── Native Vector Icon Helpers for PDF Rendering ─────────────────────────────
function drawUserIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.circle(x + 5, y + 4, 2.5, "F");
  doc.roundedRect(x + 1, y + 8, 8, 4, 2, 2, "F");
}

function drawCalendarIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.roundedRect(x + 1, y + 2, 8, 9, 1.5, 1.5, "F");
  doc.setFillColor(255, 255, 255);
  doc.rect(x + 2.5, y + 1, 1, 2.5, "F");
  doc.rect(x + 6.5, y + 1, 1, 2.5, "F");
  doc.rect(x + 2.5, y + 5.5, 1.5, 1.2, "F");
  doc.rect(x + 6, y + 5.5, 1.5, 1.2, "F");
  doc.rect(x + 2.5, y + 8, 1.5, 1.2, "F");
  doc.rect(x + 6, y + 8, 1.5, 1.2, "F");
}

function drawCoinsIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.ellipse(x + 5, y + 3.5, 4, 1.8, "F");
  doc.ellipse(x + 5, y + 6.5, 4, 1.8, "F");
  doc.ellipse(x + 5, y + 9.5, 4, 1.8, "F");
}

function drawClocheIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.circle(x + 5, y + 2, 1, "F");
  doc.roundedRect(x + 1, y + 3.5, 8, 5, 3.5, 3.5, "F");
  doc.roundedRect(x + 0.5, y + 8.5, 9, 1.5, 0.5, 0.5, "F");
}

function drawDocIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.roundedRect(x + 1, y + 1, 8, 10, 1, 1, "F");
  doc.setFillColor(255, 255, 255);
  doc.rect(x + 2.5, y + 3.5, 5, 1, "F");
  doc.rect(x + 2.5, y + 5.5, 5, 1, "F");
  doc.rect(x + 2.5, y + 7.5, 3.5, 1, "F");
}

function drawMegaphoneIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.triangle(x + 1, y + 5.5, x + 7, y + 2, x + 7, y + 9, "F");
  doc.rect(x + 7, y + 1.5, 1.5, 8, "F");
  doc.rect(x + 3.5, y + 6.5, 1.5, 3, "F");
}

function drawPinIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.circle(x + 3.5, y + 3.5, 2.5, "F");
  doc.triangle(x + 1.5, y + 4.5, x + 5.5, y + 4.5, x + 3.5, y + 8, "F");
  doc.setFillColor(255, 255, 255);
  doc.circle(x + 3.5, y + 3.5, 1, "F");
}

function drawPhoneIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.roundedRect(x + 1, y + 1, 6, 9, 1.2, 1.2, "F");
  doc.setFillColor(255, 255, 255);
  doc.rect(x + 2, y + 2.5, 4, 5, "F");
  doc.circle(x + 4, y + 8.5, 0.6, "F");
}

function drawFacebookIcon(doc, x, y) {
  doc.setFillColor(220, 38, 38);
  doc.roundedRect(x + 1, y + 1, 8, 8, 1.5, 1.5, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(7);
  doc.text("f", x + 4, y + 7);
  doc.setTextColor(30, 41, 59); // Restore text color immediately so subsequent text is dark!
}

function drawCard(doc, x, y, w, h, iconDrawer, titleText) {
  // Rounded card frame
  doc.setFillColor(255, 255, 255);
  doc.setDrawColor(203, 213, 225); // Slate 300
  doc.setLineWidth(0.75);
  doc.roundedRect(x, y, w, h, 4, 4, "FD");

  // Icon
  if (iconDrawer) {
    iconDrawer(doc, x + 8, y + 5);
  }

  // Header Title
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.5);
  doc.setTextColor(220, 38, 38); // Red 600
  doc.text(titleText, x + (iconDrawer ? 22 : 8), y + 13.5);

  // Divider line under header
  doc.setDrawColor(226, 232, 240); // Slate 200
  doc.setLineWidth(0.6);
  doc.line(x, y + 18, x + w, y + 18);
}

export function exportOrderReceiptPdf(order, businessName = "JAYRALDINE'S CATERING", autoSave = false) {
  const jsPDFClass = (window.jspdf && (window.jspdf.jsPDF || window.jspdf)) || window.jsPDF;
  if (!jsPDFClass) {
    throw new Error("jsPDF library is not loaded.");
  }
  const doc = new jsPDFClass({ unit: "pt", format: "a4" });
  const marginX = 30;
  const contentW = 535; // A4 width 595 - 60
  const rightX = marginX + contentW; // 565
  const centerX = 297.64;

  // ──────────────────────────────────────────────────────────────────────────
  // 1. TOP HEADER
  // ──────────────────────────────────────────────────────────────────────────
  const headerTopY = 22;
  const logoSize = 48; // STRICT 1:1 Aspect Ratio (Never stretched!)

  // Embed Logo (Square 1:1 ratio)
  if (RECEIPT_LOGO_BASE64) {
    try {
      doc.addImage(RECEIPT_LOGO_BASE64, "PNG", marginX, headerTopY, logoSize, logoSize);
    } catch (e) {
      console.warn("Logo render note:", e);
    }
  }

  // Red vertical divider line
  doc.setDrawColor(220, 38, 38); // Red #DC2626
  doc.setLineWidth(1.5);
  doc.line(marginX + logoSize + 10, headerTopY + 2, marginX + logoSize + 10, headerTopY + logoSize - 2);

  // Title: JAYRALDINE'S CATERING / BOOKING AGREEMENT
  const textLeftX = marginX + logoSize + 20;
  doc.setTextColor(220, 38, 38); // Red
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("JAYRALDINE'S CATERING", textLeftX, headerTopY + 20);

  doc.setTextColor(15, 23, 42); // Dark Charcoal / Navy #0F172A
  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  doc.text("BOOKING AGREEMENT", textLeftX, headerTopY + 38);

  // Right Side Header Metadata
  const bookingRef = order.booking_ref || (order.id ? `TB-${String(order.id).padStart(5, "0")}` : "TB-00001-69215");
  const dateIssued = formatDateIssued(order.created_at || order.bk_created_at);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(100, 116, 139); // Slate 500
  doc.text("ORDER REF:", rightX - 90, headerTopY + 18, { align: "right" });
  doc.setFont("helvetica", "bold");
  doc.setTextColor(15, 23, 42);
  doc.text(String(bookingRef), rightX, headerTopY + 18, { align: "right" });

  doc.setFont("helvetica", "normal");
  doc.setTextColor(100, 116, 139);
  doc.text("DATE ISSUED:", rightX - 90, headerTopY + 32, { align: "right" });
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  doc.text(String(dateIssued), rightX, headerTopY + 32, { align: "right" });

  // Full-width red horizontal bar across top section
  doc.setDrawColor(220, 38, 38);
  doc.setLineWidth(1.5);
  doc.line(marginX, headerTopY + logoSize + 8, rightX, headerTopY + logoSize + 8);

  // ──────────────────────────────────────────────────────────────────────────
  // 2. TWO-COLUMN MIDDLE SECTION
  // ──────────────────────────────────────────────────────────────────────────
  const startY = headerTopY + logoSize + 16; // ~86pt
  const colGap = 16;
  const leftColW = 258;
  const rightColX = marginX + leftColW + colGap; // 304
  const rightColW = rightX - rightColX; // 261

  const customerName = order.customer_name || order.customer || order.name || "aasdfasdf";
  const address = order.customer_address || order.address || order.venue || "street, Apas, Cebu City, Cebu";
  const contact = order.contact || order.phone || "09234234234";
  const eventDate = order.event_date || order.bk_event_date || "2026-10-21";
  let eventTime = order.event_time || order.bk_event_time || "6:00 PM";
  if (order.event_end_time || order.bk_event_end_time) {
    eventTime += ` - ${order.event_end_time || order.bk_event_end_time}`;
  }
  const venue = order.venue || order.bk_venue || address;
  const occasion = order.occasion || order.bk_occasion || "Birthday";
  const motif = order.motif || order.color_theme || order.bk_color_theme || "#2563EB";
  const pax = order.pax || order.bk_pax || 60;
  const instructions = order.notes || order.special_instructions || order.bk_notes || "Standard arrangement.";

  const total = Number(order.total || order.bk_total_amount || 0);
  const paid = Number(order.paid || order.downpayment || order.bk_down_payment || order.bk_amount_paid || 0);
  const balance = Number(order.balance ?? Math.max(0, total - paid));
  const payMode = order.payment_mode || order.payment_method || "Cash";
  const downpaymentStatus = (order.down_payment_status || order.bk_down_payment_status || (paid > 0 ? "PAID" : "PENDING")).toUpperCase();

  // ── LEFT COLUMN: Card 1 (Client Info), Card 2 (Event Details), Card 3 (Payment Details)
  // Card 1: CLIENT INFORMATION
  const card1H = 74;
  drawCard(doc, marginX, startY, leftColW, card1H, drawUserIcon, "CLIENT INFORMATION");
  let c1y = startY + 31;

  doc.setFontSize(8);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(51, 65, 85);
  doc.text("Name:", marginX + 8, c1y);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  doc.text(String(customerName), marginX + 65, c1y);

  c1y += 14;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(51, 65, 85);
  doc.text("Address:", marginX + 8, c1y);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  const addrLines = doc.splitTextToSize(String(address), leftColW - 72);
  doc.text(addrLines[0] || "", marginX + 65, c1y);

  c1y += 14;
  doc.setFont("helvetica", "bold");
  doc.setTextColor(51, 65, 85);
  doc.text("Contact #:", marginX + 8, c1y);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(15, 23, 42);
  doc.text(String(contact), marginX + 65, c1y);

  // Card 2: EVENT DETAILS
  const card2Y = startY + card1H + 8;
  const card2H = 142;
  drawCard(doc, marginX, card2Y, leftColW, card2H, drawCalendarIcon, "EVENT DETAILS");
  let c2y = card2Y + 30;

  function drawFieldRow(lbl, val) {
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.setTextColor(51, 65, 85);
    doc.text(lbl, marginX + 8, c2y);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(15, 23, 42);
    const lines = doc.splitTextToSize(String(val || "—"), leftColW - 104);
    doc.text(lines[0] || "", marginX + 96, c2y);
    c2y += 14;
  }

  drawFieldRow("Function Date:", eventDate);
  drawFieldRow("Time:", eventTime);
  drawFieldRow("Venue:", venue);
  drawFieldRow("Occasion:", occasion);
  drawFieldRow("Motif:", motif);
  drawFieldRow("No. of Pax:", `${pax} pax / sets`);
  drawFieldRow("Special Instructions:", instructions);

  // Card 3: PAYMENT DETAILS
  const card3Y = card2Y + card2H + 8;
  const card3H = 86;
  drawCard(doc, marginX, card3Y, leftColW, card3H, drawCoinsIcon, "PAYMENT DETAILS");
  let c3y = card3Y + 31;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(15, 23, 42);
  doc.text("Total Amount:", marginX + 8, c3y);
  doc.text(peso(total), marginX + leftColW - 8, c3y, { align: "right" });

  c3y += 14;
  doc.text("Downpayment:", marginX + 8, c3y);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(22, 163, 74); // Green
  doc.text(`${peso(paid)} (${payMode} - ${downpaymentStatus})`, marginX + leftColW - 8, c3y, { align: "right" });

  // Balance Due pink highlight row
  c3y += 10;
  doc.setFillColor(255, 241, 242); // Rose 50
  doc.setDrawColor(254, 205, 211); // Rose 200
  doc.setLineWidth(0.6);
  doc.roundedRect(marginX + 2, c3y, leftColW - 4, 24, 3, 3, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.5);
  doc.setTextColor(220, 38, 38);
  doc.text("Balance Due:", marginX + 8, c3y + 15);
  doc.setFontSize(9);
  doc.text(peso(balance), marginX + leftColW - 8, c3y + 15, { align: "right" });

  // ── RIGHT COLUMN: Card 4 (PACKAGE & MENU)
  const card4H = 310; // Exactly matches 74 + 8 + 142 + 8 + 86 = 318
  drawCard(doc, rightColX, startY, rightColW, card4H, drawClocheIcon, "PACKAGE & MENU");
  let rY = startY + 31;

  const pkgName = order.package_name || order.bk_package_name || "CUSTOM PACKAGE";
  const baseTotal = Number(order.base_total || order.bk_base_total || total);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.setTextColor(190, 18, 60); // Red / Rose 700
  doc.text(`PACKAGE: ${String(pkgName).toUpperCase()}`, rightColX + 8, rY);

  rY += 12;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.setTextColor(71, 85, 105);
  doc.text(`Good for ${pax} person(s)   ·   Base: ${peso(baseTotal)}`, rightColX + 8, rY);

  rY += 16;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text("MENU:", rightColX + 8, rY);

  rY += 13;
  const menuSelections = order.menu_selections || order.menu_items || [];
  if (menuSelections && menuSelections.length > 0) {
    doc.setFontSize(7.8);
    const maxItems = Math.min(menuSelections.length, 9);
    for (let i = 0; i < maxItems; i++) {
      const itm = menuSelections[i];
      const itmName = itm.item_name || itm.name || String(itm);
      const cat = itm.category || itm.mi_category || "";
      const catText = cat ? ` (${cat})` : "";

      doc.setFont("helvetica", "normal");
      doc.setTextColor(15, 23, 42);
      doc.text(`${i + 1}.`, rightColX + 8, rY);

      const fullText = `${itmName}${catText}`;
      const lines = doc.splitTextToSize(fullText, rightColW - 24);
      doc.text(lines[0] || "", rightColX + 20, rY);
      rY += 12;
    }
  } else {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(7.5);
    doc.setTextColor(100, 116, 139);
    doc.text("Standard package inclusions.", rightColX + 20, rY);
    rY += 13;
  }

  // ADD-ONS & EXTRAS
  const charges = order.additional_charges || [];
  rY = Math.max(rY + 4, startY + 265);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.5);
  doc.setTextColor(15, 23, 42);
  doc.text("ADD-ONS & EXTRAS:", rightColX + 8, rY);

  rY += 13;
  if (charges && charges.length > 0) {
    doc.setFontSize(8);
    const maxCharges = Math.min(charges.length, 3);
    for (let i = 0; i < maxCharges; i++) {
      const c = charges[i];
      const desc = c.description || c.ac_description || "Add-on Extra";
      const amt = Number(c.amount || c.ac_amount || 0);
      const amtStr = amt >= 0 ? `+${peso(amt)}` : `-${peso(Math.abs(amt))}`;

      doc.setFont("helvetica", "normal");
      doc.setTextColor(15, 23, 42);
      doc.text(`• ${desc}:`, rightColX + 8, rY);
      doc.setFont("helvetica", "bold");
      doc.text(amtStr, rightColX + rightColW - 8, rY, { align: "right" });
      rY += 12;
    }
  } else {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7.5);
    doc.setTextColor(100, 116, 139);
    doc.text("• None specified.", rightColX + 8, rY);
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 3. SIGNATURES (CONFORME & NOTED BY)
  // ──────────────────────────────────────────────────────────────────────────
  const sigY = startY + card4H + 16; // ~420pt
  const sigCol1End = marginX + 310;
  const dateLabelX = marginX + 335;
  const dateLineEnd = rightX - 10;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(15, 23, 42);

  doc.text("CONFORME:", marginX, sigY);
  doc.setDrawColor(148, 163, 184); // Slate 400
  doc.setLineWidth(0.6);
  doc.line(marginX + 62, sigY, sigCol1End, sigY);
  doc.text("Date:", dateLabelX, sigY);
  doc.line(dateLabelX + 26, sigY, dateLineEnd, sigY);

  const sig2Y = sigY + 18;
  doc.text("NOTED BY:", marginX, sig2Y);
  doc.line(marginX + 62, sig2Y, sigCol1End, sig2Y);
  doc.text("Date:", dateLabelX, sig2Y);
  doc.line(dateLabelX + 26, sig2Y, dateLineEnd, sig2Y);

  // ──────────────────────────────────────────────────────────────────────────
  // 4. TERMS AND CONDITIONS CARD
  // ──────────────────────────────────────────────────────────────────────────
  const termsY = sig2Y + 14; // ~452pt
  const termsH = 148;
  drawCard(doc, marginX, termsY, contentW, termsH, drawDocIcon, "TERMS AND CONDITIONS");

  let tY = termsY + 28;
  const termsList = [
    {
      bullet: "The client shall pay 50% downpayment upon reservation of booking and shall pay the full amount 3 days before the date of the event."
    },
    {
      bullet: "Mode of payment. The client shall personally pay in Cash for the downpayment and full payment. If cash is not available, the client can also pay through Bank Transfer or Gcash."
    },
    {
      bullet: "Failure to pay. A failure to make payment according to the terms of the payment will be considered a cancellation of the event and the provisions for cancellation will apply. (15) days before the event - 20% charge, (7) days - 30%, (3) days - 50%."
    },
    {
      bullet: "Consider Food and Liabilities. Any Food and Drinks or any consumables that is NOT prepared by JAYRALDINE SERVICES brought by the client will FREE US ON ANY LIABILITIES due to food poisoning and spoilage. We charge Corkage Fee for bringing outside Food and Drinks. Precise time should be placed in the BOOKING AGREEMENT and shall be strictly follow to avoid poisoning and spoilage."
    }
  ];

  doc.setFontSize(7.5);
  for (const item of termsList) {
    doc.setFont("helvetica", "bold");
    doc.setTextColor(220, 38, 38);
    doc.text("•", marginX + 8, tY);

    doc.setFont("helvetica", "normal");
    doc.setTextColor(30, 41, 59); // Slate 800
    const lines = doc.splitTextToSize(item.bullet, contentW - 24);
    doc.text(lines, marginX + 18, tY);
    tY += lines.length * 9.5 + 4;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // 5. FOOTER BANNER
  // ──────────────────────────────────────────────────────────────────────────
  const footerDividerY = termsY + termsH + 12;
  doc.setDrawColor(220, 38, 38);
  doc.setLineWidth(1.2);
  doc.line(marginX, footerDividerY, rightX, footerDividerY);

  let fY = footerDividerY + 12;
  drawMegaphoneIcon(doc, centerX - 188, fY - 7);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.setTextColor(220, 38, 38); // Red
  doc.text("WE INVITE YOU TO SEE HOW WE CAN HELP YOUR EVENT; THE BEST IT CAN POSSIBLY BE!!!", centerX + 6, fY, { align: "center" });

  fY += 12;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.5);
  doc.setTextColor(30, 41, 59);
  doc.text("Located at 518 Y Rama Ave., Cebu City", centerX, fY, { align: "center" });

  fY += 10;
  doc.text("Please feel free to call us at +63 912 345 6789", centerX, fY, { align: "center" });

  fY += 10;
  doc.text("Find us on Facebook: Jayraldine's Catering Services", centerX, fY, { align: "center" });

  // Bottom 3-item bar with red separator lines
  fY += 14;
  const col1W = 165;
  const col2W = 175;
  const col3W = contentW - col1W - col2W; // 195

  // Item 1: Address
  drawPinIcon(doc, marginX + 2, fY - 7);
  doc.setFontSize(6.8);
  doc.setTextColor(30, 41, 59);
  doc.text("Located at 518 Y Rama Ave., Cebu City", marginX + 13, fY);

  // Divider 1
  doc.setDrawColor(220, 38, 38);
  doc.setLineWidth(1);
  doc.line(marginX + col1W, fY - 7, marginX + col1W, fY + 2);

  // Item 2: Phone
  drawPhoneIcon(doc, marginX + col1W + 6, fY - 7);
  doc.setTextColor(30, 41, 59);
  doc.text("Please feel free to call us at +63 912 345 6789", marginX + col1W + 18, fY);

  // Divider 2
  doc.line(marginX + col1W + col2W, fY - 7, marginX + col1W + col2W, fY + 2);

  // Item 3: Facebook
  drawFacebookIcon(doc, marginX + col1W + col2W + 6, fY - 7);
  doc.setTextColor(30, 41, 59); // Explicitly ensure dark text color!
  doc.text("Find us on Facebook: Jayraldine's Catering Services", marginX + col1W + col2W + 18, fY);

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

  window.XLSX.writeFile(wb, `orders_archive_${new Date().toISOString().slice(0, 10)}.xlsx`);
}
