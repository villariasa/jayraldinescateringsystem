# Event Calendar Conflict Resolution Specification

## 1. Venue & Slot Management
The calendar engine monitors booking density across dates, venues, and equipment allocations.

## 2. Conflict Rules
- **Double Booking Guard**: Flags warning if the same venue hall is assigned to multiple events with overlapping event windows.
- **Buffer Times**: Enforces mandatory 3-hour turnaround buffers between events for cleaning and setup.
- **Capacity Caps**: Prevents total daily guest pax across all concurrent events from exceeding commissary cooking capacity (max 1,500 pax/day).
