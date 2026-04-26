Product Requirements Document (PRD) Action Checklist
1. Real-Time Systems & Notifications (Priority Focus)
This section addresses the live clock, countdown timers, and scheduled notification triggers.

[x] Global Real-time Clock: Implement a live running clock in the top navigation or header of the app (updates every second without refreshing).

[x] Live Event Countdowns: On the dashboard/e vents page, display a live "Countdown Timer" for upcoming events (e.g., "Starts in 00:59:00").

[x] Notification Scheduler (Backend): Implement a timed job/cron scheduler on the backend to constantly check upcoming event dates against the current time.

[x] 1-Day & 1-Minute Triggers: Set up the scheduler to push notifications out exactly 1 day before an event, and 1 minute before an event.

[x] Dynamic Notification UI: Ensure the notification dropdown updates dynamically (using WebSockets or polling) rather than just displaying a static timestamp from when the page was loaded.

[x] Fix "Mark as Read" Badge: Fix the state management bug where clicking "Mark as read all" clears the list but fails to reset the unread badge count to 0 in the database and UI.

2. Status Workflow & Filtering
[x] Status Dropdown Logic: Fix the dropdown to enable status selection.

[x] Terminal Status Locking: Implement business logic (both UI disabled state and backend validation) so that if a status is currently Cancelled or Confirmed, it cannot be changed.

[x] Pending Status Unlocking: Ensure only items with a Pending status can be transitioned to Cancelled or Confirmed.

[x] Visibility of Approvals: Add clear, visible action buttons (e.g., "Approve", "Decline") directly on the main table rows or detail views so the user knows exactly where to update statuses.

[x] Filter Radio/Select Fix: Update the filter UI to restrict selection to exactly one option at a time (All, Pending, Confirmed, Cancelled). Use a standard <select> dropdown or mutually exclusive radio buttons instead of multi-select checkboxes.

3. Customer & Billing Flow Redesign
[x] Customer Creation Isolation: Remove inline customer creation from the Orders module. Users must explicitly create a customer in the Customers Module first.

[x] Customer Module Fixes: Ensure the "Export" functionality in the Customers module works (check CSV/Excel generation logic).

[x] Order/Billing Search & Select: In the Orders/Billing UI, replace manual customer text inputs with a searchable dropdown (Select2/Autocomplete) that fetches from the Customers database.

[x] Read-Only Auto-Populate: Upon selecting a customer, auto-fill their details (Name, Contact, Address) in read-only fields.

[x] Billing CRUD (Edit/Delete): Add an "Edit" and "Delete" button to the Billing module. Allow updating of specific fields: Status, Total Amount, and Amount Paid.

[x] Invoice Date Picker: On the "New Invoice" modal, change the Event Date text input to a native Date Picker (<input type="date">).

[x] Invoice Database Type: Ensure the event_date column in the database is strictly set to a DATE or DATETIME format.

4. Menu & Calendar Modules
[x] Menu Edit Functionality: Add an "Edit Menu" modal/page. Allow the user to update the Menu Name, Description, Price, Status (Available/Unavailable), and Image. Ensure this patches the existing database record rather than just relying on the Delete function.

[x] Calendar Data Persistence: Fix the database hookup for the Calendar module. When an event or booking is created, ensure an INSERT SQL query fires to save it to the database so it persists after closing the app. Ensure the calendar fetches (SELECT) these records on load.

5. Reports & Polish
[x] Live Report Queries: Ensure all charts and report metrics run live database queries on page load (avoid caching outdated data).

[x] Text Truncation: Apply CSS text truncation to the "Top Selling Menu" descriptions so long texts are cut off with an ellipsis (...) and don't break the UI layout (e.g., white-space: nowrap; overflow: hidden; text-overflow: ellipsis;).

6. Dashboard Live DB Data
[x] Dashboard DB-Driven Data: All dashboard cards (KPIs, Daily Capacity, Upcoming Events, Recent Activity, Menu Alerts) must load from live database queries. Added v_recent_activity and v_menu_alerts views and corresponding repo functions. Dashboard auto-refreshes every 60 seconds. No hardcoded/fake data anywhere on the dashboard.


