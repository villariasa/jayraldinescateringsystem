# Print Template Engine & Invoice Generation Guide

## 1. Template Rendering Engine
Uses Jinja2 HTML templates rendered to high-resolution vector PDF outputs via Qt's `QTextDocument` and `QPrinter` engines.

## 2. Standard Templates
- `contract_agreement.html`: Formal catering legal agreement with client signature blocks.
- `official_receipt.html`: BIR-compliant commercial sales receipt with tax breakdowns.
- `kitchen_prep_sheet.html`: Production schedule for kitchen chefs and sous chefs.
