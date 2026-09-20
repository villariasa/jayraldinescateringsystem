# Monthly Sales Evaluation Report Calculation Specification

## 1. Mathematical Model
In previous iterations, the Sales Evaluation Report aggregated `bookings.bk_total_amount`. In business reality, contracted booking totals represent **projected or committed revenue**, not cash in hand.

The updated formula calculates **Actual Sales** as:
$$\text{Actual Sales}(m, y) = \sum \text{payment\_records.pr\_amount}(m, y) + \sum \text{cash\_flow\_transactions.cft\_actual\_sales}(m, y)$$

## 2. Filtering Criteria
- Excludes cancelled bookings (`bk_status != 'Cancelled'`).
- Binds by payment transaction date (`pr_payment_date`), not initial event reservation date.
- Compares against targeted sales quotas to determine variance and achievement percentage.
