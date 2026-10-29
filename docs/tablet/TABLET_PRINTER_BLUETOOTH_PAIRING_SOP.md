# Tablet Kiosk Bluetooth Thermal Printer Pairing SOP

> **Target Version:** v2.7.5  
> **Status:** Standard Operating Procedure  
> **Date:** October 29, 2026  
> **Audience:** Field Technicians, Banquet Supervisors

---

## 1. Hardware Specifications
- **Printer Models:** 58mm / 80mm ESC/POS Mobile Bluetooth Thermal Printers (e.g., Rongta RPP02N, Zijiang ZJ-5805).
- **Supported Profiles:** SPP (Serial Port Profile) over Bluetooth 4.0 / BLE.

## 2. Pairing Sequence
1. Power on thermal printer with feed button held to verify self-test printout (baud rate: 9600, PIN: `0000` or `1234`).
2. On Android tablet, navigate to `Settings -> Connected Devices -> Pair New Device`.
3. Select printer serial name and enter PIN.
4. Open Jayraldine's Tablet Kiosk app -> navigate to `Settings -> Hardware -> Receipt Printer`.
5. Tap **Test Print Receipt** to verify ESC/POS byte handshake and logo rendering.
