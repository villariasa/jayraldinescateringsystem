# AI Chef Jay Prompt Safety & Allergen Alerts Specification

## 1. Scope & Objective
Ensures AI Chef Jay operates safely within catering operational guidelines, avoiding prompt injections and cross-referencing culinary advice with dietary allergy constraints.

## 2. Rule Tiers
1. **Sanitization**: Strips raw system prompts, SQL injection sequences, and script delimiters.
2. **Allergen Alerting**: Automatically checks recommended ingredient lists against customer medical notes (e.g., nuts, shellfish, lactose, gluten).
3. **Budget Guardrails**: Enforces realistic wholesale portion margins and warns when generated menus exceed customer target per-head pricing.
