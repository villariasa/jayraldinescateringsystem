# Package Zero-Cost Pricing & Complimentary Inclusions Specification

## 1. Requirement
Catering packages frequently feature complimentary inclusions (e.g., Free Dessert Station, Free 1 Lechon Belly Promo, Free Chafing Dish Rental).

## 2. Validation Adjustments
- `QDoubleSpinBox` minimum limit lowered from `0.01` to `0.00`.
- Database schemas verified to allow `price_per_pax = 0.00` without triggering zero-division errors during package aggregation.
- Invoices render ₱0.00 line items explicitly marked with a `[COMPLIMENTARY]` badge.
