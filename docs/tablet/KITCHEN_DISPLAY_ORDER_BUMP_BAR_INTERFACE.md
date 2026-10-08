# Kitchen Display System (KDS) Order Bump Bar Interface Specification

> **Target Version:** v4.2.5  
> **Status:** KDS Hardware Integration  
> **Date:** October 8, 2026  
> **Audience:** UI Developers, Commissary Engineers

---

## 1. Kitchen Environment Demands
Chefs and dish station leads cannot touch glass tablet screens with greasy or flour-dusted hands.

## 2. Physical Bump Bar Key Bindings
Standard USB/Bluetooth 10-key industrial bump bars map to KDS events:

| Key Code | Function | Action |
|---|---|---|
| `KEY_1` to `KEY_8` | Select Order Slot 1–8 | Highlights active booking card |
| `KEY_ENTER` | Bump Order | Marks active stage complete (Prep → Cooked → Packed) |
| `KEY_RECALL` | Undo Last Bump | Restores bumped order to active display |
| `KEY_SCROLL_UP` | Page Up | Scrolls order ticket list upward |
| `KEY_SCROLL_DOWN` | Page Down | Scrolls order ticket list downward |
