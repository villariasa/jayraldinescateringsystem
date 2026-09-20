# PC 317 - Systems Analysis and Design
## Worksheet No. 8: Nonfunctional Requirements

**Date:** _________________________  
**Proposed System:** Jayraldine's Catering Reservation and Management System  
**Student Names:**  
1. _____________________________________  
2. _____________________________________  
3. _____________________________________  
4. _____________________________________  

---

## Part 1: Nonfunctional Requirements by Category (Pages 2 - 3)

### Operational Requirements:
1. **Technical Environment:** The system operates in a client-server architecture using a Windows 10/11 64-bit desktop PC as the central server/manager station, interconnected with Android tablets, iPads, and mobile smartphones over a local Wi-Fi router (LAN) without requiring an active external internet connection.
2. **System Integration:** The system provides seamless real-time integration between the desktop PySide6 UI, the embedded HTTP Sync Server (port 8000), tablet kiosk PWAs, ESC/POS thermal receipt printers, and automated PDF contract generators (ReportLab).
3. **Portability:** Cross-platform accessibility allowing the desktop management application to run on Windows PCs while tablet kiosks run as an installable Android APK and Progressive Web App (PWA) on mobile web browsers.
4. **Maintainability:** Modular software design separating UI components, database repositories, and networking layers, with automated SQLite/MySQL schema migrations and single-click installer deployment.

---

### Performance Requirements:
1. **Speed:** User interface queries (booking lookups, customer history, menu package selections) respond in under 0.5 seconds. Tablet order sync over the local network completes in under 500 milliseconds. Billing contracts and reports compile in under 2 seconds.
2. **Capacity:** The local server concurrently supports 5 to 10 active staff tablet kiosk terminals simultaneously, while the database accommodates over 10,000 bookings and 50,000 financial records without performance degradation.
3. **Availability & Reliability:** 99.9% uptime during operational business hours with 100% offline resilience (zero dependency on cloud uptime or ISP connectivity during live catering events).

---

### Security Requirements:
1. **System Value Estimates:** High business criticality—protects proprietary package rates, customer contracts, food costings, and financial collections. Data loss or corruption could result in double-booking event venues and financial discrepancy.
2. **Access Control:** Role-Based Access Control (RBAC) separates Owner/Admin, Staff/Cashier, and Tablet Kiosk permissions. Critical actions (deleting bookings, overriding package pricing, database resets) require Owner authentication confirmation.
3. **Encryption & Authentication:** User passwords are stored using salted cryptographic hashing (SHA-256 / bcrypt). Local API endpoints require device authentication tokens.
4. **Virus Control & Integrity:** Cleanly bundled Windows executables compliant with Windows Defender; parameterized database queries to prevent SQL injection.

---

### Cultural and Political Requirements:
1. **Multilingual:** Interface is in Philippine English incorporating standard local catering terminology (e.g., Lechon, Kakanin, Debut, Pakyaw, Fiesta, Pax) with standard Philippine Peso currency (PHP / ₱).
2. **Customization:** Supports Dark and Light UI themes with selectable color accents, customizable package configurations (per-pax rates and ₱0.00 complimentary items), and custom business branding on receipts.
3. **Making Unstated Norms Explicit:** Explicit enforcement of Philippine catering reservation rules: mandatory downpayment deposit to confirm dates, venue/date collision detection to prevent double-booking, and clear separation of Contracted Revenue vs. Actual Cash Sales.
4. **Legal:** Adherence to the Philippine Data Privacy Act of 2012 (RA 10173) for customer contact information and compliance with local commercial billing receipt standards.

---

## Part 2: Requirements Definition Table (Page 4 Task)

**Accomplish the following task:**  
*Develop a requirement definition by identifying the nonfunctional requirements of your proposed system.*

| Non-Functional Requirements | System Requirements |
| :--- | :--- |
| **2.1 Operational**<br><br>**Technical Environment** | 1. The central server shall run on a standard Windows 10 or Windows 11 PC (64-bit) with at least 4GB of RAM.<br>2. Tablet and kiosk ordering terminals shall operate on Android 8.0+ or any device running modern web browsers.<br>3. Devices shall interconnect over a local wireless router (Wi-Fi LAN) without requiring internet connectivity.<br>4. The database layer shall utilize an embedded/local relational database (MySQL / SQLite). |
| **2.1 Operational**<br><br>**System Integration** | 1. The desktop application shall integrate with an embedded HTTP LAN server (port 8000) to communicate with mobile clients.<br>2. The system shall interface with standard desktop laser and 80mm ESC/POS thermal receipt printers.<br>3. The system shall integrate with ReportLab and openpyxl libraries for automated PDF contract and Excel report exports. |
| **2.1 Operational**<br><br>**Portability** | 1. The desktop application shall be deployable via a standalone setup installer containing all required runtime libraries.<br>2. The client interface shall be accessible cross-platform on Android tablets, iPads, and mobile phones via Progressive Web App (PWA) and Android APK. |
| **2.1 Operational**<br><br>**Maintainability** | 1. The database shall support automatic schema migrations and updates via bundled SQL scripts upon application launch.<br>2. The architecture shall decouple UI views, data access repositories, and network synchronization utilities for modular updates. |
| **2.2 Performance**<br><br>**Speed** | 1. The system shall respond to user search queries, package selections, and form submissions in under 0.5 seconds.<br>2. Orders submitted from tablet kiosks shall reflect on the server screen within under 1 second.<br>3. Financial evaluation summaries and PDF contracts shall generate in under 2 seconds. |
| **2.2 Performance**<br><br>**Capacity** | 1. The local server shall support at least 10 concurrent active tablet kiosk connections simultaneously without lag.<br>2. The database shall accommodate at least 10,000 bookings and 50,000 financial payment records without performance loss. |
| **2.2 Performance**<br><br>**Availability and Reliability** | 1. The system shall achieve 99.9% uptime during operational business hours.<br>2. The system shall operate fully in offline mode without requiring internet connectivity.<br>3. Automated database backup triggers shall safeguard against unexpected machine shutdown or power outage. |
| **2.3 Security**<br><br>**System Value Estimates** | 1. The system protects sensitive booking calendars, contract pricing, inventory counts, and financial transaction records.<br>2. Data loss or corruption must be prevented to avoid double-booked event venues and cash collection discrepancies. |
| **2.3 Security**<br><br>**Access Control** | 1. The system shall enforce Role-Based Access Control (Admin, Staff, Kiosk).<br>2. Critical functions (price adjustments, booking cancellations, user management, and raw database exports) shall require Owner PIN/Password confirmation. |
| **2.3 Security**<br><br>**Encryption and Authentication** | 1. User passwords shall be stored using salted cryptographic hashing (SHA-256 / bcrypt).<br>2. LAN communication between tablets and server shall require authenticated device handshakes. |
| **2.3 Security**<br><br>**Virus Control** | 1. All compiled binaries shall be cleanly built to pass Windows Defender SmartScreen and antivirus heuristic scans.<br>2. The system shall sanitize all user inputs with parameterized SQL statements to prevent code injection. |
| **2.4 Cultural and Political**<br><br>**Multilingual** | 1. The system language shall be Philippine English with support for regional event and catering terms (Debut, Fiesta, Pakyaw, Lechon, Pax).<br>2. The system shall use the Philippine Peso symbol (₱) and standard Philippine date/time formatting. |
| **2.4 Cultural and Political**<br><br>**Customization** | 1. The UI shall support user toggling between Light and Dark visual themes with dynamic color accents.<br>2. Invoices and contracts shall support customizable business headers, logos, contact details, and custom package rates (including ₱0.00 complimentary items). |
| **2.4 Cultural and Political**<br><br>**Making Unstated Norms Explicit** | 1. The system shall explicitly enforce standard catering reservation rules (e.g., initial deposit required to confirm event slots).<br>2. The system shall clearly separate "Projected Contract Revenue" from "Actual Sales / Cash Collections" on financial evaluation reports.<br>3. The booking calendar shall explicitly flag time/venue scheduling conflicts. |
| **2.4 Cultural and Political**<br><br>**Legal** | 1. The system shall comply with the Philippine Data Privacy Act of 2012 (RA 10173) by securing customer contact information.<br>2. Printed billing statements and receipts shall comply with standard commercial transaction transparency guidelines. |
