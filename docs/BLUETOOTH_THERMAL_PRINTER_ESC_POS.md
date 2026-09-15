# ESC/POS Thermal Receipt Printer Specifications

## 1. Byte Sequence Protocol
- **Paper Width**: $58\text{mm}$ and $80\text{mm}$ standard thermal paper rolls.
- **Command Set**: Standard ESC/POS commands:
  - Initialize: `\x1B\x40`
  - Bold On/Off: `\x1B\x45\x01` / `\x1B\x45\x00`
  - Center Align: `\x1B\x61\x01`
  - Paper Cut: `\x1D\x56\x41\x10`
