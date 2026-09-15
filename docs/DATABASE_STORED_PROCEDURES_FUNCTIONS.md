# PostgreSQL Stored Functions & Trigger Automations

## 1. Automated Invoice Trigger
```sql
CREATE OR REPLACE FUNCTION trg_update_invoice_balance()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE invoices
    SET inv_amount_paid = COALESCE((SELECT SUM(pr_amount) FROM payment_records WHERE pr_invoice_id = NEW.pr_invoice_id), 0.0),
        inv_balance = inv_total_amount - COALESCE((SELECT SUM(pr_amount) FROM payment_records WHERE pr_invoice_id = NEW.pr_invoice_id), 0.0),
        inv_status = CASE 
            WHEN (inv_total_amount - COALESCE((SELECT SUM(pr_amount) FROM payment_records WHERE pr_invoice_id = NEW.pr_invoice_id), 0.0)) <= 0 THEN 'Paid'::invoice_status
            WHEN COALESCE((SELECT SUM(pr_amount) FROM payment_records WHERE pr_invoice_id = NEW.pr_invoice_id), 0.0) > 0 THEN 'Partial'::invoice_status
            ELSE 'Unpaid'::invoice_status
        END
    WHERE inv_id = NEW.pr_invoice_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```
