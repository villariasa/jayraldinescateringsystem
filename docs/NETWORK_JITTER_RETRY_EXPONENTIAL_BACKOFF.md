# Network Jitter Mitigation & Exponential Retry Backoff

## 1. Retry Algorithm
When network requests to `/api/sync/lan-sync` encounter transient packet loss:

$$t_{\text{wait}} = \min(t_{\max}, t_{\text{base}} \times 2^{\text{attempt}}) \pm \text{Jitter}$$

- **Base Interval ($t_{\text{base}}$)**: $500\text{ms}$
- **Maximum Ceiling ($t_{\max}$)**: $10,000\text{ms}$
- **Full Jitter**: Random uniform distribution $\pm 20\%$ to prevent synchronized retry stampedes.
