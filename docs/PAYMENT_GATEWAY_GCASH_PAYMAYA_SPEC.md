# Digital Payment Gateway (QR Ph / GCash / Maya) Specifications

## 1. Payment Verification Flow
1. **Dynamic QR Generation**: Renders standard National QR Ph merchant code with embedded invoice reference and payable amount.
2. **Transaction Reference Capture**: Validates customer payment reference numbers (12-16 alphanumeric digits).
3. **Split Payment Processing**: Supports combined payment modes (e.g. ₱10,000 GCash + ₱5,000 Cash down payment).
4. **Ledger Auditing**: Automatically registers verified payments into the central `payment_records` table.
