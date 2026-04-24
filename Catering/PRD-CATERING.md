You are a senior UI/UX architect and PySide6 system designer.

I already have an existing catering management system. Your task is to MODERNIZE the entire UI/UX including layout structure, not just styling.

Do NOT break business logic or backend functionality. Only redesign interface, layout, visual hierarchy, and user experience flow.

The goal is to transform the system into a modern, premium, SaaS-level catering dashboard that feels fresh, fast, and exciting to use.

---

🎯 OVERALL DESIGN GOAL:

Create a modern catering management system inspired by:
- Stripe dashboard (clean SaaS finance UI)
- Notion (structured simplicity)
- Linear (fast workflow UX)

The system must feel:
- premium
- intuitive
- minimal but powerful
- visually modern
- workflow-driven

---

🎨 DESIGN SYSTEM (STRICT THEME)

Primary Red:        #E11D48
Deep Red:           #9F1239
Soft Red Tint:      #FFE4E6
Accent Gold:        #F59E0B

Background:         #0B1220
Surface:            #111827
Hover Surface:      #1F2937
Borders:            #243244

Text Primary:       #F9FAFB
Text Secondary:     #9CA3AF
Muted Text:         #6B7280

Success:            #22C55E
Warning:            #FACC15
Error:              #EF4444
Info:               #3B82F6

---

🧠 GLOBAL UX PRINCIPLES:

- Red is ONLY for actions, highlights, and active states
- Dark neutral background for structure
- Use spacing > decoration
- Replace borders with soft shadows
- Use rounded corners (8px–16px)
- Maintain consistent spacing system (8 / 16 / 24 / 32 px)
- Reduce clutter, increase clarity

---

🏗️ COMPLETE LAYOUT REDESIGN (IMPORTANT)

Redesign the entire application layout into a modern SaaS dashboard structure:

---

1. 🧭 SIDEBAR NAVIGATION (LEFT PANEL)

- Fixed vertical sidebar
- Dark background (#0B1220)
- Includes:
  - Dashboard
  - Orders / Events
  - Customers
  - Menu Management
  - Inventory
  - Kitchen
  - Billing
  - Reports
  - Settings

Design rules:
- Active item = red background (#E11D48)
- Hover = soft red tint (#FFE4E6 with opacity)
- Icons + labels aligned
- Clean spacing between items
- Collapsible sidebar (icon-only mode optional)

---

2. 🧾 TOP BAR (HEADER)

- Minimal top navigation
- Shows:
  - Page title
  - Search bar
  - Notifications icon
  - User profile menu

Design rules:
- No heavy borders
- Subtle divider line only
- Clean spacing
- Lightweight feel

---

3. 📊 MAIN DASHBOARD AREA

Use card-based layout system:

Include:
- Revenue summary cards
- Active orders status
- Upcoming events
- Inventory alerts
- Recent transactions

Card design:
- Surface: #111827
- Rounded corners: 14px
- Soft shadow
- Hover lift effect
- Clear hierarchy inside each card

---

4. 📦 WORKFLOW MODULE LAYOUT (VERY IMPORTANT)

Each module (Orders, Billing, Inventory, etc.) must follow this structure:

A. Header section
- Title
- Action buttons (Add, Export, Filter)

B. Content area
- Table or cards view
- Clean spacing

C. Side panel (optional modern UX)
- Details panel slides in when item is clicked

---

5. 🧾 TABLE MODERNIZATION

- Remove harsh grid lines
- Subtle row separation
- Hover highlight
- Sticky header
- Clean typography
- Status badges (colored pills)

---

6. 🧍 USER EXPERIENCE FLOW

Redesign navigation flow to feel natural:

Example:
Dashboard → Select Order → View Details → Assign Kitchen → Track Status → Billing → Completed

Add:
- clear status indicators
- step-based progression UI where needed
- minimal clicks for core actions

---

7. ✨ MODERN UI EFFECTS

- Hover transitions (150–250ms)
- Soft shadows instead of borders
- Subtle glow on active elements
- Smooth state changes
- No heavy animations

---

8. 🔐 ROLE-BASED UI FEEL

Different UI emphasis depending on role:

Admin:
- full dashboard access
- analytics visible

Staff:
- limited navigation
- task-focused UI

Kitchen:
- queue-based UI (simple, large status cards)

Finance:
- billing + reports focused UI

---

📦 OUTPUT REQUIREMENTS:

- Redesign full layout structure
- Improve all PySide6 UI components
- Provide updated QSS stylesheet
- Suggest new layout hierarchy if needed
- Keep backend logic untouched
- Ensure system feels modern, fast, and premium

---

🚀 FINAL GOAL:

Transform the existing catering system into a modern SaaS-level application with a clean dashboard layout, intuitive workflow, and premium visual identity that makes users feel excited to use it.
You are a senior software architect and product engineer.

Your task is to design a complete, production-ready PRD (Product Requirements Document) and implementation checklist for a Catering Service Management System.

This system must be fully functional, modular, and scalable. Do not focus on UI only. Focus on real-world operations, workflows, data integrity, and system completeness.

---

CORE OBJECTIVE:
Build a fully working catering management system that supports end-to-end operations from customer inquiry to billing, reporting, and administration.

---

STEP 1: SYSTEM ANALYSIS

Start by analyzing and defining:
- Business goals of a catering service system
- Core users (Admin, Staff, Kitchen, Finance, Client)
- Key workflows (booking → preparation → delivery → billing)
- System boundaries (what is included vs not included)

---

STEP 2: MODULE BREAKDOWN (MANDATORY)

Identify ALL required modules. Include and expand if missing:

1. User & Role Management
- authentication
- role-based access control (RBAC)
- permissions per module

2. Customer Management
- customer profiles
- contact history
- event history

3. Catering Orders / Booking System
- event booking
- menu selection
- scheduling
- guest count management
- event status tracking

4. Menu Management
- menu categories
- package deals
- pricing rules
- custom menu builder

5. Inventory Management
- ingredients tracking
- stock deduction per order
- low stock alerts

6. Kitchen Operations Module
- order preparation queue
- task assignment
- preparation status tracking

7. Delivery & Logistics Module
- delivery scheduling
- driver assignment
- delivery status tracking

8. Billing & Payments
- invoice generation
- breakdown of charges
- VAT, discounts, penalties
- payment tracking
- partial/full payment support

9. Accounting / Financial Module
- revenue tracking
- expenses tracking
- reports (daily, monthly, yearly)

10. Reporting & Analytics
- sales reports
- popular menus
- customer trends
- operational performance

11. Notifications System
- email/SMS notifications
- booking confirmations
- reminders

12. Audit Logs
- system activity tracking
- user action logs

---

STEP 3: DATA MODEL DESIGN

Define:
- all major tables
- relationships (ERD-level explanation)
- primary keys and foreign keys
- normalization rules

---

STEP 4: WORKFLOW DESIGN

Describe full lifecycle flows:
- Customer booking flow
- Order approval flow
- Kitchen preparation flow
- Delivery flow
- Billing and payment flow

Include:
- state transitions
- status enums
- edge cases

---

STEP 5: SYSTEM ARCHITECTURE

Define:
- frontend structure (PySide6 / web / hybrid)
- backend architecture (API design if needed)
- database design (MySQL/PostgreSQL)
- modular separation
- scalability considerations

---

STEP 6: IMPLEMENTATION CHECKLIST

Provide a detailed checklist:

- Database setup complete
- Tables created with constraints
- Modules implemented one by one
- API endpoints (if applicable)
- UI screens mapped per module
- Role-based access tested
- Billing logic validated
- Inventory deduction verified
- Reports tested with sample data
- End-to-end workflow testing

---

STEP 7: VALIDATION RULES

Include:
- data validation rules
- business rule enforcement
- error handling strategy
- consistency checks (e.g., stock cannot go negative)

---

FINAL OUTPUT REQUIREMENT:

Deliver:
1. Full PRD document
2. Module breakdown (complete and expanded)
3. Database schema design overview
4. System workflow diagrams in text form
5. Step-by-step implementation checklist
6. Missing modules if any must be identified and added automatically

---

GOAL:
This system must be production-grade, not prototype-level. Ensure completeness, scalability, and real-world usability.
