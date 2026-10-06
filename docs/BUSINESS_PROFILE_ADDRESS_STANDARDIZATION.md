# Business Profile Canonical Address & Contact Information Standards

> **Target Version:** v4.2.3  
> **Status:** Approved / Active Specification  
> **Date:** October 6, 2026  
> **Component:** Business Profile, PDF Templates, Receipts, System Config

---

## 1. Specification Overview

Printed invoices, receipts, contracts, and tablet outputs reference the official commissary headquarters for Jayraldine's Catering Services.

Historical typographical variances (such as `"518 Y Rama Ave."` instead of the correct Cebu City street name `"518 V. Rama Ave."`) have been identified and formally corrected across all desktop and mobile assets.

---

## 2. Canonical Business Information Constants

```json
{
  "business_name": "JAYRALDINE'S CATERING SERVICES",
  "business_title": "Jayraldine's Catering Services",
  "street_address": "518 V. Rama Ave.",
  "barangay": "Guadalupe / Calamba",
  "city": "Cebu City",
  "province": "Cebu",
  "postal_code": "6000",
  "primary_phone": "+63 912 345 6789",
  "email": "inquiries@jayraldinescatering.com",
  "official_tagline": "Exceptional Culinary Elegance for Every Occasion"
}
```

---

## 3. Propagation Across Artifacts

All receipt generators pull from these canonical constants:
1. `Catering_Present/jayraldines_catering/utils/exporter.py`
2. `Catering_Present/jayraldines_catering/components/order_print_dialog.py`
3. `Tablet_Android_APK/app/src/main/assets/js/exporter.js`
4. `Tablet_PWA/frontend/js/exporter.js`
