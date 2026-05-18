const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, VerticalAlign, PageNumber, PageBreak, LevelFormat,
  TableOfContents
} = require('docx');
const fs = require('fs');

// ── helpers ─────────────────────────────────────────────────────────────────
const CONTENT_W = 9360; // US Letter 8.5" - 2×1" margins  (DXA)

const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

const hdrBorder = { style: BorderStyle.SINGLE, size: 12, color: "2E75B6" };

function p(text, opts = {}) {
  return new Paragraph({
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { before: opts.before ?? 120, after: opts.after ?? 120, line: opts.line ?? 276 },
    children: [new TextRun({
      text,
      bold: opts.bold || false,
      italics: opts.italic || false,
      size: opts.size || 24,
      font: "Arial",
      color: opts.color || "000000",
    })],
    indent: opts.indent ? { left: opts.indent } : undefined,
    numbering: opts.numbering || undefined,
  });
}

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, size: 32, font: "Arial", color: "1F4E79" })],
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, bold: true, size: 28, font: "Arial", color: "2E75B6" })],
  });
}

function heading3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, bold: true, size: 26, font: "Arial", color: "2E75B6" })],
  });
}

function spacer(n = 1) {
  return Array.from({ length: n }, () =>
    new Paragraph({ children: [new TextRun("")], spacing: { before: 0, after: 60 } })
  );
}

function imagePlaceholder(caption) {
  // Gray box as placeholder + caption below
  const labelRow = new TableRow({
    children: [new TableCell({
      borders: { top: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" },
                 bottom: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" },
                 left: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" },
                 right: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" } },
      shading: { fill: "D9D9D9", type: ShadingType.CLEAR },
      width: { size: CONTENT_W, type: WidthType.DXA },
      margins: { top: 200, bottom: 200, left: 240, right: 240 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 0, after: 0 },
        children: [new TextRun({ text: `[ INSERT IMAGE HERE ]`, bold: true, size: 24, font: "Arial", color: "666666" })]
      })]
    })]
  });

  const box = new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [CONTENT_W],
    rows: [new TableRow({
      height: { value: 2880, rule: "exact" },
      children: [new TableCell({
        borders: { top: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" },
                   bottom: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" },
                   left: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" },
                   right: { style: BorderStyle.SINGLE, size: 8, color: "AAAAAA" } },
        shading: { fill: "F2F2F2", type: ShadingType.CLEAR },
        width: { size: CONTENT_W, type: WidthType.DXA },
        margins: { top: 200, bottom: 200, left: 240, right: 240 },
        verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { before: 0, after: 0 },
          children: [new TextRun({ text: `[ INSERT IMAGE HERE ]`, bold: true, size: 24, font: "Arial", color: "888888" })]
        })]
      })]
    })]
  });

  const cap = new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 80, after: 200 },
    children: [
      new TextRun({ text: caption, italic: true, size: 22, font: "Arial", color: "444444" })
    ]
  });

  return [box, cap];
}

function bulletItem(text, numbering) {
  return new Paragraph({
    numbering,
    spacing: { before: 60, after: 60, line: 276 },
    children: [new TextRun({ text, size: 24, font: "Arial" })],
  });
}

// Data dictionary table builder
function dataTable(rows) {
  const colWidths = [1200, 2000, 900, 900, 700, 700, 700, 860]; // sum=7960... adjust below

  const hdrCells = ["Attribute Name", "Contents", "Type", "Format", "Range", "Required", "PK/FK", "FK Referenced Table"]
    .map((h, i) => new TableCell({
      borders,
      shading: { fill: "1F4E79", type: ShadingType.CLEAR },
      width: { size: colWidths[i], type: WidthType.DXA },
      margins: { top: 60, bottom: 60, left: 80, right: 80 },
      children: [new Paragraph({
        spacing: { before: 0, after: 0 },
        children: [new TextRun({ text: h, bold: true, size: 18, font: "Arial", color: "FFFFFF" })]
      })]
    }));

  const dataRows = rows.map((row, ri) => {
    const cells = row.map((cell, ci) => new TableCell({
      borders,
      shading: { fill: ri % 2 === 0 ? "FFFFFF" : "EEF4FB", type: ShadingType.CLEAR },
      width: { size: colWidths[ci], type: WidthType.DXA },
      margins: { top: 60, bottom: 60, left: 80, right: 80 },
      children: [new Paragraph({
        spacing: { before: 0, after: 0 },
        children: [new TextRun({ text: String(cell), size: 18, font: "Arial" })]
      })]
    }));
    return new TableRow({ children: cells });
  });

  return new Table({
    width: { size: CONTENT_W, type: WidthType.DXA },
    columnWidths: [1250, 2000, 950, 800, 700, 700, 700, 1260],
    rows: [new TableRow({ children: hdrCells }), ...dataRows]
  });
}

// ── numbering config ──────────────────────────────────────────────────────────
const numberingConfig = [
  {
    reference: "bullets",
    levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
  },
  {
    reference: "numbers",
    levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
  },
  {
    reference: "numbers2",
    levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
  },
  {
    reference: "numbers3",
    levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } } }]
  },
];

const bul = { reference: "bullets", level: 0 };

// ── DOCUMENT ──────────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: { config: numberingConfig },
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1800 }
      }
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: "2E75B6", space: 1 } },
            spacing: { before: 0, after: 120 },
            children: [
              new TextRun({ text: "Jayraldine\u2019s Catering Management System", italics: true, size: 20, font: "Arial", color: "444444" }),
              new TextRun({ text: "\t", size: 20 }),
              new TextRun({ text: "Capstone Project Manuscript", size: 20, font: "Arial", color: "444444" }),
            ],
            tabStops: [{ type: "right", position: CONTENT_W }]
          })
        ]
      })
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            border: { top: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } },
            spacing: { before: 80, after: 0 },
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "Page ", size: 20, font: "Arial", color: "666666" }),
              new TextRun({ children: [PageNumber.CURRENT], size: 20, font: "Arial", color: "666666" }),
              new TextRun({ text: " of ", size: 20, font: "Arial", color: "666666" }),
              new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 20, font: "Arial", color: "666666" }),
            ]
          })
        ]
      })
    },

    children: [

      // ── TITLE PAGE ──────────────────────────────────────────────────────────
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 720, after: 120 },
        children: [new TextRun({ text: "Republic of the Philippines", size: 24, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "CEBU TECHNOLOGICAL UNIVERSITY", size: 28, bold: true, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "MAIN CAMPUS", size: 24, bold: true, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 },
        children: [new TextRun({ text: "College of Information Technology", size: 24, font: "Arial" })] }),

      ...spacer(2),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "JAYRALDINE\u2019S CATERING MANAGEMENT SYSTEM", size: 36, bold: true, font: "Arial", color: "1F4E79" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 },
        children: [new TextRun({ text: "A Capstone Project", size: 26, italics: true, font: "Arial", color: "444444" })] }),

      ...spacer(2),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "Presented to the Faculty of the College of Information Technology", size: 24, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 },
        children: [new TextRun({ text: "Cebu Technological University", size: 24, font: "Arial" })] }),

      ...spacer(1),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "In Partial Fulfillment of the Requirements for the Degree of", size: 24, italics: true, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 },
        children: [new TextRun({ text: "Bachelor of Science in Information Technology", size: 24, bold: true, font: "Arial" })] }),

      ...spacer(2),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "Submitted by:", size: 24, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 },
        children: [new TextRun({ text: "[Student Name/s]", size: 24, bold: true, font: "Arial" })] }),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "Submitted to:", size: 24, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 360 },
        children: [new TextRun({ text: "[Instructor / Adviser Name]", size: 24, bold: true, font: "Arial" })] }),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 120 },
        children: [new TextRun({ text: "Date Submitted:", size: 24, font: "Arial" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 1440 },
        children: [new TextRun({ text: "May 2026", size: 24, bold: true, font: "Arial" })] }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── CHAPTER 1 ────────────────────────────────────────────────────────────
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 360, after: 200 },
        children: [new TextRun({ text: "CHAPTER 1", size: 32, bold: true, font: "Arial", color: "1F4E79" })] }),

      // 1.2 INTRODUCTION
      heading1("1.2 Introduction"),

      heading2("1.2.1 Background of the Study"),
      p("The catering industry is a dynamic and service-intensive sector that demands a high degree of operational coordination among multiple departments including booking management, kitchen preparation, client communication, billing, and business analytics. For small to medium-sized catering enterprises, the manual administration of these interdependent processes often leads to inefficiencies, scheduling conflicts, missed communications, and inaccurate financial records. As digital solutions become increasingly accessible, the adoption of specialized management software has emerged as a practical approach to streamline these operations and support sustainable business growth."),
      p("Jayraldine\u2019s Catering is a local catering enterprise that has historically relied on traditional, paper-based systems and informal digital tools such as spreadsheets and messaging applications to manage its daily operations. While these methods have served the business in its early stages, the increasing volume of client bookings, the complexity of coordinating kitchen tasks across multiple events, and the growing expectation of professional client communication have exposed significant limitations in the existing approach. Bookings were tracked without automated conflict detection, kitchen staff had no structured checklist to follow during preparation, clients received no automated confirmation messages upon booking approval, and the business had no integrated means of generating receipts or tracking net profit against operational expenses."),
      p("This capstone project was conceived in direct response to these identified operational gaps. The proponents worked closely with the catering business owner to document pain points, prioritize features, and develop a desktop application purpose-built for Jayraldine\u2019s Catering. The resulting system, the Jayraldine\u2019s Catering Management System, is a fully integrated desktop application developed using Python with the PySide6 graphical user interface framework and PostgreSQL as the relational database management system. The system covers the full lifecycle of a catering event \u2014 from the initial client inquiry and booking request, through kitchen preparation, invoice generation, and payment collection, to post-event reporting and business performance analysis."),
      p("The development of this system is grounded in the principles of software engineering, database design, and human-computer interaction. It reflects the proponents\u2019 applied learning in information technology and their commitment to producing a solution that delivers measurable value to a real-world business context."),

      heading2("1.2.2 Statement of the Problem"),
      p("Prior to the development of this system, Jayraldine\u2019s Catering faced a set of recurring operational problems that limited the efficiency and professionalism of its service delivery. These problems were identified through direct consultation with the business owner and observation of the existing workflow. The specific problems addressed by this study are as follows:"),

      ...["Absence of date conflict detection and capacity enforcement. The business had no mechanism to prevent the acceptance of bookings that exceeded the maximum daily guest capacity. Multiple bookings on the same date could collectively surpass the kitchen and service team\u2019s physical limits, resulting in compromised service quality and client dissatisfaction.",
         "Lack of downpayment enforcement before booking confirmation. Bookings were confirmed without verifying whether the client had submitted the required minimum downpayment. This exposed the business to financial risk from uncommitted clients who might cancel without consequence.",
         "No automated client notification system. Upon approving a booking, the staff had no integrated tool to automatically send confirmation messages to clients via email or SMS. This created communication gaps and increased the risk of miscommunication regarding event details.",
         "No structured kitchen preparation workflow. Kitchen staff received only a general description of the items to prepare for each event. There was no per-dish task checklist, no stage-based Kanban tracking, and no mechanism to monitor preparation progress across multiple concurrent orders.",
         "No integrated billing and receipt generation. Invoices were manually prepared, and there was no built-in capability to generate branded receipt documents or deliver them to clients electronically via email.",
         "Inability to track net profit. While revenue from bookings and invoices could be tallied informally, there was no system for logging operational expenses by category. This made it impossible to calculate net profit, assess cost efficiency, or support informed business decisions.",
         "No customer loyalty tracking or follow-up reminder system. Repeat clients were not recognized or rewarded, and staff had no structured tool to schedule and track follow-up reminders for prospective or returning clients.",
         "Absence of an audit trail. There was no record of who approved or cancelled bookings, who issued invoices, or what changes were made to financial records. This created accountability gaps and made it difficult to investigate discrepancies."
      ].map((item, i) => new Paragraph({
        numbering: { reference: `numbers${i < 3 ? "" : i < 6 ? "2" : "3"}`, level: 0 },
        spacing: { before: 80, after: 80, line: 276 },
        children: [new TextRun({ text: item, size: 24, font: "Arial" })],
      })),

      p("These problems collectively motivated the development of a unified management system designed to automate, enforce, and monitor all critical operations of the catering business."),

      heading2("1.2.3 Objectives of the Study"),
      p("The primary objective of this study is to design, develop, and deploy a desktop-based Catering Management System for Jayraldine\u2019s Catering that addresses the identified operational problems and enhances the overall efficiency, accuracy, and professionalism of the business."),
      p("Specifically, this study aims to:", { after: 60 }),
      ...[
        "Develop an Orders and Bookings module that enables staff to receive, record, approve, and manage client booking requests, with automated enforcement of date capacity limits and minimum downpayment requirements before confirmation.",
        "Implement an automated client notification system that sends booking confirmation messages to clients via email and SMS upon booking approval, and supports manual resending of confirmations at any time.",
        "Design and implement a Kitchen Management module featuring a Kanban-style order tracking board with six preparation stages (Queued, Preparing, In Progress, Ready, Delivered, Done), and per-order task checklists that are automatically generated from booked items.",
        "Build an integrated Billing and Invoicing module that tracks invoice status (Unpaid, Partial, Paid), supports payment recording, and enables the generation and delivery of branded receipt documents in PDF format via print or email.",
        "Create an Expense Tracking and Profit Analysis module that allows the business to log operational expenses by category and automatically calculate net profit against total revenue.",
        "Implement a Customer Relationship Management module with loyalty tier tracking (Bronze, Silver, Gold, VIP) automatically updated based on confirmed booking history, and a follow-up reminder system visible on the Dashboard.",
        "Develop a full audit logging system that records every significant action performed in the system \u2014 including booking approvals, cancellations, invoice transactions, and kitchen status changes \u2014 with actor identification, timestamps, and old/new value tracking.",
        "Provide a reporting and analytics module that presents business performance metrics through charts and KPI cards, with export capabilities to PDF, Excel, and CSV formats.",
        "Establish a database backup and restore facility within the application that allows authorized staff to create and restore full database backups without requiring external tools.",
      ].map((item, i) => new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        spacing: { before: 80, after: 80, line: 276 },
        children: [new TextRun({ text: `${i + 1}. ${item}`, size: 24, font: "Arial" })],
      })),

      heading2("1.2.4 Significance of the Study"),
      p("The development of the Jayraldine\u2019s Catering Management System holds significance at multiple levels \u2014 for the business itself, for its clients, for the academic proponents, and for future researchers in the same domain."),

      p("For Jayraldine\u2019s Catering (Business Owner and Staff). The system directly eliminates the most pressing operational inefficiencies experienced by the business. Staff will benefit from a centralized platform that unifies all aspects of catering management \u2014 from booking intake to kitchen coordination to financial reporting \u2014 reducing the reliance on multiple disconnected tools.", { bold: false }),
      p("For Clients of Jayraldine\u2019s Catering. Clients benefit from a more responsive and organized service experience. Automated booking confirmation messages ensure that clients are informed promptly upon approval. Professionally generated receipts and invoices delivered via email provide clients with reliable documentation of their transactions."),
      p("For the Proponents. This project represents a comprehensive application of the knowledge and skills acquired throughout the Bachelor of Science in Information Technology program. It offered practical experience in full-stack desktop application development, relational database design, stored procedure programming, user interface design, and software project management."),
      p("For Future Researchers and Developers. This study contributes a documented reference for the development of desktop-based management systems for small and medium enterprises in the service sector. The architecture, database design, and feature set documented herein may serve as a foundation or comparative reference for future capstone projects addressing similar business domains."),

      // ── 1.3 SCOPE AND LIMITATIONS ────────────────────────────────────────────
      heading1("1.3 Scope and Limitations"),

      heading2("1.3.1 Scope"),
      p("The Jayraldine\u2019s Catering Management System is a single-machine, desktop-based application designed to operate within the internal workflow of Jayraldine\u2019s Catering. The scope of the system encompasses the following functional areas:"),

      ...[
        ["1. Orders and Bookings Management.", "The system supports the full booking lifecycle: creation of new booking records, editing of pending bookings, approval with automated downpayment and capacity validation, cancellation with reason recording, and tracking of booking status through the states PENDING, CONFIRMED, COMPLETED, and CANCELLED. Each booking stores the client name, event date, event time, number of guests (pax), occasion type, venue, selected menu package or custom items, payment mode, and downpayment amount. The system generates a unique booking reference number for each record (e.g., BKG-001)."],
        ["2. Date Capacity Management.", "The system enforces a configurable maximum daily guest capacity (default: 600 pax). A booking cannot be confirmed if the cumulative guest count for the same event date would exceed this limit. The capacity threshold is visually represented on the Calendar module using color-coded indicators (green, amber, red)."],
        ["3. Downpayment Policy Enforcement.", "The system enforces a configurable minimum downpayment percentage (default: 30%). A booking cannot be confirmed if the amount paid is less than the calculated minimum downpayment. An administrative override toggle (Allow Zero Downpayment) can be enabled in Settings when necessary."],
        ["4. Client Notification.", "Upon booking confirmation, the system automatically sends a booking confirmation message to the client via email (SMTP protocol) and/or SMS (Semaphore SMS gateway API), provided credentials are configured. A manual resend button is available for each confirmed booking."],
        ["5. Calendar Scheduling.", "The system provides a monthly calendar view displaying all confirmed bookings with color-coded capacity indicators. Staff can click any day to view events and manage manual schedule entries."],
        ["6. Kitchen Order Management.", "The system automatically creates a kitchen order entry for every confirmed booking. Orders are tracked through six preparation stages on a Kanban board: Queued, Preparing, In Progress, Ready, Delivered, and Done. Each kitchen order card displays a task checklist auto-generated from booked menu items."],
        ["7. Billing and Invoicing.", "The system supports invoice creation and management, tracking of payment status (Unpaid, Partial, Paid), partial payment recording, and generation of branded PDF receipts deliverable via print or email."],
        ["8. Customer Relationship Management.", "The system maintains a customer database with loyalty tier tracking (Bronze, Silver, Gold, VIP) automatically updated based on confirmed booking history, plus a follow-up reminder system visible on the Dashboard."],
        ["9. Expense and Profit Tracking.", "The system allows staff to log business expenses under six categories: Food Cost, Labor, Transport, Utilities, Equipment, and Other. The Reports module aggregates total revenue and expenses to calculate and display net profit."],
        ["10. Reporting and Analytics.", "The Reports module displays KPI summary cards and interactive charts. Reports can be filtered by time period and exported in PDF, Excel, or CSV format."],
        ["11. Notification System.", "The system runs a background scheduler polling for upcoming confirmed events every 10 seconds, triggering toast notifications at 24 hours before, 30 minutes before, and at the exact event start time."],
        ["12. Audit Logging.", "All significant system actions are automatically recorded in the audit log with actor, action type, affected table, record identifier, and old/new values."],
        ["13. Settings and Configuration.", "The Settings module allows authorized staff to configure business information, booking and capacity policy, email SMTP credentials, Semaphore SMS API key, appearance (dark/light theme), and database backup/restore operations."],
        ["14. Database Backup and Restore.", "The system provides built-in backup (via pg_dump) and restore (via psql) functionality accessible from the Settings module."],
      ].flatMap(([title, body]) => [
        new Paragraph({
          spacing: { before: 160, after: 60, line: 276 },
          children: [
            new TextRun({ text: title, bold: true, size: 24, font: "Arial" }),
            new TextRun({ text: " " + body, size: 24, font: "Arial" }),
          ]
        })
      ]),

      heading2("1.3.2 Limitations"),
      p("While the Jayraldine\u2019s Catering Management System addresses a broad range of operational needs, the following limitations are acknowledged:"),
      ...[
        "Single-machine desktop deployment. The system is designed for installation on a single workstation. It does not support simultaneous multi-user network access, and has no web-based or mobile interface.",
        "No raw ingredient inventory tracking. The system does not manage raw ingredient stock levels, supplier procurement, or recipe-level ingredient consumption.",
        "No online booking portal. All bookings are entered by staff on behalf of clients who contact the business through other channels.",
        "No multi-user role-based access control. All users of the installed application have access to all modules.",
        "SMS delivery depends on third-party API. The SMS notification feature requires a valid Semaphore API key and active internet connection.",
        "Email delivery depends on SMTP configuration. Valid SMTP server credentials are required for email notification and receipt delivery.",
        "PDF generation requires reportlab. The PDF export feature depends on the reportlab Python library.",
        "Limited to the Philippine context. Currency is displayed in Philippine Peso (\u20b1) format and date/time formats follow local conventions.",
        "No payment gateway integration. Payment amounts are entered manually by staff.",
        "Backup and restore require PostgreSQL client utilities. The pg_dump and psql tools must be present in the system PATH.",
      ].map(item => new Paragraph({
        numbering: { reference: "bullets", level: 0 },
        spacing: { before: 80, after: 80, line: 276 },
        children: [new TextRun({ text: item, size: 24, font: "Arial" })],
      })),

      // ── 1.4 METHODOLOGY ──────────────────────────────────────────────────────
      heading1("1.4 Methodology"),
      p("The development of the Jayraldine\u2019s Catering Management System followed an iterative, requirements-driven development approach. The proponents conducted structured interviews with the catering business owner to identify and prioritize operational pain points, then translated these into a formal Product Requirements Document (PRD). Development proceeded in prioritized feature batches, with each batch followed by a review session with the stakeholder to validate behavior against the stated requirements."),
      p("The system was architected as a three-tier desktop application: a PySide6-based presentation layer, a Python business logic layer, and a PostgreSQL database layer. All database interactions are mediated through stored procedures, providing a clean separation between application logic and data persistence."),

      heading2("1.4.1 ERD Conceptual Model"),
      p("The conceptual entity-relationship model identifies the following primary entities and their relationships:"),
      ...[
        "Customer \u2014 represents a client of the catering business. A customer may have zero or more bookings, zero or more invoices, and zero or more follow-up reminders.",
        "Booking \u2014 represents a catering event request. Each booking belongs to one customer and may correspond to one kitchen order and one or more invoices.",
        "Package \u2014 represents a pre-defined catering package with a fixed price per pax.",
        "Menu Item \u2014 represents an individual dish or service offering.",
        "Kitchen Order \u2014 represents the kitchen preparation record for a confirmed booking.",
        "Kitchen Task \u2014 represents a single preparation checklist item for a kitchen order.",
        "Invoice \u2014 represents a billing record tracking total amount, amount paid, and payment status.",
        "Expense \u2014 represents an operational cost entry with category, amount, description, and date.",
        "Notification \u2014 represents a system-generated alert for an upcoming event.",
        "Calendar Event \u2014 represents a manually scheduled entry on a specific date.",
        "Audit Log \u2014 records every significant system action with actor, action type, and values.",
        "Receipt Log \u2014 records each instance of a receipt being printed or emailed.",
        "Confirmation Log \u2014 records each instance of a booking confirmation sent via email or SMS.",
        "Business Info \u2014 a singleton configuration record storing business details and policy parameters.",
        "Customer Follow-Up \u2014 a reminder entry associated with a customer with a scheduled date.",
      ].map(item => bulletItem(item, bul)),

      ...spacer(1),
      ...imagePlaceholder("Figure 1. ERD Conceptual Model \u2014 showing all entities, attributes, and relationships of the Jayraldine\u2019s Catering Management System"),

      heading2("1.4.2 Data Dictionary"),
      p("The following tables describe the structure of each database table implemented in the Jayraldine\u2019s Catering Management System."),

      // bookings table
      heading3("Table: bookings"),
      dataTable([
        ["id", "Unique booking identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["booking_ref", "Human-readable booking reference", "VARCHAR(20)", "BKG-NNN", "Unique", "Yes", "\u2014", "\u2014"],
        ["customer_id", "Reference to the customer", "INTEGER", "\u2014", "Valid customer ID", "Yes", "FK", "customers"],
        ["customer_name", "Customer name (denormalized)", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["event_date", "Date of the catering event", "DATE", "YYYY-MM-DD", "\u2014", "Yes", "\u2014", "\u2014"],
        ["event_time", "Time of the catering event", "TIME", "HH:MM", "\u2014", "No", "\u2014", "\u2014"],
        ["pax", "Number of guests", "INTEGER", "\u2014", "\u2265 1", "Yes", "\u2014", "\u2014"],
        ["occasion", "Type of event occasion", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["venue", "Location of the event", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["package_id", "Reference to selected package", "INTEGER", "\u2014", "Valid package ID", "No", "FK", "packages"],
        ["items_desc", "Description of menu items selected", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["payment_mode", "Mode of payment", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["total_amount", "Total billing amount", "NUMERIC(12,2)", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["amount_paid", "Amount paid as downpayment", "NUMERIC(12,2)", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["status", "Current booking status", "booking_status ENUM", "\u2014", "PENDING/CONFIRMED/COMPLETED/CANCELLED", "Yes", "\u2014", "\u2014"],
        ["cancellation_reason", "Reason recorded on cancellation", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["created_at", "Timestamp when booking was created", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["updated_at", "Timestamp of last update", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: customers"),
      dataTable([
        ["id", "Unique customer identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["name", "Full name of the customer", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["contact_number", "Customer contact number", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["email", "Customer email address", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["address", "Customer physical address", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["total_events", "Count of confirmed and completed bookings", "INTEGER", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["loyalty_tier", "Auto-assigned loyalty tier", "loyalty_tier ENUM", "\u2014", "Bronze/Silver/Gold/VIP", "Yes", "\u2014", "\u2014"],
        ["status", "Customer account status", "TEXT", "\u2014", "Active, Inactive", "Yes", "\u2014", "\u2014"],
        ["created_at", "Timestamp when record was created", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["updated_at", "Timestamp of last update", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: customer_follow_ups"),
      dataTable([
        ["id", "Unique follow-up identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["customer_id", "Reference to the associated customer", "INTEGER", "\u2014", "Valid customer ID", "Yes", "FK", "customers"],
        ["follow_up_date", "Date when follow-up action is due", "DATE", "YYYY-MM-DD", "\u2014", "Yes", "\u2014", "\u2014"],
        ["note", "Description of the follow-up task", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["is_done", "Whether follow-up has been completed", "BOOLEAN", "\u2014", "true/false", "Yes", "\u2014", "\u2014"],
        ["created_at", "Timestamp when follow-up was added", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: menu_items"),
      dataTable([
        ["id", "Unique menu item identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["name", "Name of the dish or service", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["description", "Brief description of the item", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["category", "Category of the menu item", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["package_tier", "Associated package tier label", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["price", "Unit price of the item", "NUMERIC(10,2)", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["status", "Availability status", "TEXT", "\u2014", "Available/Unavailable/Seasonal/Out of Stock", "Yes", "\u2014", "\u2014"],
        ["created_at", "Timestamp when item was added", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: packages"),
      dataTable([
        ["id", "Unique package identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["name", "Package name", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["description", "Package description", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["price_per_pax", "Price charged per guest", "NUMERIC(10,2)", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["min_pax", "Minimum number of guests", "INTEGER", "\u2014", "\u2265 1", "No", "\u2014", "\u2014"],
        ["created_at", "Timestamp when package was created", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: invoices"),
      dataTable([
        ["id", "Unique invoice identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["invoice_ref", "Human-readable invoice reference", "VARCHAR(20)", "INV-NNN", "Unique", "Yes", "\u2014", "\u2014"],
        ["customer_id", "Reference to the associated customer", "INTEGER", "\u2014", "Valid customer ID", "Yes", "FK", "customers"],
        ["customer_name", "Customer name (denormalized)", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["event_date", "Date of the catering event", "DATE", "YYYY-MM-DD", "\u2014", "No", "\u2014", "\u2014"],
        ["total_amount", "Total invoice amount", "NUMERIC(12,2)", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["amount_paid", "Total amount received to date", "NUMERIC(12,2)", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["status", "Computed payment status", "TEXT", "\u2014", "Unpaid, Partial, Paid", "Yes", "\u2014", "\u2014"],
        ["created_at", "Timestamp when invoice was created", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["updated_at", "Timestamp of last update", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: kitchen_orders"),
      dataTable([
        ["id", "Unique kitchen order identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["booking_id", "Reference to the associated booking", "INTEGER", "\u2014", "Valid booking ID", "Yes", "FK", "bookings"],
        ["client_name", "Client name for Kanban card display", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["pax", "Number of guests for this order", "INTEGER", "\u2014", "\u2265 1", "Yes", "\u2014", "\u2014"],
        ["event_name", "Name/occasion of the event", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["items_desc", "Menu items description string", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["status", "Current kitchen preparation stage", "TEXT", "\u2014", "Queued/Preparing/In Progress/Ready/Delivered/Done", "Yes", "\u2014", "\u2014"],
        ["created_at", "Timestamp when order was created", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["updated_at", "Timestamp of last status update", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: kitchen_tasks"),
      dataTable([
        ["id", "Unique task identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["order_id", "Reference to the associated kitchen order", "INTEGER", "\u2014", "Valid kitchen order ID", "Yes", "FK", "kitchen_orders"],
        ["task_label", "Description of the preparation task", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["is_done", "Whether the task has been completed", "BOOLEAN", "\u2014", "true/false", "Yes", "\u2014", "\u2014"],
        ["sort_order", "Display order of task within card", "INTEGER", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["updated_at", "Timestamp of last update", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: calendar_events"),
      dataTable([
        ["id", "Unique calendar event identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["event_date", "Date of the scheduled event", "DATE", "YYYY-MM-DD", "\u2014", "Yes", "\u2014", "\u2014"],
        ["title", "Event title or label", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["note", "Additional description or notes", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["created_at", "Timestamp when the event was created", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: notifications"),
      dataTable([
        ["id", "Unique notification identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["booking_id", "Reference to the associated booking", "INTEGER", "\u2014", "Valid booking ID", "No", "FK", "bookings"],
        ["title", "Short notification title", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["message", "Full notification message text", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["type", "Notification trigger type", "TEXT", "\u2014", "1_day, 30_min, now", "Yes", "\u2014", "\u2014"],
        ["is_read", "Whether notification has been read", "BOOLEAN", "\u2014", "true/false", "Yes", "\u2014", "\u2014"],
        ["created_at", "Timestamp when notification was generated", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: expenses"),
      dataTable([
        ["id", "Unique expense identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["category", "Expense category", "expense_category ENUM", "\u2014", "Food Cost/Labor/Transport/Utilities/Equipment/Other", "Yes", "\u2014", "\u2014"],
        ["description", "Description of the expense", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["amount", "Expense amount", "NUMERIC(10,2)", "\u2014", "\u2265 0", "Yes", "\u2014", "\u2014"],
        ["expense_date", "Date the expense was incurred", "DATE", "YYYY-MM-DD", "\u2014", "Yes", "\u2014", "\u2014"],
        ["created_at", "Timestamp when record was entered", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: audit_logs"),
      dataTable([
        ["id", "Unique audit log entry identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["actor", "Staff member who performed the action", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["action", "Type of action performed", "TEXT", "\u2014", "APPROVE/CANCEL/CREATE/UPDATE/STATUS_CHANGE", "Yes", "\u2014", "\u2014"],
        ["table_name", "Name of the affected database table", "TEXT", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
        ["record_id", "Primary key of the affected record", "INTEGER", "\u2014", "\u2265 1", "Yes", "\u2014", "\u2014"],
        ["old_value", "Previous state of the record (JSONB)", "JSONB", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["new_value", "New state of the record (JSONB)", "JSONB", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["created_at", "Timestamp when log entry was written", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: receipt_log"),
      dataTable([
        ["id", "Unique receipt log identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["invoice_id", "Reference to the invoice", "INTEGER", "\u2014", "Valid invoice ID", "Yes", "FK", "invoices"],
        ["method", "Delivery method used", "TEXT", "\u2014", "print, email", "Yes", "\u2014", "\u2014"],
        ["sent_at", "Timestamp when receipt was delivered", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: confirmation_log"),
      dataTable([
        ["id", "Unique confirmation log identifier", "INTEGER", "Auto-increment", "\u2265 1", "Yes", "PK", "\u2014"],
        ["booking_id", "Reference to the associated booking", "INTEGER", "\u2014", "Valid booking ID", "Yes", "FK", "bookings"],
        ["method", "Notification channel used", "TEXT", "\u2014", "email, sms", "Yes", "\u2014", "\u2014"],
        ["sent_at", "Timestamp when confirmation was sent", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      ...spacer(1),

      heading3("Table: business_info"),
      dataTable([
        ["id", "Singleton record identifier", "INTEGER", "\u2014", "Always 1", "Yes", "PK", "\u2014"],
        ["business_name", "Registered business name", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["owner_name", "Name of the business owner", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["contact_number", "Business contact number", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["email", "Business email address", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["address", "Physical address of the business", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["min_downpayment_pct", "Minimum required downpayment percentage", "NUMERIC(5,2)", "\u2014", "0\u2013100", "Yes", "\u2014", "\u2014"],
        ["allow_zero_downpayment", "Toggle to bypass downpayment check", "BOOLEAN", "\u2014", "true/false", "Yes", "\u2014", "\u2014"],
        ["max_daily_pax", "Maximum total guests allowed per day", "INTEGER", "\u2014", "\u2265 1", "Yes", "\u2014", "\u2014"],
        ["smtp_host", "SMTP server hostname", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["smtp_port", "SMTP server port number", "INTEGER", "\u2014", "1\u201365535", "No", "\u2014", "\u2014"],
        ["smtp_user", "SMTP account username", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["smtp_pass", "SMTP account password or app password", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["sms_api_key", "Semaphore SMS API key", "TEXT", "\u2014", "\u2014", "No", "\u2014", "\u2014"],
        ["updated_at", "Timestamp of last settings update", "TIMESTAMP", "\u2014", "\u2014", "Yes", "\u2014", "\u2014"],
      ]),

      heading2("1.4.3 ERD Physical Model"),
      p("The physical entity-relationship model extends the conceptual model by specifying the exact PostgreSQL implementation details: column data types, NOT NULL and DEFAULT constraints, primary key sequences, foreign key references with ON DELETE behavior, enumerated type declarations, and index definitions."),
      p("Key physical model decisions include:"),
      ...[
        "Enumerated types (booking_status, loyalty_tier, expense_category) are declared as PostgreSQL CREATE TYPE ... AS ENUM constructs, enforcing domain integrity at the database engine level.",
        "Automatic timestamp updates on the updated_at columns are implemented via PostgreSQL trigger functions using BEFORE UPDATE triggers.",
        "Loyalty tier recalculation is triggered automatically after any update to bookings.status via an AFTER UPDATE trigger that calls the sp_recalculate_loyalty() stored procedure.",
        "Foreign key constraints are defined with ON DELETE CASCADE where child records have no independent meaning, and with ON DELETE RESTRICT where referential integrity must be explicitly managed.",
        "Indexes are defined on frequently queried foreign key columns and filter predicates to support performant query execution.",
      ].map(item => bulletItem(item, bul)),

      ...spacer(1),
      ...imagePlaceholder("Figure 2. ERD Physical Model \u2014 showing all tables, column names, data types, constraints, primary keys, foreign keys, and relationships"),

      // ── 1.5 DEVELOPMENT TOOLS ────────────────────────────────────────────────
      heading1("1.5 Development Tools and Technologies"),

      heading2("1.5.1 PostgreSQL"),
      p("PostgreSQL is an open-source, object-relational database management system (ORDBMS) known for its standards compliance, extensibility, reliability, and feature richness. For this project, PostgreSQL version 14 or later was used as the exclusive data persistence layer."),
      p("PostgreSQL was selected for the following reasons:"),
      ...[
        "Stored Procedures and Functions. The system\u2019s business logic is largely implemented in the database layer through PostgreSQL stored procedures (using PL/pgSQL), enabling transactional consistency.",
        "Enumerated Types. PostgreSQL\u2019s native ENUM type support allows domain constraints to be enforced directly at the database level.",
        "Trigger Functions. Automatic loyalty tier recalculation and timestamp management are implemented via database triggers.",
        "JSONB Support. The audit_logs table uses JSONB to store structured old/new value snapshots.",
        "pg_dump / psql Utilities. Built-in command-line backup and restore utilities are leveraged directly by the application.",
        "psycopg2 Driver. PostgreSQL is accessed from Python via the psycopg2 driver, the de facto standard PostgreSQL adapter for Python.",
      ].map(item => bulletItem(item, bul)),

      heading2("1.5.2 Python"),
      p("Python is a high-level, interpreted, general-purpose programming language renowned for its readability, extensive standard library, and vibrant ecosystem. Python version 3.11 or later was used for all application development."),
      p("Key Python libraries used:"),
      ...[
        "PySide6 \u2014 official Qt for Python binding for the graphical user interface.",
        "psycopg2 \u2014 mature PostgreSQL interface for Python.",
        "reportlab \u2014 programmatic generation of branded PDF receipts and reports.",
        "openpyxl \u2014 Excel (.xlsx) file generation for report exports.",
        "smtplib / email (standard library) \u2014 SMTP email composition and delivery.",
        "requests \u2014 HTTP POST requests to the Semaphore SMS gateway API.",
        "threading \u2014 non-blocking background operations during application startup.",
        "os and subprocess \u2014 invocation of pg_dump and psql for backup and restore.",
      ].map(item => bulletItem(item, bul)),

      heading2("1.5.3 PySide6 (Qt for Python)"),
      p("PySide6 is the official Python binding for the Qt framework, developed and maintained by The Qt Company. It provides access to the full Qt 6 widget toolkit, enabling the development of professional-grade, cross-platform desktop graphical user interfaces."),
      p("PySide6 was selected for the following reasons:"),
      ...[
        "Rich Widget Set. Qt provides a comprehensive set of native-looking UI components including tables, list views, dialogs, combo boxes, date pickers, tab widgets, and scroll areas.",
        "Fusion Style. The application uses Qt\u2019s built-in \u201cFusion\u201d platform style for a consistent, modern appearance across operating systems.",
        "Qt Style Sheets (QSS). Dark and light themes are implemented using Qt Style Sheets, dynamically applied at runtime.",
        "Signal/Slot Architecture. Qt\u2019s signal/slot event system enables clean, decoupled communication between UI components.",
        "QTimer for Background Polling. The notification scheduler uses QTimer to fire a polling event every 10 seconds within the Qt event loop.",
        "PyInstaller Compatibility. The application can be packaged into a standalone Windows executable using PyInstaller.",
      ].map(item => bulletItem(item, bul)),

      heading2("1.5.4 System Architecture"),
      p("The Jayraldine\u2019s Catering Management System follows a three-tier desktop application architecture:"),
      new Paragraph({
        spacing: { before: 160, after: 60, line: 276 },
        children: [
          new TextRun({ text: "Tier 1 \u2014 Presentation Layer (UI). ", bold: true, size: 24, font: "Arial" }),
          new TextRun({ text: "The presentation layer consists of nine page modules unified within a main window frame. Shared UI components (sidebar navigation, topbar, toast notifications, booking modal, filter popover) are implemented as reusable classes.", size: 24, font: "Arial" }),
        ]
      }),
      new Paragraph({
        spacing: { before: 60, after: 60, line: 276 },
        children: [
          new TextRun({ text: "Tier 2 \u2014 Business Logic Layer. ", bold: true, size: 24, font: "Arial" }),
          new TextRun({ text: "Business logic is distributed between the Python application layer (form validation, PDF/Excel/CSV generation, email/SMS dispatch, background scheduling) and the PostgreSQL stored procedure layer (booking status transition enforcement, loyalty tier calculation, invoice status derivation, audit log writing).", size: 24, font: "Arial" }),
        ]
      }),
      new Paragraph({
        spacing: { before: 60, after: 160, line: 276 },
        children: [
          new TextRun({ text: "Tier 3 \u2014 Data Layer. ", bold: true, size: 24, font: "Arial" }),
          new TextRun({ text: "The data layer is a local PostgreSQL instance running the jayraldines_catering database. The utils/db.py module provides the sole access point to the database, implementing a singleton connection pattern with auto-reconnect capability.", size: 24, font: "Arial" }),
        ]
      }),

      ...spacer(1),
      ...imagePlaceholder("Figure 3. System Architecture Diagram \u2014 showing the three-tier structure: Presentation Layer (PySide6 UI), Business Logic Layer (Python + PostgreSQL Stored Procedures), and Data Layer (PostgreSQL)"),

      // ── 1.6 PROJECT TIMELINE ─────────────────────────────────────────────────
      heading1("1.6 Project Timeline (Gantt Chart)"),
      p("The development of the Jayraldine\u2019s Catering Management System was carried out over a structured development timeline spanning approximately six months. The project phases proceeded as follows:"),
      ...[
        ["Phase 1 \u2014 Requirements Gathering and Analysis (Weeks 1\u20133).", "Structured interviews with the catering business owner to document workflows, identify pain points, and define system requirements. A Product Requirements Document (PRD) was prepared."],
        ["Phase 2 \u2014 Database Design and Initial Setup (Weeks 4\u20136).", "Entity-relationship diagram designed at conceptual and physical levels. PostgreSQL database schema created including all table definitions, enumerated types, and initial stored procedures."],
        ["Phase 3 \u2014 Core Module Development (Weeks 7\u201312).", "Foundational modules implemented: Orders & Bookings, Customers, Menu, Calendar, and Kitchen. Main window navigation, sidebar, topbar, and theme system established."],
        ["Phase 4 \u2014 Advanced Feature Development (Weeks 13\u201318).", "Downpayment enforcement, capacity hard block, kitchen task checklist, billing and invoicing with PDF receipt generation, email notification via SMTP, and SMS notification via Semaphore implemented."],
        ["Phase 5 \u2014 Analytics, Notifications, and Audit (Weeks 19\u201322).", "Notification scheduler, audit logging system, customer loyalty tiers with PostgreSQL trigger, follow-up reminder system, and dashboard charts completed."],
        ["Phase 6 \u2014 Testing, Refinement, and Documentation (Weeks 23\u201326).", "End-to-end testing against all stated requirements. UI refinements, database backup/restore feature, and all documentation finalized."],
      ].flatMap(([title, body]) => [
        new Paragraph({
          spacing: { before: 160, after: 80, line: 276 },
          children: [
            new TextRun({ text: title, bold: true, size: 24, font: "Arial" }),
            new TextRun({ text: " " + body, size: 24, font: "Arial" }),
          ]
        })
      ]),

      ...spacer(1),
      ...imagePlaceholder("Figure 4. Project Gantt Chart \u2014 showing all six development phases with weekly timeline bars across the six-month project duration"),

      // ── 1.7 EXPECTED OUTPUTS ─────────────────────────────────────────────────
      heading1("1.7 Expected Outputs (Screenshots)"),
      p("This section presents the major interface screens of the Jayraldine\u2019s Catering Management System, illustrating the visual design and functionality of each module."),

      heading2("Dashboard"),
      p("The Dashboard provides a real-time business overview upon login. It displays KPI summary cards for today\u2019s events, pending bookings, weekly revenue, and outstanding unpaid balance. The lower section presents four analytics charts: monthly income (bar chart), payment method distribution (pie chart), top menu items by order count, and customer order frequency. Below the charts, an upcoming events card lists confirmed bookings due within the next 7 days with countdown timers."),
      ...imagePlaceholder("Figure 5. Dashboard Module (Dark Mode) \u2014 showing KPI cards, analytics charts, upcoming events section, and follow-up alerts"),

      heading2("Orders and Bookings"),
      p("The Orders & Bookings page presents all bookings in a searchable, filterable table. Each row displays the booking reference, customer name, event date, pax count, occasion, status badge, and amount paid versus total amount. Action buttons allow staff to approve, cancel, resend confirmation, edit, or delete a booking. A filter popover allows filtering by status, date range, and occasion type."),
      ...imagePlaceholder("Figure 6. Orders and Bookings Page \u2014 showing the booking table with status badges and action buttons"),
      ...imagePlaceholder("Figure 7. New Booking Modal \u2014 showing all input fields and the menu package selector"),

      heading2("Customers"),
      p("The Customers page lists all client records with their name, contact number, email, total events count, and loyalty tier badge (Bronze, Silver, Gold, or VIP). Clicking a customer row expands a detail panel showing full profile information, follow-up reminders, and a button to add a new follow-up."),
      ...imagePlaceholder("Figure 8. Customers Page \u2014 showing the customer list with loyalty tier badges and follow-up section"),

      heading2("Menu"),
      p("The Menu page is divided into two tabs: Menu Items and Packages. The Menu Items tab displays all dishes with their category, price, and status badge (Available, Unavailable, Seasonal, Out of Stock). The Packages tab lists all catering packages with their price per pax and minimum pax requirements. Both tabs support search filtering and CRUD operations."),
      ...imagePlaceholder("Figure 9. Menu Page \u2014 showing the Menu Items tab with status badges and package management"),

      heading2("Calendar"),
      p("The Calendar displays a full monthly view with color-coded day cells based on capacity utilization (green, amber, or red). Clicking any day opens a side panel listing all confirmed bookings for that day, a capacity status label, and a \u201cManage Day Schedule\u201d button for adding or removing manual events."),
      ...imagePlaceholder("Figure 10. Calendar Module \u2014 showing a month with color-coded day cells and the day detail side panel open"),

      heading2("Kitchen"),
      p("The Kitchen module presents a Kanban board with six column stages: Queued, Preparing, In Progress, Ready, Delivered, and Done. Each confirmed booking appears as a card with the client name, pax count, event name, items description, and a task checklist with checkboxes. Staff can advance or return cards between stages and manage per-card tasks."),
      ...imagePlaceholder("Figure 11. Kitchen Kanban Board \u2014 showing multiple order cards across different stage columns with task checklists visible"),

      heading2("Billing"),
      p("The Billing page lists all invoices with their reference number, customer name, event date, total amount, amount paid, and status badge (Unpaid, Partial, Paid). Staff can generate and save PDF receipts or email them directly to clients. The invoice form supports recording multiple partial payments."),
      ...imagePlaceholder("Figure 12. Billing Page \u2014 showing the invoice list with status badges and action icons"),
      ...imagePlaceholder("Figure 13. Generated PDF Receipt \u2014 showing the branded receipt layout with business name, invoice details, and payment summary"),

      heading2("Reports"),
      p("The Reports page contains three tabs: Overview, Expenses, and Profit. The Overview tab displays KPI summary cards with a period filter selector and export buttons (PDF, Excel, CSV). The Expenses tab shows a list of logged expenses with a form to add new entries. The Profit tab shows a net profit breakdown comparing total revenue against total expenses."),
      ...imagePlaceholder("Figure 14. Reports Overview Tab \u2014 showing KPI cards, period filter, and export buttons"),
      ...imagePlaceholder("Figure 15. Reports Expenses Tab \u2014 showing the expense log and add-expense form"),

      heading2("Settings"),
      p("The Settings page is organized into sections: Business Information, Booking & Capacity Policy, Email (SMTP) Configuration, SMS Configuration (Semaphore), Appearance, Database Backup & Restore, Occasions Management, and Audit Log. The Audit Log section displays the 50 most recent logged actions in a scrollable table."),
      ...imagePlaceholder("Figure 16. Settings Page \u2014 showing the Business Information section and Booking Policy configuration"),
      ...imagePlaceholder("Figure 17. Settings Audit Log Section \u2014 showing recent logged actions with actor, action, table, record, and timestamp columns"),

      // ── 1.8 CONCLUSION ───────────────────────────────────────────────────────
      heading1("1.8 Conclusion"),

      heading2("1.8.1 Summary"),
      p("The Jayraldine\u2019s Catering Management System was developed as a comprehensive, integrated desktop application designed to address the specific operational challenges of a small catering business operating in the Philippine context. Through structured requirements gathering, systematic database design, and iterative feature implementation, the proponents produced a fully functional system that delivers measurable improvements across all identified problem areas."),
      p("The system successfully fulfills all stated objectives: it enforces date capacity limits and minimum downpayment requirements before booking confirmation, automates client communication through email and SMS upon booking approval, provides kitchen staff with a structured Kanban workflow and per-order task checklists, enables generation and delivery of branded receipt documents, tracks operational expenses and calculates net profit, automatically recognizes and rewards repeat clients through a loyalty tier system, and maintains a complete audit trail of all significant system actions."),
      p("The technical implementation demonstrates a sound application of relational database design principles, with business rules enforced at the database layer through PostgreSQL stored procedures, triggers, and enumerated types. The use of PySide6 produced a professional, responsive desktop application with a polished dark-mode default theme, a clean navigation structure, and consistent visual design across all nine modules."),
      p("The data dictionary documents fifteen database tables covering every operational domain of the system. The three-tier architecture provides a clean separation of concerns that facilitates future maintenance and feature expansion."),
      p("While the system operates as a single-machine desktop application without multi-user network access or raw ingredient inventory tracking, these limitations are consistent with the current scale and operational context of the business. The system\u2019s modular design and well-structured codebase provide a solid foundation for future enhancements, including potential network-accessible deployment, role-based access control, and integration with external payment platforms."),
      p("In conclusion, the Jayraldine\u2019s Catering Management System represents a practical, fully realized capstone project that applies academic knowledge in information technology to solve real business problems. It demonstrates proficiency in full-stack desktop application development, PostgreSQL database design, event-driven GUI programming, and software project management."),

      // ── 1.9 REFERENCES ───────────────────────────────────────────────────────
      heading1("1.9 References"),
      p("Below are the key references consulted during the design, development, and documentation of the Jayraldine\u2019s Catering Management System, formatted in APA style.", { after: 240 }),

      ...[
        "PostgreSQL Global Development Group. (2023). PostgreSQL 15 documentation. The PostgreSQL Global Development Group. https://www.postgresql.org/docs/15/",
        "The Qt Company. (2023). PySide6 documentation: Qt for Python. The Qt Company Ltd. https://doc.qt.io/qtforpython-6/",
        "Python Software Foundation. (2023). Python 3.11 documentation. Python Software Foundation. https://docs.python.org/3.11/",
        "ReportLab Inc. (2023). ReportLab open-source PDF toolkit user guide (Version 4.0). ReportLab Inc. https://www.reportlab.com/docs/reportlab-userguide.pdf",
        "Gazoni, E., & Clark, C. (2023). openpyxl \u2014 A Python library to read/write Excel 2010 xlsx/xlsm files. https://openpyxl.readthedocs.io/",
        "Reitz, K., & Chiang, C. (2023). Requests: HTTP for humans. https://requests.readthedocs.io/",
        "Psycopg Team. (2023). Psycopg 2.9 documentation. https://www.psycopg.org/docs/",
        "Semaphore Philippines. (2023). Semaphore SMS API documentation. Semaphore. https://semaphore.co/docs",
        "Sommerville, I. (2016). Software engineering (10th ed.). Pearson Education Limited.",
        "Connolly, T., & Begg, C. (2014). Database systems: A practical approach to design, implementation, and management (6th ed.). Pearson Education Limited.",
        "Lutz, M. (2013). Learning Python (5th ed.). O\u2019Reilly Media.",
        "Cebu Technological University. (2024). Capstone project manuscript guide and template. CTU College of Information Technology.",
      ].map(ref => new Paragraph({
        spacing: { before: 80, after: 80, line: 276 },
        indent: { left: 720, hanging: 720 },
        children: [new TextRun({ text: ref, size: 24, font: "Arial" })]
      })),

      ...spacer(2),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 240, after: 0 },
        children: [new TextRun({ text: "\u2014 End of Manuscript \u2014", italics: true, size: 22, font: "Arial", color: "888888" })]
      }),

    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/mnt/user-data/outputs/Jayraldines_CMS_Manuscript.docx", buffer);
  console.log("Done!");
});