# Multi-Terminal Concurrency & Conflict Resolution Guide

## 1. Optimistic Locking Protocol
Tables prone to concurrent edits (`bookings`, `inventory_items`, `menu_packages`) maintain an integer `version` column.

## 2. Collision Handling
- When submitting an update, the SQL query executes `WHERE id = :id AND version = :expected_version`.
- If affected rows == 0, a concurrency conflict is detected.
- The application fetches the newest record, displays a diff dialog to the operator, and provides options to Merge, Overwrite, or Discard.
