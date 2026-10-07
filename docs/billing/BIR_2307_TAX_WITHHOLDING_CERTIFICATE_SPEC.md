# BIR Form 2307 Creditable Withholding Tax (CWT) Specification

> **Target Version:** v4.2.4  
> **Status:** Approved / Active Specification  
> **Date:** October 7, 2026  
> **Component:** Billing Module, Tax Engine, Accounting Integration

---

## 1. Legal Background
Corporate clients (Top Withholding Agents in the Philippines) are legally mandated by the Bureau of Internal Revenue (BIR) to withhold creditable income tax from catering suppliers:
- **Expanded Withholding Tax (EWT):** 2% for purchase of services / catering.

---

## 2. Calculation Schema

$$	ext{Gross Billing} = 	ext{PHP } 100,000.00$$
$$	ext{VAT Base (Net of 12\% VAT)} = rac{100,000}{1.12} = 	ext{PHP } 89,285.71$$
$$	ext{2\% Withholding (BIR 2307)} = 89,285.71 	imes 0.02 = 	ext{PHP } 1,785.71$$
$$	ext{Net Cash Payable by Client} = 100,000.00 - 1,785.71 = 	ext{PHP } 98,214.29$$

---

## 3. System Invoicing Fields
- Checkbox: `[x] Deduct 2% Withholding Tax (BIR Form 2307 Certificate Required)`
- System generates receipt showing Withholding Tax Credit deduction upon certificate upload.\n