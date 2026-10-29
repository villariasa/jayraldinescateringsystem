# REST Sync API v3 Rate Limiting, Token Bucket & Security Policies

> **Target Version:** v2.7.5  
> **Status:** API Security Standard  
> **Date:** October 29, 2026  
> **Audience:** Backend Engineers, Security Architects

---

## 1. Token Bucket Rate Limiting Architecture
To safeguard commissary backend servers from rogue sync polling loops:
- **Kiosk Tablets:** 120 requests / minute burst capacity, replenishing at 2 tokens / second.
- **Admin Desktop Terminals:** 300 requests / minute.

## 2. Header Contract
- `X-RateLimit-Limit`: Maximum requests per window.
- `X-RateLimit-Remaining`: Remaining allowance.
- `X-RateLimit-Reset`: Unix timestamp until full replenishment.
- HTTP `429 Too Many Requests` triggers exponential backoff on tablet sync clients.
