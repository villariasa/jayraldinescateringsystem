# PC 317: Systems Analysis and Design
## Worksheet No. 4: Technical Feasibility Analysis

| **Field** | **Details** |
|---|---|
| **Course** | PC 317 - Systems Analysis and Design |
| **Activity** | Worksheet No. 4: Technical Feasibility Analysis |
| **Date** | September 7, 2026 |
| **Student Names** | 1. Armenta, Mikka<br>2. Ilustrisimo, Daniel Grant<br>3. Navarro, Rey Anderson<br>4. Villarias, Medy |
| **Client / System** | Jayraldine's Catering Management System |
| **Project Sponsor** | Danilo Gimperoso Jr. (Jayraldine's Catering Services) |

---

### Objectives
1. Analyze technical feasibility of the proposed project.
2. Identify the associated risks.

### Tasks
1. Create a technical feasibility analysis of the proposed system. (refer to the given sample as guide)

---

# Worksheet No. 4: Technical Feasibility Analysis

### 1. Project Executive Summary
Mikka Armenta, Daniel Grant Ilustrisimo, Rey Anderson Navarro, and Medy Villarias created the following technical feasibility analysis for the Jayraldine's Catering Management System. The System Request (Worksheet No. 3) is referenced, along with the detailed business case from Worksheet No. 1. The highlights of the technical feasibility analysis are as follows:

* **Project Title:** Jayraldine's Catering Management and Scheduling System
* **Primary Sponsor:** Danilo Gimperoso Jr. (Jayraldine's Catering Services, 518 V. Rama Ave., Brgy. Calamba, Cebu City)
* **Technical Proponents:** Mikka Armenta, Daniel Grant Ilustrisimo, Rey Anderson Navarro, Medy Villarias
* **Overall Technical Feasibility:** The proposed system is feasible technically, with manageable risks that are effectively mitigated by using mature web technologies and intuitive user interface designs.

---

### 2. Technical Risk Analysis

#### 2.1 Familiarity with the Application (Business Domain)
*Jayraldine's Catering Services' risk regarding familiarity with catering management applications is moderately low.*

* **Analyst Domain Understanding:** The student analysts have conducted comprehensive process mapping of Jayraldine's end-to-end operational lifecycle, identifying six key operational gaps (`G-1` to `G-6`) spanning customer consultations, menu pricing, physical clear book scheduling, hauling logs, and paper-based billing.
* **User Domain Experience:** The business sponsor (Danilo Gimperoso Jr.) and catering staff possess deep domain expertise in catering production, buffet management, event styling, and customer negotiations. Because the proposed system digitizes their existing operational procedures rather than introducing an unfamiliar business model, the operational learning curve is minimal.
* **Industry Precedents:** Web-based food catering, banquet booking, and event scheduling platforms are widely established in the software industry, providing proven design patterns and established business logic.

#### 2.2 Familiarity with the Technology (Software & Tools)
*Jayraldine's Catering Services' risk regarding familiarity with the technology is moderately low.*

* **Development Stack Proficiency:** The development team has strong practical competencies in modern web development standards, JavaScript/TypeScript, React/Next.js, Node.js, and relational database systems (SQLite / PostgreSQL).
* **Technology Stack Maturity:** The system utilizes established, production-ready Progressive Web Application (PWA) technologies. These tools are backed by extensive technical documentation, robust component libraries, and active developer ecosystems, avoiding risky experimental software.
* **User Technological Literacy:** Client staff currently utilize basic consumer technology (smartphones and Facebook Messenger) with limited exposure to dedicated enterprise software. To eliminate operational resistance, the system is designed as a responsive, touch-friendly web app featuring clean layouts, minimal data entry friction, and guided workflows.

#### 2.3 Project Size (Scope, Team & Timeframe)
*The project size is considered low to medium risk.*

* **Development Team Capacity:** The project team consists of four (4) student developers/analysts with clear distribution of responsibilities across systems analysis, UI/UX prototyping, database design, and full-stack development.
* **Defined Functional Modules:** The project scope is strictly bounded to the six (6) core functional modules approved in the System Request: `F1` Order Management, `F2` Billing & Payments, `F3` Printable Event Calendar, `F4` Financial Analytics, `F5` Customer Records & Loyalty, and `F6` Dashboard Reporting.
* **Project Timeframe:** The development timeline spans an academic semester (~3 to 4 months). An iterative development approach will deliver the core transactional modules (`F1`, `F2`, `F3`) in early milestones, followed by reporting and loyalty features (`F4`, `F5`, `F6`).
* **System Independence:** The system operates as an independent, standalone web application and does not require complex integrations with third-party ERP systems or legacy enterprise databases, significantly reducing project complexity.

#### 2.4 Compatibility with Existing Infrastructure
*The compatibility with Jayraldine's Catering Services' existing technical infrastructure should be good.*

* **Hardware Compatibility:** Jayraldine's Catering Services operates without specialized server hardware. The proposed application is architected as a lightweight Progressive Web App that runs efficiently on standard consumer devices (desktop computers, laptops, tablets, and smartphones) via modern browsers (Chrome, Edge, Safari).
* **Network Connectivity:** The business already maintains broadband and mobile internet connectivity for managing Facebook customer inquiries. The web app is optimized for low-bandwidth consumption and responsive caching.
* **Printing & Peripheral Integration:** The system features built-in print stylesheets (`@media print`) to format operational kitchen worksheets (`F3.2`) and official billing receipts (`F2.2`), ensuring seamless compatibility with standard office printers currently owned by the client.

---

### 3. Technical Feasibility Summary Matrix

| Risk Dimension | Risk Level | Assessment & Justification | Mitigation Strategy |
|---|---|---|---|
| **Familiarity with Application** | **Moderately Low** | Thoroughly mapped operational workflows (`G-1`–`G-6`), but customized menu pricing and package add-ons require precise business logic. | Conduct weekly prototype validation with the sponsor to verify quotation calculations and package tier rules. |
| **Familiarity with Technology** | **Moderately Low** | Proponents have solid web development proficiency; client personnel possess basic smartphone and browser skills. | Develop an intuitive, tablet-optimized UI with simple navigation; conduct basic user training during initial deployment. |
| **Project Size** | **Low to Medium** | Four-member team building six core modules (`F1`–`F6`) within an academic semester timeframe. | Adopt an agile, iterative sprint schedule prioritizing core booking, billing, and scheduling modules (`F1`–`F3`) first. |
| **Compatibility with Infrastructure** | **Low** | Operates seamlessly on existing consumer hardware (PCs, tablets, smartphones) and standard desktop printers. | Ensure standard browser compliance, responsive design, and CSS print media styling without proprietary driver dependencies. |

---

### 4. Special Technical Considerations and Risk Mitigation
* **Budgetary Constraints:** Leverage open-source web frameworks (React, Next.js, Node.js) and zero-cost or low-cost cloud deployment solutions to eliminate expensive recurring licensing fees.
* **Data Loss Prevention (Addresses `G-2`):** Replace fragile physical clear book sleeves with automated database backups and export features (CSV/PDF) to guarantee disaster recovery.
* **Cross-Device Accessibility (Addresses `G-6`):** Implement responsive design so front-desk staff, kitchen crews, and on-site logistics handlers can access live schedule updates simultaneously from separate mobile/tablet devices.
* **Automated Arithmetic (Addresses `G-5`):** Eliminate manual calculation errors by enforcing automated formula computations for headcounts, equipment add-ons (Tiffany chairs, backdrops, sounds), and payment balance tracking.

---

### 5. Technical Feasibility Conclusion
Based on the comprehensive technical evaluation of application domain familiarity, development technology maturity, project scale, and infrastructure compatibility, the proposed Jayraldine's Catering Management System is deemed **TECHNICALLY FEASIBLE**. The technical risks identified are well understood, of low-to-moderate severity, and fully manageable through iterative agile delivery, user-friendly UI design, and standard web technologies.
