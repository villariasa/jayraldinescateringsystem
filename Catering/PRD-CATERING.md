You are a senior UI/UX engineer working on a PySide6 SaaS-style catering management system.

Improve the Notification system and Filter system using modern UI patterns.

---

🎯 OBJECTIVE:

Replace all modal-based interactions for Notifications and Filters with modern POPUP OVERLAY PANELS (Popover UI).

These panels must be anchored to their trigger buttons and NOT centered like modals.

---

## 🔔 NOTIFICATION SYSTEM (POPOVER)

When the user clicks the Notification button:

- Open a popover panel directly under the notification icon/button
- Do NOT use a modal dialog
- Do NOT block the full screen

Design requirements:
- Floating panel anchored to button position
- Soft shadow and rounded corners (10–14px)
- Dark SaaS theme (#111827 surface)
- Smooth fade/slide animation
- Close when clicking outside

Content inside notification popover:
- List of notifications
- Grouped by type (Orders, Payments, System)
- Timestamp display
- Read / Unread state
- Optional "Mark all as read" action

---

## 🔍 FILTER SYSTEM (POPOVER FILTER PANEL)

Replace all filter modals with a FILTER POPOVER PANEL.

When user clicks Filter button:

- Open a popover panel anchored to the filter button
- NOT centered modal
- NOT full screen overlay

Design requirements:
- Compact floating panel
- Clear grouping of filter options
- Apply / Reset buttons at bottom
- Smooth animation open/close
- Dark modern SaaS styling consistent with system UI

Filter features:
- Date range filter
- Status filter (dropdown or chips)
- Category filter (if applicable)
- Search refinement options

---

## 🎨 UI STYLE REQUIREMENTS

Both Notification and Filter popovers must:

- Use dark theme surface (#111827)
- Rounded corners (10px–14px)
- Subtle shadows (no harsh borders)
- Consistent spacing (8 / 16 / 24 px system)
- Smooth transition animation (150–250ms)
- Match SaaS dashboard style (Stripe / Notion inspired)

---

## ⚡ UX RULES

- Do NOT use modal dialogs for these features
- Panels must feel lightweight and fast
- Must close on outside click or ESC key
- Must not block full UI interaction
- Must feel like modern web SaaS popovers

---

🚀 FINAL GOAL:

Transform Notifications and Filters into modern popover-based interaction systems that improve usability, reduce friction, and make the UI feel responsive, fast, and professional.

also make sure no more laggy 
