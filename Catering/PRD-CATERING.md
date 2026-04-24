PRD: PySide6 UI/UX Modernization (Catering Business Edition)
1. Project Overview & Objective
Goal: Upgrade an existing PySide6 desktop application to a modern, premium aesthetic tailored for a catering business. The UI must feel clean, appetizing, professional, and efficient.
Strict Constraint: This is a purely visual overhaul. DO NOT alter core Python logic, DO NOT change the existing widget hierarchy, and DO NOT remove any functional features.

2. Theming & Visual Identity
The design language shifts from a dark tech dashboard to a crisp, hygienic, and energetic "Red and White" theme suited for the food and hospitality industry.

Color Palette (Clean Light Theme)
App Background (Base): #F8F9FA (A very soft, warm off-white to reduce eye strain while maintaining a clean look).

Surface/Panels: #FFFFFF (Pure white for cards, sidebars, and content areas to make them pop).

Primary Action/Brand Accent: #D32F2F (A rich, appetizing Crimson Red for primary buttons, active states, and highlights).

Secondary/Hover Accent: #B71C1C (A deeper, darker red for pressed states and hover feedback).

Primary Text: #212529 (Dark charcoal for maximum readability; never use pure black).

Secondary Text/Icons: #6C757D (Muted slate gray for placeholders and inactive elements).

Borders/Dividers: #DEE2E6 (Very light, subtle gray for structural separation).

Design Paradigms
Base Engine: Qt Fusion style must be enforced at the app level.

Geometry: Soft, approachable curves. 8px border-radius for small interactive elements; 12px to 16px for large structural panels (cards, sidebars).

Spacing System: Strict base-4 spacing (8px, 16px, 24px) for consistent breathing room and alignment.

Depth (Neumorphism-lite): Drop harsh borders on major layout containers. Use soft, highly diffused drop shadows (QGraphicsDropShadowEffect) to lift pure white cards off the off-white background.

3. Component-Level Styling Specifications
Navigation / Sidebar
Structure: Pure white #FFFFFF panel resting on the left.

Active Item: Needs to draw the eye instantly. Use a bold red left-border (4px solid #D32F2F), a very faint red background tint (e.g., rgba(211, 47, 47, 0.08)), and bold dark text.

Inactive Items: Charcoal text, transparent background.

Hover Feedback: Smooth transition to a light gray background (#F1F3F5) with a 6px border radius to keep it contained.

Buttons
Primary Buttons (e.g., "Create Order", "Confirm Catering"):

Background: #D32F2F (Crimson).

Text: Pure White, bold.

Corners: 8px radius.

Interactions: Hover brightens slightly; Pressed darkens to #B71C1C.

Secondary Buttons (e.g., "Cancel", "Edit"):

Background: #FFFFFF or #F8F9FA.

Border: 1px solid #DEE2E6.

Text: Charcoal #212529.

Interactions: Hover transitions border to Red #D32F2F and text to Red.

Inputs & Forms (Search, QLineEdit, QComboBox)
Default State: Flat white background, 8px radius, subtle light gray border (#DEE2E6).

Padding: Spacious (minimum 10px vertical, 14px horizontal) to prevent a cramped, legacy-software feel.

Focus State: When typing, the border must immediately snap to the primary Red (#D32F2F) to clearly indicate the active field.

Data Tables (Menus, Invoices, Client Lists)
General: Remove all heavy, legacy gridlines.

Headers: Pure white background, bold muted gray text, separated from data by a single 2px solid Red (#D32F2F) bottom border.

Rows: Alternating row colors are crucial for scanning large orders (#FFFFFF and #F8F9FA).

Selection: When a user clicks a row, highlight it with a very soft red tint (do not use harsh solid colors that obscure the text).

4. Implementation Rules & Architecture
QSS Modularity: All styling MUST be extracted into a central style.qss file. Absolutely no setStyleSheet spaghetti code injected randomly throughout the Python logic.

Shadow Helper: Since pure QSS can't do drop shadows, specify a single reusable Python utility function to apply QGraphicsDropShadowEffect to containers requiring depth (like the central dashboard cards).

Targeting: Use Qt Object Names (e.g., widget.setObjectName("PrimaryCard")) to map the QSS precisely without accidentally styling unintended nested widgets.


the file is the catering project to modify open it and find what your looking .
