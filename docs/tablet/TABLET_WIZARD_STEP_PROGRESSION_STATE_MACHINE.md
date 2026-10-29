# Tablet Booking Wizard Finite State Machine Specification

> **Target Version:** v2.7.5  
> **Status:** Architecture Spec  
> **Date:** October 29, 2026  
> **Audience:** Frontend Developers, QA Automation

---

## 1. State Diagram
```
[ IDLE ] ──► [ STEP_PACKAGE ] ──► [ STEP_DATE_VENUE ] ──► [ STEP_MENU ] ──► [ STEP_SUMMARY ] ──► [ CONFIRMED ]
   ▲                                                                                                  │
   └─────────────────────────────── RESET / TIMEOUT ──────────────────────────────────────────────────┘
```

## 2. Transition Guard Rules
- `STEP_PACKAGE -> STEP_DATE_VENUE`: Requires `selectedPackageId != null` OR `selectedSetId != null`.
- `STEP_DATE_VENUE -> STEP_MENU`: Requires valid future event date, verified venue address, and guest count >= `min_pax`.
- `STEP_MENU -> STEP_SUMMARY`: In set mode, all dishes must be selected or accepted with no pending replacement slots.
