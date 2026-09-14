# Audit Log Cryptographic Tamper-Proofing Specifications

## 1. Chaining Mechanism
Each audit log entry computes a cryptographic SHA-256 HMAC hash binding the current event to the preceding log entry:

$$\text{Hash}_{n} = \text{HMAC-SHA256}(\text{Secret}, \text{Hash}_{n-1} \parallel \text{Timestamp} \parallel \text{User} \parallel \text{Action} \parallel \text{Payload})$$

- **Integrity Verification**: Nightly verification job alerts administrators if any intermediate log row is modified or deleted.
