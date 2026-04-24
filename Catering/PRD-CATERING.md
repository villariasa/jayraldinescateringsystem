Improve my existing PySide6 UI with focus on ICON SYSTEM and THEME SUPPORT.

CRITICAL CONSTRAINTS:
- Do NOT change layout, structure, widget positions, or UI flow.
- Do NOT rewrite business logic.
- Only improve ICONS and ADD THEME SYSTEM.

---

PART 1: ICON SYSTEM UPGRADE
- Replace all default Qt icons with a modern icon set (Lucide or Tabler preferred).
- Use only ONE icon library (no mixing).
- Convert all QPushButton, QAction, toolbar, menu icons to SVG-based icons.
- Ensure consistent icon style (same stroke weight, minimal, modern SaaS look).
- Ensure icons are scalable and sharp on high DPI screens.
- Maintain consistent icon sizes (18px–24px).
- Remove all Qt default/system icons completely.

Implement:
- Central IconManager class or module
- Organized /icons directory structure
- Clean mapping system for icon usage

---

PART 2: THEME SYSTEM (LIGHT + DARK)

Create a theme system with TWO modes:
- Light Theme
- Dark Theme

IMPORTANT:
- Both themes must use the SAME base color palette family (just inverted brightness levels).
- Maintain consistent branding across both modes.

Design rules:
- Light theme: clean, soft, minimal contrast, modern UI
- Dark theme: deep neutral background, reduced eye strain, same accent colors
- Use consistent accent color across both themes (do NOT change brand identity)
- Ensure text readability and proper contrast ratios

Implementation requirements:
- Create a ThemeManager class
- Store themes as QSS (Qt Style Sheets)
- Allow runtime switching between Light and Dark mode
- Apply theme globally to QApplication

---

PART 3: STRUCTURE REQUIREMENTS
- Separate files:
  - theme.py (ThemeManager)
  - icons.py (IconManager)
- Clean reusable architecture
- Easy to extend in future

---

OUTPUT:
- Updated PySide6 code only for:
  - Icon system refactor
  - Theme system implementation
- Provide sample usage (how to switch theme + assign icons)



changes made , we dont need to have a an inventory since we are focusing in catering system so only menu , also pls dont remove the calendar part you remove it though pls dont remove the calendar part 



As a user, the current “Add Booking” experience is difficult and not intuitive.

Redesign and improve ONLY the booking creation flow to make it significantly more user-friendly, modern, and efficient.

---

🎯 OBJECTIVE:

Transform the “Add Booking” feature into a modern, guided modal-based interface that feels smooth, fast, and easy to use.

---

🧠 REQUIREMENTS:

1. Replace the current booking form/page with a MODAL WINDOW design
   - Do not use default or basic dialog styles
   - Must feel like a modern SaaS interface (not a basic popup)

2. The modal must include:
   - Step-by-step or structured form layout (not cluttered single page form)
   - Clear sections (Customer Info, Event Details, Menu Selection, Schedule, Notes)
   - Logical grouping of fields

3. UX IMPROVEMENTS:
   - Reduce cognitive load (no overwhelming long form)
   - Use progressive disclosure (show only relevant fields)
   - Add validation hints inline (not after submit only)
   - Show clear call-to-action buttons (Next, Back, Save Booking)

---

🎨 DESIGN REQUIREMENTS:

- Modern dark theme consistent with system UI
- Rounded corners (10px–16px)
- Soft shadows (no hard borders)
- Smooth transitions between steps
- Clean spacing system (8 / 16 / 24 px)
- Highlight active step clearly

---

⚡ INTERACTION DESIGN:

- Multi-step modal wizard OR structured sectioned modal
- Step indicator (progress bar or step numbers)
- Save progress before final submission
- Easy cancel/close without losing context

---

💎 VISUAL STYLE:

- Do NOT use default Qt dialog styling
- Use custom styled modal container
- Must match modern SaaS UI (Stripe / Notion style)
- Subtle hover effects and transitions
- Clean typography and hierarchy

---

🚀 GOAL:

Make booking creation feel:
- fast
- guided
- intuitive
- modern
- non-intimidating for users

The final result should dramatically improve usability compared to the current implementation.
