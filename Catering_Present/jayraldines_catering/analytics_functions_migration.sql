-- =============================================================================
-- ANALYTICS FUNCTIONS MIGRATION
-- Year-parameterized reporting functions. The old current-year-only views
-- (v_monthly_income, v_profit_summary) are kept untouched; these functions
-- unlock historical queries, weekly rollups, and year-vs-year comparisons
-- for the Dashboard period toggle, Reports year selector, and the AI page.
--
-- Apply with:
--   psql -U <user> -d jayraldines_catering -f analytics_functions_migration.sql
-- =============================================================================

-- -----------------------------------------------------------------------------
-- fn_available_years: every year that has invoice or expense data, newest first
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_available_years()
RETURNS TABLE (year INT)
LANGUAGE sql STABLE AS $$
    SELECT DISTINCT y FROM (
        SELECT EXTRACT(YEAR FROM inv_event_date)::INT AS y FROM invoices
        UNION
        SELECT EXTRACT(YEAR FROM exp_expense_date)::INT AS y FROM expenses
    ) years
    ORDER BY y DESC;
$$;

-- -----------------------------------------------------------------------------
-- fn_monthly_income: revenue/paid per month for a given year
-- (parameterized version of v_monthly_income)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_monthly_income(p_year INT)
RETURNS TABLE (
    month_label   TEXT,
    month_num     INT,
    total_revenue FLOAT,
    total_paid    FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        TO_CHAR(inv_event_date, 'Mon')             AS month_label,
        EXTRACT(MONTH FROM inv_event_date)::INT    AS month_num,
        COALESCE(SUM(inv_total_amount), 0)::FLOAT  AS total_revenue,
        COALESCE(SUM(inv_amount_paid), 0)::FLOAT   AS total_paid
    FROM invoices
    WHERE EXTRACT(YEAR FROM inv_event_date) = p_year
    GROUP BY month_label, month_num
    ORDER BY month_num;
$$;

-- -----------------------------------------------------------------------------
-- fn_profit_summary: revenue / expense / net profit per month for a given year
-- (parameterized version of v_profit_summary)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_profit_summary(p_year INT)
RETURNS TABLE (
    month_num     INT,
    month_label   TEXT,
    revenue       FLOAT,
    total_expense FLOAT,
    net_profit    FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        COALESCE(m.month_num, e.month_num)                                         AS month_num,
        COALESCE(m.month_label, TO_CHAR(TO_DATE(e.month_num::TEXT, 'MM'), 'Mon'))  AS month_label,
        COALESCE(m.revenue, 0)::FLOAT                                              AS revenue,
        COALESCE(e.total_expense, 0)::FLOAT                                        AS total_expense,
        (COALESCE(m.revenue, 0) - COALESCE(e.total_expense, 0))::FLOAT             AS net_profit
    FROM (
        SELECT EXTRACT(MONTH FROM inv_event_date)::INT AS month_num,
               TO_CHAR(inv_event_date, 'Mon') AS month_label,
               SUM(inv_total_amount) AS revenue
        FROM invoices
        WHERE EXTRACT(YEAR FROM inv_event_date) = p_year
        GROUP BY month_num, month_label
    ) m
    FULL OUTER JOIN (
        SELECT EXTRACT(MONTH FROM exp_expense_date)::INT AS month_num,
               SUM(exp_amount) AS total_expense
        FROM expenses
        WHERE EXTRACT(YEAR FROM exp_expense_date) = p_year
        GROUP BY month_num
    ) e ON m.month_num = e.month_num
    ORDER BY COALESCE(m.month_num, e.month_num);
$$;

-- -----------------------------------------------------------------------------
-- fn_weekly_summary: revenue / expense / profit per week of a given month
-- Week 1 = days 1-7, week 2 = 8-14, etc. (week-of-month keeps labels stable)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_weekly_summary(p_year INT, p_month INT)
RETURNS TABLE (
    week_num      INT,
    week_label    TEXT,
    revenue       FLOAT,
    total_expense FLOAT,
    net_profit    FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        w                                                             AS week_num,
        'Week ' || w                                                  AS week_label,
        COALESCE(r.revenue, 0)::FLOAT                                 AS revenue,
        COALESCE(e.total_expense, 0)::FLOAT                           AS total_expense,
        (COALESCE(r.revenue, 0) - COALESCE(e.total_expense, 0))::FLOAT AS net_profit
    FROM generate_series(1, 5) w
    LEFT JOIN (
        SELECT ((EXTRACT(DAY FROM inv_event_date)::INT - 1) / 7) + 1 AS week_num,
               SUM(inv_total_amount) AS revenue
        FROM invoices
        WHERE EXTRACT(YEAR FROM inv_event_date) = p_year
          AND EXTRACT(MONTH FROM inv_event_date) = p_month
        GROUP BY 1
    ) r ON r.week_num = w
    LEFT JOIN (
        SELECT ((EXTRACT(DAY FROM exp_expense_date)::INT - 1) / 7) + 1 AS week_num,
               SUM(exp_amount) AS total_expense
        FROM expenses
        WHERE EXTRACT(YEAR FROM exp_expense_date) = p_year
          AND EXTRACT(MONTH FROM exp_expense_date) = p_month
        GROUP BY 1
    ) e ON e.week_num = w
    ORDER BY w;
$$;

-- -----------------------------------------------------------------------------
-- fn_yearly_summary: revenue / expense / profit per year (all history)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_yearly_summary()
RETURNS TABLE (
    year          INT,
    revenue       FLOAT,
    total_expense FLOAT,
    net_profit    FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT
        COALESCE(r.year, e.year)                                       AS year,
        COALESCE(r.revenue, 0)::FLOAT                                  AS revenue,
        COALESCE(e.total_expense, 0)::FLOAT                            AS total_expense,
        (COALESCE(r.revenue, 0) - COALESCE(e.total_expense, 0))::FLOAT AS net_profit
    FROM (
        SELECT EXTRACT(YEAR FROM inv_event_date)::INT AS year,
               SUM(inv_total_amount) AS revenue
        FROM invoices GROUP BY 1
    ) r
    FULL OUTER JOIN (
        SELECT EXTRACT(YEAR FROM exp_expense_date)::INT AS year,
               SUM(exp_amount) AS total_expense
        FROM expenses GROUP BY 1
    ) e ON r.year = e.year
    ORDER BY COALESCE(r.year, e.year);
$$;

-- -----------------------------------------------------------------------------
-- fn_expense_breakdown: expense totals per category for a year
-- (p_month optional: pass NULL for the whole year)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_expense_breakdown(p_year INT, p_month INT DEFAULT NULL)
RETURNS TABLE (
    category TEXT,
    total    FLOAT
)
LANGUAGE sql STABLE AS $$
    SELECT exp_category::TEXT               AS category,
           COALESCE(SUM(exp_amount), 0)::FLOAT AS total
    FROM expenses
    WHERE EXTRACT(YEAR FROM exp_expense_date) = p_year
      AND (p_month IS NULL OR EXTRACT(MONTH FROM exp_expense_date) = p_month)
    GROUP BY exp_category
    ORDER BY total DESC;
$$;

-- -----------------------------------------------------------------------------
-- New expense categories for the dedicated Expenses page
-- (each ALTER must run outside an explicit transaction block)
-- -----------------------------------------------------------------------------
ALTER TYPE expense_category ADD VALUE IF NOT EXISTS 'Salary';
ALTER TYPE expense_category ADD VALUE IF NOT EXISTS 'Service';
