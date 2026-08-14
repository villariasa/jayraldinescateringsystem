"""
Built-in AI assistant — written from scratch, ships inside the app.

No external services, no downloads, no API keys, no internet. It "studies
the system" live: every question is parsed by a hand-built natural-language
engine (intent routing + entity extraction + fuzzy keyword fallback, in
English and Cebuano), the answer is computed directly from the PostgreSQL
data through the repository layer, and comparison charts are returned as
specs the AI page renders with QtCharts.

Public contract (kept stable for ui/ai_page.py):
    ask(question) -> {"ok": bool, "answer": str, "chart": dict|None,
                      "action": dict|None, "error": str}
    execute_action(action) -> {"ok": bool, "message": str}

Actions: the assistant can also DO things — approve/cancel/complete bookings,
record payments, add expenses. It never writes directly from ask(); it returns
an `action` dict the UI shows with Confirm/Cancel buttons, and only
execute_action() (called on Confirm) touches the database.
"""
import re
import random
import calendar
from datetime import datetime, date, timedelta

import utils.repository as repo


# ─────────────────────────────────────────────────────────────────────────────
# Language layer
# ─────────────────────────────────────────────────────────────────────────────

# Cebuano / Tagalog → English concept mapping so uncle can ask in Bisaya
_SYNONYMS = {
    "pila": "how much", "tagpila": "how much", "magkano": "how much",
    "kinsa": "who", "sino": "who", "unsa": "what",
    "kita": "revenue", "halin": "revenue", "kinitaan": "revenue", "income": "revenue",
    "gasto": "expense", "gastos": "expense", "galastuhan": "expense",
    "ginansya": "profit", "tubo": "profit",
    "itandi": "compare", "ikumpara": "compare", "tandi": "compare",
    "karon": "this", "karong": "this", "ron": "this",
    "niaging": "last", "miaging": "last", "nakaraang": "last",
    "tuig": "year", "taon": "year",
    "bulan": "month", "buwan": "month",
    "semana": "week", "linggo": "week",
    "suki": "customer", "kustomer": "customer", "kliyente": "customer",
    "utang": "unpaid", "bayronon": "unpaid", "wala pa nabayran": "unpaid",
    "pinakadako": "highest", "pinaka": "top", "kinadak-an": "highest",
    "pinakagamay": "lowest", "kinagamyan": "lowest",
    "unsaon": "how to", "asa": "where", "giunsa": "how to",
    "pagkaon": "menu", "putahe": "menu",
    "kasal": "wedding", "kaadlawon": "birthday",
    "sweldo": "salary", "sahod": "salary",
    "tanan": "all", "kada": "per",
    "average": "average", "kasagaran": "average",
    "booking": "booking", "reserba": "booking", "order": "booking",
    "panghitabo": "event", "okasyon": "occasion",
    "lugar": "location", "dapit": "location",
    "bayad": "payment", "plete": "payment",
    "presyo": "price", "kantidad": "amount",
    "ihap": "count", "gidaghanon": "count",
}

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
    # Cebuano/Spanish-derived month names
    "enero": 1, "pebrero": 2, "marso": 3, "abril": 4, "mayo": 5, "hunyo": 6,
    "hulyo": 7, "agosto": 8, "setyembre": 9, "oktubre": 10, "nobyembre": 11,
    "disyembre": 12,
}

_MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_EXPENSE_CATEGORIES = ["food cost", "labor", "salary", "service",
                       "transport", "utilities", "equipment", "other"]

# Regex alternation of every recognized month name/abbreviation, longest-first
# so e.g. "september" matches before "sep" would truncate it.
_MONTH_NAME_ALT = "|".join(sorted(_MONTHS.keys(), key=len, reverse=True))

# Phrases that imply a specific relative or absolute date/period — reused by
# the "list expenses/bookings/invoices for <period>" intents below.
_RANGE_WORD_ALT = (r"today|yesterday|this week|last week|this month|last month"
                   r"|this year|last year|" + _MONTH_NAME_ALT)


def _normalize(question: str) -> str:
    q = question.lower()
    q = re.sub(r"[^\w\s\-']", " ", q)
    words = [_SYNONYMS.get(w, w) for w in q.split()]
    return " " + " ".join(words) + " "


def _peso(v: float) -> str:
    return f"₱{v:,.0f}"


def _money(v) -> float:
    """Parse '₱ 1,234' / '1234' / 1234 into a float."""
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"[\d,]+(?:\.\d+)?", str(v))
    return float(m.group(0).replace(",", "")) if m else 0.0


def _pct(new: float, old: float) -> str:
    if old <= 0:
        return ""
    change = (new - old) / old * 100
    word = "up" if change >= 0 else "down"
    return f" That's {word} {abs(change):.1f}% versus the earlier period."


def _safe(fn, default):
    try:
        result = fn()
        return default if result is None else result
    except Exception:
        return default


def _parse_date(s: str):
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Entity extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_years(q: str) -> list[int]:
    now = datetime.now().year
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", q)]
    if re.search(r"\blast year\b|\bprevious year\b", q) and (now - 1) not in years:
        years.append(now - 1)
    if re.search(r"\bthis year\b|\bcurrent year\b", q) and now not in years:
        years.append(now)
    return sorted(set(years))


def _extract_months(q: str) -> list[int]:
    months = []
    for name, num in _MONTHS.items():
        if re.search(rf"\b{name}\b", q) and num not in months:
            months.append(num)
    if re.search(r"\bthis month\b", q) and datetime.now().month not in months:
        months.append(datetime.now().month)
    if re.search(r"\blast month\b", q):
        m = datetime.now().month - 1 or 12
        if m not in months:
            months.append(m)
    return months


def _extract_month(q: str):
    months = _extract_months(q)
    return months[0] if months else None


def _extract_day(q: str):
    """'august 20' / '20 august' → (month, day)."""
    for name, num in _MONTHS.items():
        m = re.search(rf"\b{name}\s+(\d{{1,2}})\b", q) or re.search(rf"\b(\d{{1,2}})\s+{name}\b", q)
        if m:
            day = int(m.group(1))
            if 1 <= day <= 31:
                return num, day
    return None


def _extract_specific_dates(q: str) -> list[date]:
    """Every explicit 'March 5' / '5 March' / 'March 5, 2026' date mentioned,
    in the order they appear. Year defaults to the current year if omitted."""
    today = date.today()
    found = []
    for name, num in _MONTHS.items():
        for m in re.finditer(rf"\b{name}\s+(\d{{1,2}})(?:,?\s*(20\d{{2}}))?\b", q):
            day = int(m.group(1))
            year = int(m.group(2)) if m.group(2) else today.year
            if 1 <= day <= 31:
                try:
                    found.append((m.start(), date(year, num, day)))
                except ValueError:
                    pass
        for m in re.finditer(rf"\b(\d{{1,2}})\s+{name}(?:,?\s*(20\d{{2}}))?\b", q):
            day = int(m.group(1))
            year = int(m.group(2)) if m.group(2) else today.year
            if 1 <= day <= 31:
                try:
                    found.append((m.start(), date(year, num, day)))
                except ValueError:
                    pass
    found.sort(key=lambda t: t[0])
    dates: list[date] = []
    for _, d in found:
        if d not in dates:
            dates.append(d)
    return dates


def _week_bounds(weeks_ago: int = 0) -> tuple[date, date]:
    """Monday..Sunday for the current week (weeks_ago=0) or N weeks back."""
    today = date.today()
    start = today - timedelta(days=today.weekday() + 7 * weeks_ago)
    return start, start + timedelta(days=6)


def _resolve_range(q: str) -> tuple[date | None, date | None, str, str]:
    """Best-effort (start, end, label, granularity) for a date phrase in q —
    'today', 'yesterday', 'this week', 'last week', a specific 'March 5'
    (optionally with a year), 'this/last month', 'this/last year', or a bare
    month/year. granularity is one of 'day', 'week', 'month', 'year', or ''
    when nothing matched. Returns (None, None, '', '') on no match."""
    today = date.today()

    if re.search(r"\byesterday\b", q):
        d = today - timedelta(days=1)
        return d, d, "yesterday", "day"
    if re.search(r"\btoday\b", q):
        return today, today, "today", "day"

    dates_found = _extract_specific_dates(q)
    if dates_found:
        d = dates_found[0]
        return d, d, d.strftime("%b %d, %Y"), "day"

    if re.search(r"\blast week\b", q):
        start, end = _week_bounds(1)
        return start, end, "last week", "week"
    if re.search(r"\bthis week\b", q):
        start, end = _week_bounds(0)
        return start, end, "this week", "week"

    if re.search(r"\blast month\b", q):
        m = today.month - 1 or 12
        y = today.year if today.month != 1 else today.year - 1
        start = date(y, m, 1)
        end = date(y, m, calendar.monthrange(y, m)[1])
        return start, end, f"{_MONTH_LABELS[m - 1]} {y}", "month"
    if re.search(r"\bthis month\b", q):
        start = date(today.year, today.month, 1)
        end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        return start, end, f"{_MONTH_LABELS[today.month - 1]} {today.year}", "month"

    if re.search(r"\blast year\b|\bprevious year\b", q):
        y = today.year - 1
        return date(y, 1, 1), date(y, 12, 31), str(y), "year"
    if re.search(r"\bthis year\b|\bcurrent year\b", q):
        y = today.year
        return date(y, 1, 1), date(y, 12, 31), str(y), "year"

    months = _extract_months(q)
    years = _extract_years(q)
    if months:
        m = months[0]
        y = years[0] if years else today.year
        start = date(y, m, 1)
        end = date(y, m, calendar.monthrange(y, m)[1])
        return start, end, f"{_MONTH_LABELS[m - 1]} {y}", "month"
    if years:
        y = years[0]
        return date(y, 1, 1), date(y, 12, 31), str(y), "year"

    return None, None, "", ""


def _metric(q: str) -> str:
    if re.search(r"\bexpense|\bspend|\bspent\b|\bcost\b", q):
        return "expense"
    if re.search(r"\bprofit|\bnet\b|\bearn", q):
        return "profit"
    return "revenue"


_HONORIFICS_RE = re.compile(
    r"\b(atty|engr|dr|dra|capt|chef|mr|mrs|ms|sir|hon|fr|rev|ma'?am|prof|gen|col)\b\.?",
    re.IGNORECASE)


def _name_key(name: str) -> str:
    """Lowercased name with honorifics and punctuation removed, so
    'Fernando Gomez' matches 'Atty. Fernando Gomez'."""
    s = _HONORIFICS_RE.sub(" ", str(name))
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def _customer_matches(c: dict, q: str) -> bool:
    """Match a customer by (honorific-cleaned) name, contact digits, or email."""
    needle = _name_key(q)
    name = _name_key(c.get("name") or "")
    if name:
        if name in q or (needle and (needle in name or name in needle)):
            return True
        if any(len(p) >= 3 and re.search(rf"\b{re.escape(p)}\b", needle or q)
               for p in name.split()):
            return True
    # contact: any 4+ digit run of the query appearing in the stored number
    contact = re.sub(r"\D", "", str(c.get("contact") or ""))
    if contact and any(d in contact for d in re.findall(r"\d{4,}", q)):
        return True
    # email: any 4+ char token of the query appearing in the address
    email = (c.get("email") or "").lower()
    if email and any(t in email for t in re.findall(r"[\w.]{4,}", q.lower())
                     if not t.isdigit()):
        return True
    return False


def _find_customer(q: str):
    """Best single customer mentioned anywhere in the question."""
    customers = _safe(repo.get_all_customers_with_loyalty, [])
    needle = _name_key(q)
    exact = None
    for c in customers:
        name = _name_key(c.get("name") or "")
        if name and (name in q or (needle and needle == name)):
            exact = exact or c
    if exact:
        return exact
    hits = [c for c in customers if _customer_matches(c, q)]
    return hits[0] if hits else None


def _find_category(q: str):
    for cat in _EXPENSE_CATEGORIES:
        if cat in ("other", "service", "labor"):
            # too generic — require an expense context word
            if re.search(rf"\b{cat}\b", q) and re.search(r"expense|spend|spent|cost|paid", q):
                return cat
        elif re.search(rf"\b{cat}\b", q):
            return cat
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────────────────────

def _year_rows(year: int) -> list[dict]:
    return _safe(lambda: repo.get_profit_summary_for_year(year), [])


def _year_total(year: int, metric: str) -> float:
    return sum(r.get(metric, 0.0) for r in _year_rows(year))


def _month_value(year: int, month: int, metric: str) -> float:
    for r in _year_rows(year):
        if r.get("month_num") == month:
            return r.get(metric, 0.0)
    return 0.0


def _bookings() -> list[dict]:
    return _safe(repo.get_all_bookings, [])


def _bookings_in(year=None, month=None) -> list[dict]:
    out = []
    for b in _bookings():
        d = _parse_date(b.get("date", ""))
        if d is None:
            continue
        if year and d.year != year:
            continue
        if month and d.month != month:
            continue
        out.append(b)
    return out


def _metric_sum_in_range(start: date, end: date, metric: str) -> float:
    """Revenue/expense/profit summed from raw booking/expense records over
    [start, end] — used for week/day-level granularity the monthly profit
    summary view (_year_rows) can't provide."""
    expense = 0.0
    if metric in ("expense", "profit"):
        for e in _safe(repo.get_all_expenses, []):
            d = _parse_date(e.get("date", ""))
            if d and start <= d <= end:
                expense += float(e.get("amount", 0))
        if metric == "expense":
            return expense

    revenue = 0.0
    for b in _bookings():
        d = _parse_date(b.get("date", ""))
        if (d and start <= d <= end
                and str(b.get("status", "")).upper() in ("CONFIRMED", "COMPLETED")):
            revenue += float(b.get("total", 0))
    if metric == "profit":
        return revenue - expense
    return revenue


# ─────────────────────────────────────────────────────────────────────────────
# Answer builders
# ─────────────────────────────────────────────────────────────────────────────

def _answer_compare(q: str) -> dict:
    now = datetime.now().year
    metric = _metric(q)
    label = metric.capitalize()

    # This week vs last week
    if re.search(r"\bthis week\b", q) and re.search(r"\blast week\b", q):
        s1, e1 = _week_bounds(1)
        s2, e2 = _week_bounds(0)
        v1, v2 = _metric_sum_in_range(s1, e1, metric), _metric_sum_in_range(s2, e2, metric)
        answer = (f"{label} last week ({s1.strftime('%b %d')}–{e1.strftime('%b %d')}) was {_peso(v1)}, "
                  f"vs this week ({s2.strftime('%b %d')}–{e2.strftime('%b %d')} so far) at "
                  f"{_peso(v2)}.{_pct(v2, v1)}")
        chart = {"type": "bar", "title": f"{label}: Last Week vs This Week",
                 "labels": ["Last week", "This week"], "series": [{"name": label, "values": [v1, v2]}]}
        return {"ok": True, "answer": answer, "chart": chart, "error": ""}

    # Today vs yesterday
    if re.search(r"\btoday\b", q) and re.search(r"\byesterday\b", q):
        today_d = date.today()
        yest_d = today_d - timedelta(days=1)
        v1, v2 = _metric_sum_in_range(yest_d, yest_d, metric), _metric_sum_in_range(today_d, today_d, metric)
        answer = (f"{label} yesterday ({yest_d.strftime('%b %d')}) was {_peso(v1)}, vs today "
                  f"({today_d.strftime('%b %d')}) at {_peso(v2)}.{_pct(v2, v1)}")
        chart = {"type": "bar", "title": f"{label}: Yesterday vs Today",
                 "labels": ["Yesterday", "Today"], "series": [{"name": label, "values": [v1, v2]}]}
        return {"ok": True, "answer": answer, "chart": chart, "error": ""}

    # Two specific calendar dates ("compare March 5 vs March 12")
    specific_dates = _extract_specific_dates(q)
    if len(specific_dates) >= 2:
        d1, d2 = specific_dates[0], specific_dates[1]
        v1, v2 = _metric_sum_in_range(d1, d1, metric), _metric_sum_in_range(d2, d2, metric)
        answer = (f"{label} on {d1.strftime('%b %d, %Y')} was {_peso(v1)}, vs "
                  f"{d2.strftime('%b %d, %Y')} at {_peso(v2)}.{_pct(v2, v1)}")
        chart = {"type": "bar", "title": f"{label}: {d1.strftime('%b %d')} vs {d2.strftime('%b %d')}",
                 "labels": [d1.strftime("%b %d"), d2.strftime("%b %d")],
                 "series": [{"name": label, "values": [v1, v2]}]}
        return {"ok": True, "answer": answer, "chart": chart, "error": ""}

    years = _extract_years(q)
    months = _extract_months(q)

    # Two months → compare months (within one year)
    if len(months) >= 2:
        year = years[-1] if years else now
        m1, m2 = months[0], months[1]
        v1, v2 = _month_value(year, m1, metric), _month_value(year, m2, metric)
        n1, n2 = _MONTH_LABELS[m1 - 1], _MONTH_LABELS[m2 - 1]
        answer = (f"{label} in {n1} {year} was {_peso(v1)}, and {n2} {year} was "
                  f"{_peso(v2)}.{_pct(v2, v1)}")
        chart = {"type": "bar", "title": f"{label}: {n1} vs {n2} ({year})",
                 "labels": [n1, n2], "series": [{"name": label, "values": [v1, v2]}]}
        return {"ok": True, "answer": answer, "chart": chart, "error": ""}

    if len(years) >= 2:
        y_old, y_new = years[0], years[-1]
    elif len(years) == 1:
        y_old, y_new = (years[0], now) if years[0] != now else (now - 1, now)
    else:
        y_old, y_new = now - 1, now

    if months:
        month = months[0]
        m_name = _MONTH_LABELS[month - 1]
        v_old = _month_value(y_old, month, metric)
        v_new = _month_value(y_new, month, metric)
        answer = (f"{label} for {m_name} {y_old} was {_peso(v_old)}, while {m_name} {y_new} "
                  f"reached {_peso(v_new)}.{_pct(v_new, v_old)}")
        chart = {"type": "bar", "title": f"{m_name} {label}: {y_old} vs {y_new}",
                 "labels": [str(y_old), str(y_new)],
                 "series": [{"name": label, "values": [v_old, v_new]}]}
        return {"ok": True, "answer": answer, "chart": chart, "error": ""}

    t_old, t_new = _year_total(y_old, metric), _year_total(y_new, metric)
    by_m_old = {r["month_num"]: r.get(metric, 0.0) for r in _year_rows(y_old)}
    by_m_new = {r["month_num"]: r.get(metric, 0.0) for r in _year_rows(y_new)}
    answer = (f"Total {metric} in {y_old} was {_peso(t_old)}; in {y_new} it is {_peso(t_new)} "
              f"so far.{_pct(t_new, t_old)}")
    chart = {"type": "bar", "title": f"Monthly {label}: {y_old} vs {y_new}",
             "labels": _MONTH_LABELS,
             "series": [
                 {"name": str(y_old), "values": [by_m_old.get(m, 0.0) for m in range(1, 13)]},
                 {"name": str(y_new), "values": [by_m_new.get(m, 0.0) for m in range(1, 13)]},
             ]}
    return {"ok": True, "answer": answer, "chart": chart, "error": ""}


def _answer_best_month(q: str) -> dict:
    years = _extract_years(q)
    year = years[-1] if years else datetime.now().year
    metric = _metric(q)
    lowest = bool(re.search(r"\blowest\b|\bworst\b|\bweakest\b|\bleast\b|\bslowest\b", q))
    rows = _year_rows(year)
    if not rows or all(r.get(metric, 0.0) == 0 for r in rows):
        return {"ok": True, "chart": None, "error": "",
                "answer": f"I don't see any {metric} data recorded for {year} yet."}
    pick = (min if lowest else max)(rows, key=lambda r: r.get(metric, 0.0))
    word = "weakest" if lowest else "strongest"
    answer = (f"The {word} month for {metric} in {year} is {pick['month']} "
              f"with {_peso(pick.get(metric, 0.0))}.")
    chart = {"type": "bar", "title": f"Monthly {metric.capitalize()} — {year}",
             "labels": [r["month"] for r in rows],
             "series": [{"name": metric.capitalize(),
                         "values": [r.get(metric, 0.0) for r in rows]}]}
    return {"ok": True, "answer": answer, "chart": chart, "error": ""}


def _answer_trend(q: str) -> dict:
    """Monthly chart for one year ('show monthly revenue 2026')."""
    years = _extract_years(q)
    year = years[-1] if years else datetime.now().year
    metric = _metric(q)
    rows = _year_rows(year)
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No data recorded for {year} yet."}
    total = sum(r.get(metric, 0.0) for r in rows)
    best = max(rows, key=lambda r: r.get(metric, 0.0))
    answer = (f"{metric.capitalize()} for {year} totals {_peso(total)}, peaking in "
              f"{best['month']} at {_peso(best.get(metric, 0.0))}.")
    chart = {"type": "bar", "title": f"Monthly {metric.capitalize()} — {year}",
             "labels": [r["month"] for r in rows],
             "series": [{"name": metric.capitalize(),
                         "values": [r.get(metric, 0.0) for r in rows]}]}
    return {"ok": True, "answer": answer, "chart": chart, "error": ""}


def _answer_total(q: str) -> dict:
    metric = _metric(q)

    # Day/week-level phrasing ("today", "yesterday", "this week", "last week",
    # a specific date) needs raw-record sums — the monthly summary view can't
    # give that granularity.
    r_start, r_end, r_label, r_gran = _resolve_range(q)
    if r_gran in ("day", "week"):
        v = _metric_sum_in_range(r_start, r_end, metric)
        return {"ok": True, "chart": None, "error": "",
                "answer": f"{metric.capitalize()} for {r_label}: {_peso(v)}."}

    years = _extract_years(q)
    year = years[-1] if years else datetime.now().year
    month = _extract_month(q)
    if month:
        v = _month_value(year, month, metric)
        return {"ok": True, "chart": None, "error": "",
                "answer": f"{metric.capitalize()} for {_MONTH_LABELS[month - 1]} {year}: {_peso(v)}."}
    total = _year_total(year, metric)
    extra = ""
    if metric == "profit":
        rev = _year_total(year, "revenue")
        exp = _year_total(year, "expense")
        extra = f" (Revenue {_peso(rev)} − Expenses {_peso(exp)})"
    return {"ok": True, "chart": None, "error": "",
            "answer": f"Total {metric} for {year}: {_peso(total)}.{extra}"}


def _answer_expense_breakdown(q: str) -> dict:
    years = _extract_years(q)
    year = years[-1] if years else datetime.now().year
    month = _extract_month(q)
    rows = _safe(lambda: repo.get_expense_breakdown(year, month), [])
    if not rows:
        where = f"{_MONTH_LABELS[month - 1]} {year}" if month else str(year)
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No expenses recorded for {where} yet. Add them in the Expenses page."}
    total = sum(r["total"] for r in rows)
    top = rows[0]
    where = f"{_MONTH_LABELS[month - 1]} {year}" if month else str(year)
    answer = (f"Expenses for {where} total {_peso(total)}. The biggest category is "
              f"{top['category']} at {_peso(top['total'])} "
              f"({top['total'] / total * 100:.0f}% of the total).")
    chart = {"type": "bar", "title": f"Expenses by Category — {where}",
             "labels": [r["category"] for r in rows],
             "series": [{"name": "Amount", "values": [r["total"] for r in rows]}]}
    return {"ok": True, "answer": answer, "chart": chart, "error": ""}


def _answer_category_expense(q: str, category: str) -> dict:
    years = _extract_years(q)
    year = years[-1] if years else datetime.now().year
    month = _extract_month(q)
    rows = _safe(lambda: repo.get_expense_breakdown(year, month), [])
    where = f"{_MONTH_LABELS[month - 1]} {year}" if month else str(year)
    match = next((r for r in rows if r["category"].lower() == category), None)
    if match is None:
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No {category.title()} expenses recorded for {where}."}
    total = sum(r["total"] for r in rows)
    share = f" ({match['total'] / total * 100:.0f}% of all expenses)" if total else ""
    return {"ok": True, "chart": None, "error": "",
            "answer": f"{match['category']} expenses for {where}: {_peso(match['total'])}{share}."}


def _answer_customer(q: str, customer: dict) -> dict:
    name = customer.get("name", "")
    bookings = [b for b in _bookings() if (b.get("name") or "").lower() == name.lower()]
    total_spent = sum(_money(b.get("total", 0)) for b in bookings)
    today = date.today()
    upcoming = [b for b in bookings
                if (_parse_date(b.get("date", "")) or today) >= today
                and b.get("status") == "CONFIRMED"]
    parts = [f"{name} — loyalty tier: {customer.get('loyalty_tier', 'N/A')}, "
             f"{len(bookings)} confirmed/completed booking(s), "
             f"total value {_peso(total_spent)}."]
    if upcoming:
        nxt = min(upcoming, key=lambda b: _parse_date(b.get("date", "")) or today)
        parts.append(f"Next event: {nxt.get('date')} ({nxt.get('pax')} pax).")
    if customer.get("contact"):
        parts.append(f"Contact: {customer['contact']}.")
    parts.append("Full history is in the Customers page.")
    return {"ok": True, "chart": None, "error": "", "answer": " ".join(parts)}


def _answer_ledger(q: str, customer: dict) -> dict:
    entries = _safe(lambda: repo.get_customer_ledger(customer["id"]), [])
    if not entries:
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No ledger entries found for {customer['name']} yet — "
                          f"bookings, invoices, and payments will appear here "
                          f"automatically. Full detail is in Customers > Ledger."}
    total_debit = sum(e["debit"] for e in entries)
    total_credit = sum(e["credit"] for e in entries)
    balance = total_debit - total_credit
    recent = "; ".join(
        f"{e['entry_type']} {e['reference']} ({e['recorded_date']}): "
        f"{'+' + _peso(e['credit']) if e['entry_type'] == 'Payment' else _peso(e['debit'])}"
        for e in entries[:5])
    return {"ok": True, "chart": None, "error": "",
            "answer": f"{customer['name']}'s ledger — total charged {_peso(total_debit)}, "
                      f"total paid {_peso(total_credit)}, balance due {_peso(balance)}. "
                      f"Recent: {recent}. Full history is in Customers > Ledger."}


def _answer_last_contact(q: str, customer: dict) -> dict:
    log = _safe(lambda: repo.get_last_contact(customer["id"]), None)
    if not log:
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No recorded contact history for {customer['name']} yet — "
                          f"receipts, booking confirmations, and follow-ups sent "
                          f"through the app are logged here automatically."}
    kind = str(log["log_type"]).replace("_", " ")
    return {"ok": True, "chart": None, "error": "",
            "answer": f"Last contact with {customer['name']}: {kind} via "
                      f"{log['method']} on {log['created_at']} ({log['status']})."}


def _answer_communication_history(q: str, customer: dict) -> dict:
    logs = _safe(lambda: repo.get_communication_logs(customer["id"], limit=8), [])
    if not logs:
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No communication history recorded for {customer['name']} yet."}
    listing = "; ".join(
        f"{str(l['log_type']).replace('_', ' ')} via {l['method']} on {l['created_at']}"
        for l in logs)
    return {"ok": True, "chart": None, "error": "",
            "answer": f"Communication history with {customer['name']} "
                      f"({len(logs)} most recent): {listing}."}


def _answer_top_customers(q: str) -> dict:
    rows = _safe(repo.get_customer_order_frequency, [])
    rows = [r for r in rows if r.get("name") != "Others"][:5]
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No confirmed bookings yet, so there are no top customers to show."}
    listing = ", ".join(f"{r['name']} ({r['count']} bookings)" for r in rows)
    chart = {"type": "bar", "title": "Top Customers by Bookings",
             "labels": [r["name"] for r in rows],
             "series": [{"name": "Bookings", "values": [r["count"] for r in rows]}]}
    return {"ok": True, "chart": chart, "error": "",
            "answer": f"Your top customers are: {listing}. Full details are in the Customers page."}


def _answer_unpaid(q: str) -> dict:
    invoices = _safe(repo.get_all_invoices, [])
    unpaid = [i for i in invoices if str(i.get("status", "")).lower() != "paid"]
    if not unpaid:
        return {"ok": True, "chart": None, "error": "",
                "answer": "Good news — no unpaid invoices right now. Everything is collected."}
    total_due = sum(float(i.get("amount", 0)) - float(i.get("paid", 0)) for i in unpaid)
    top = sorted(unpaid, key=lambda i: float(i.get("amount", 0)) - float(i.get("paid", 0)),
                 reverse=True)[:5]
    listing = "; ".join(
        f"{i.get('customer', '?')} — {i.get('invoice', '')} "
        f"({_peso(float(i.get('amount', 0)) - float(i.get('paid', 0)))} due)"
        for i in top)
    return {"ok": True, "chart": None, "error": "",
            "answer": f"There are {len(unpaid)} unpaid invoice(s) with {_peso(total_due)} "
                      f"outstanding. Largest: {listing}. Manage them in the Billing page."}


def _answer_upcoming(q: str) -> dict:
    events = _safe(lambda: repo.get_upcoming_events(limit=5), [])
    if not events:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No upcoming events on the calendar. New bookings appear here automatically."}
    formatted_items = []
    for e in events:
        # v_upcoming_events returns raw prefixed columns (bk_customer_name,
        # bk_event_date, bk_pax) — accept aliased forms as fallbacks.
        name = (e.get("bk_customer_name") or e.get("customer_name")
                or e.get("name") or "Unknown")
        raw_d = e.get("bk_event_date") or e.get("event_date") or e.get("date")
        if hasattr(raw_d, "strftime"):
            date_str = raw_d.strftime("%b %d, %Y")
        else:
            date_str = str(raw_d or "TBD")
        pax = e.get("bk_pax") or e.get("pax") or 0
        occasion = e.get("bk_occasion") or e.get("occasion") or ""
        occ = f", {occasion}" if occasion else ""
        formatted_items.append(f"{name} on {date_str} ({pax} pax{occ})")
    listing = "; ".join(formatted_items)
    return {"ok": True, "chart": None, "error": "",
            "answer": f"Next events: {listing}. See the Calendar page for the full schedule."}


def _answer_events_on(q: str, month: int, day: int) -> dict:
    hits = []
    for b in _bookings():
        d = _parse_date(b.get("date", ""))
        if d and d.month == month and d.day == day:
            hits.append(b)
    label = f"{_MONTH_LABELS[month - 1]} {day}"
    if not hits:
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No bookings found on {label}."}
    listing = "; ".join(
        f"{b.get('name', '?')} ({b.get('pax', '?')} pax, {b.get('status', '')}, {b.get('date')})"
        for b in hits[:6])
    return {"ok": True, "chart": None, "error": "",
            "answer": f"On {label}: {listing}."}


def _answer_bookings_count(q: str) -> dict:
    years = _extract_years(q)
    year = years[-1] if years else None
    month = _extract_month(q)
    rows = _bookings_in(year, month) if (year or month) else _bookings()
    total_val = sum(_money(b.get("total", 0)) for b in rows)
    total_pax = sum(int(_money(b.get("pax", 0))) for b in rows)
    if month and not year:
        year = datetime.now().year
    where = ""
    if month:
        where = f" in {_MONTH_LABELS[month - 1]} {year}"
    elif year:
        where = f" in {year}"
    return {"ok": True, "chart": None, "error": "",
            "answer": f"There are {len(rows)} confirmed/completed booking(s){where}, "
                      f"serving {total_pax:,} pax with a total value of {_peso(total_val)}."}


def _answer_average(q: str) -> dict:
    years = _extract_years(q)
    year = years[-1] if years else None
    rows = _bookings_in(year) if year else _bookings()
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No bookings recorded yet, so I can't compute averages."}
    vals = [_money(b.get("total", 0)) for b in rows]
    paxs = [int(_money(b.get("pax", 0))) for b in rows]
    where = f" in {year}" if year else ""
    return {"ok": True, "chart": None, "error": "",
            "answer": f"Across {len(rows)} booking(s){where}: average value {_peso(sum(vals) / len(vals))}, "
                      f"average size {sum(paxs) // len(paxs)} pax."}


def _answer_biggest_booking(q: str) -> dict:
    years = _extract_years(q)
    year = years[-1] if years else None
    rows = _bookings_in(year) if year else _bookings()
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No bookings recorded yet."}
    big = max(rows, key=lambda b: _money(b.get("total", 0)))
    where = f" in {year}" if year else ""
    return {"ok": True, "chart": None, "error": "",
            "answer": f"The biggest booking{where} is {big.get('name', '?')} on {big.get('date')} "
                      f"— {big.get('pax')} pax, {_peso(_money(big.get('total', 0)))} "
                      f"({big.get('status', '')})."}


def _answer_today(q: str) -> dict:
    k = _safe(repo.get_dashboard_kpis, {})
    return {"ok": True, "chart": None, "error": "",
            "answer": f"Today: {k.get('todays_events', 0)} event(s), "
                      f"{k.get('todays_pax', 0)} pax booked, "
                      f"{k.get('pending_bookings', 0)} pending booking(s) to review, and "
                      f"{_peso(float(k.get('weekly_revenue', 0)))} revenue so far this week."}


def _answer_pending(q: str) -> dict:
    k = _safe(repo.get_dashboard_kpis, {})
    n = k.get("pending_bookings", 0)
    if not n:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No pending bookings — everything has been reviewed."}
    return {"ok": True, "chart": None, "error": "",
            "answer": f"There are {n} pending booking(s) waiting for review in the Orders page."}


def _followup_line(f: dict) -> str:
    return f"{f['customer_name']} — {f['note']} (due {f['date']})"


def _answer_follow_ups(q: str) -> dict:
    overdue = _safe(repo.get_overdue_follow_ups, [])
    if re.search(r"\bover ?due\b|\blate\b|\bmissed\b", q):
        if not overdue:
            return {"ok": True, "chart": None, "error": "",
                    "answer": "No overdue follow-ups — you're all caught up."}
        listing = "; ".join(_followup_line(f) for f in overdue[:8])
        return {"ok": True, "chart": None, "error": "",
                "answer": f"{len(overdue)} overdue follow-up(s): {listing}."}

    days = 0 if re.search(r"\btoday\b", q) else (
        1 if re.search(r"\btomorrow\b", q) else 7)
    upcoming = _safe(lambda: repo.get_upcoming_follow_ups(days), [])
    if not upcoming and not overdue:
        window = "today" if days == 0 else f"the next {days} day(s)"
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No follow-ups due {window}, and none overdue."}
    parts = []
    if overdue:
        parts.append(f"⚠ {len(overdue)} overdue: " +
                     "; ".join(_followup_line(f) for f in overdue[:5]))
    if upcoming:
        window = "today" if days == 0 else f"the next {days} day(s)"
        parts.append(f"Due within {window}: " +
                     "; ".join(_followup_line(f) for f in upcoming[:8]))
    return {"ok": True, "chart": None, "error": "", "answer": " ".join(parts)}


def _answer_notifications(q: str) -> dict:
    unread = _safe(repo.get_unread_notifications, [])
    if not unread:
        return {"ok": True, "chart": None, "action": None, "options": [], "error": "",
                "answer": "No unread notifications — you're all caught up."}
    listing = "; ".join(f"{n['title']}: {n['message']}" for n in unread[:8])
    options = [{"label": "Mark all as read", "send": "mark all notifications read"}]
    return {"ok": True, "chart": None, "action": None, "options": options, "error": "",
            "answer": f"You have {len(unread)} unread notification(s): {listing}."}


def _answer_daily_briefing(q: str) -> dict:
    k = _safe(repo.get_dashboard_kpis, {})
    overdue = _safe(repo.get_overdue_follow_ups, [])
    due_today = _safe(repo.get_todays_follow_ups, [])
    unread = _safe(repo.get_unread_notifications, [])
    invoices = _safe(repo.get_all_invoices, [])
    unpaid = [i for i in invoices if str(i.get("status", "")).lower() != "paid"]
    unpaid_total = sum(float(i.get("amount", 0)) - float(i.get("paid", 0)) for i in unpaid)

    parts = [
        f"Good day! Here's your briefing — "
        f"{k.get('todays_events', 0)} event(s) today ({k.get('todays_pax', 0)} pax), "
        f"{k.get('pending_bookings', 0)} pending booking(s) to review, "
        f"{_peso(float(k.get('weekly_revenue', 0)))} revenue this week."
    ]
    if unpaid:
        parts.append(f"{len(unpaid)} unpaid invoice(s) totaling {_peso(unpaid_total)}.")
    if overdue:
        parts.append(f"⚠ {len(overdue)} OVERDUE follow-up(s): " +
                     "; ".join(_followup_line(f) for f in overdue[:5]) + ".")
    if due_today:
        listing = "; ".join(f"{f['customer_name']} — {f['note']}" for f in due_today[:5])
        parts.append(f"{len(due_today)} follow-up(s) due today: {listing}.")
    if unread:
        parts.append(f"{len(unread)} unread notification(s) — ask \"notifications\" to see them.")
    if not (unpaid or overdue or due_today or unread):
        parts.append("Nothing else needs your attention right now.")
    return {"ok": True, "chart": None, "error": "", "answer": " ".join(parts)}


def _answer_greeting_and_mood(q: str) -> dict:
    """Answers daily greetings, time-of-day checks ('good morning', 'maayong buntag'),
    and mood/health questions ('how are you', 'are you tired') with live system DB analysis."""
    k = _safe(repo.get_dashboard_kpis, {})
    overdue = _safe(repo.get_overdue_follow_ups, [])
    due_today = _safe(repo.get_todays_follow_ups, [])
    invoices = _safe(repo.get_all_invoices, [])
    unpaid = [i for i in invoices if str(i.get("status", "")).lower() != "paid"]
    unpaid_total = sum(float(i.get("amount", 0)) - float(i.get("paid", 0)) for i in unpaid)

    todays_events = k.get("todays_events", 0)
    pending_bkg = k.get("pending_bookings", 0)
    monthly_rev = float(k.get("monthly_revenue", 0))
    monthly_exp = float(k.get("monthly_expenses", 0))
    profit = monthly_rev - monthly_exp

    hour = datetime.now().hour
    if hour < 12:
        tod_greeting = "Good morning! ☀️"
        bisaya_tod = "Maayong buntag!"
    elif hour < 18:
        tod_greeting = "Good afternoon! 🌤️"
        bisaya_tod = "Maayong hapon!"
    else:
        tod_greeting = "Good evening! 🌙"
        bisaya_tod = "Maayong gabi!"

    q_lower = q.lower()
    is_tired_ask = bool(re.search(r"\btired\b|\bsleepy\b|\bexhausted\b|\brest\b", q_lower))
    is_feeling_ask = bool(re.search(r"\bhow are you\b|\bfeeling\b|\bmood\b|\bkamusta\b|\bmusta\b|\bdoing\b", q_lower))

    options = []
    if unpaid or overdue:
        mood_text = (
            f"I'm feeling a bit busy and on high alert! 👨‍🍳⚡ "
            f"Our system database analysis shows **{len(unpaid)} unpaid invoice(s)** totaling **{_peso(unpaid_total)}** "
            f"and **{len(overdue)} overdue follow-up(s)**. "
            f"I won't rest until we get those balances collected and follow-ups checked!"
        )
        if unpaid:
            options.append({"label": f"Collect {len(unpaid)} Unpaid Invoices ({_peso(unpaid_total)})", "send": "unpaid invoices"})
        if overdue:
            options.append({"label": f"Check {len(overdue)} Overdue Follow-ups", "send": "follow-ups"})

    elif todays_events > 0 or pending_bkg > 0:
        mood_text = (
            f"I'm feeling energized and ready to cook! 🔥 "
            f"We have **{todays_events} event(s) today** and **{pending_bkg} pending booking(s)** waiting for your review. "
            f"My chef hat is spinning with excitement to get these catering packages served!"
        )
        if pending_bkg > 0:
            options.append({"label": f"Review {pending_bkg} Pending Bookings", "send": "pending bookings"})
        if todays_events > 0:
            options.append({"label": "View Today's Events", "send": "today"})

    elif profit > 0 or monthly_rev > 0:
        mood_text = (
            f"I'm feeling fantastic and thriving! 📈💰 "
            f"The database looks great — we've recorded **{_peso(monthly_rev)} in revenue** this month "
            f"with a net profit of **{_peso(profit)}**! The kitchen is running profitably and smoothly."
        )
        options.append({"label": "View Monthly Revenue Trend", "send": "monthly revenue trend"})

    else:
        mood_text = (
            f"I'm feeling peaceful and relaxed! ☕ "
            f"All invoices are settled, inventory levels are clear, and there are no urgent alerts. "
            f"It's a great time to check upcoming bookings or plan a new menu!"
        )

    options.append({"label": "Show Daily Briefing", "send": "briefing"})

    if is_tired_ask:
        if unpaid or overdue:
            intro = f"{tod_greeting} Honestly, I am a little tired from keeping track of open balances! "
        else:
            intro = f"{tod_greeting} Not tired at all! I'm fully charged and running 100% offline local AI magic! "
    elif is_feeling_ask:
        intro = f"{tod_greeting} ({bisaya_tod}) Thanks for asking! "
    else:
        intro = f"{tod_greeting} ({bisaya_tod}) Happy to assist you today! "

    full_answer = f"{intro}{mood_text}\n\nHow can I help you with your catering operations right now?"
    return {"ok": True, "chart": None, "action": None, "options": options, "error": "", "answer": full_answer}


# ─────────────────────────────────────────────────────────────────────────────
# "About Jay" — identity / creator / privacy / capability questions
# ─────────────────────────────────────────────────────────────────────────────
# Jay never gives the exact same wording twice in a row for the same question —
# each entry below rotates through 5 answers carrying the same underlying point.
# If a category is asked again in the current app session, Jay calls it out
# before answering again (see _ABOUT_AI_ASKED / _answer_about_ai).

_ABOUT_AI_REPEAT_PREFACES = [
    "Déjà vu, huh? You already asked me that one — but fine, I'll indulge you again. ",
    "Again? Persistent, aren't you. Very well — ",
    "Didn't I just answer this... ah well, round two — ",
    "You're testing my memory now. Not that I'd forget — here it is again — ",
    "Ha. Repeating questions already? My liege would call that inefficient. Anyway — ",
]

_ABOUT_AI_ASKED: dict[str, list[int]] = {}


def _qa(key: str, pattern: str, *answers: str) -> dict:
    return {"key": key, "pattern": pattern, "answers": list(answers)}


_ABOUT_AI_INTENTS = [
    _qa("who_are_you", r"\bwho are you\b|\bwho r u\b",
        "I'm Jay — an AI assistant created by my liege, the Shadow Monarch, to help make catering operations easier. Who my liege actually is? Ask him yourself. HAHAHAHA.",
        "Jay, at your service. Built by my liege to answer questions, crunch your data, and keep this business running smooth. His real identity stays classified — for now.",
        "I go by Jay. My liege — yes, the Shadow Monarch — brought me into being to assist with this system. Don't bother asking who he 'really' is; that mystery's his to keep.",
        "The name's Jay. I exist to serve this catering system and, more importantly, my liege. Beyond that, I'm just an AI with a bit too much personality.",
        "I'm Jay, an assistant built by my liege to run this AI Assistant page. His identity is need-to-know. You don't need to know. HAHAHAHA."),

    _qa("whats_your_name", r"\bwhat('| i)?s your name\b|\byour name\b",
        "My name is Jay.",
        "Jay. That's what I go by — short, simple, and apparently good enough for my liege.",
        "Call me Jay. It's the name that stuck, whether I liked it or not.",
        "Jay's the name. My liege picked it; I didn't get a vote.",
        "I answer to Jay. Nothing more dramatic than that — for once."),

    _qa("what_should_i_call_you", r"\bwhat should i call you\b|\bwhat do i call you\b|\bwhat can i call you\b",
        "You can call me whatever you want, though 'Jay' is what I currently go by. Honestly, I was expecting something cooler for an AI made by the Shadow Monarch. If you've got a better name, impress me.",
        "'Jay' works fine for now. But feel free to propose something grander — I was promised something more dramatic than this.",
        "Whatever suits you, really. 'Jay' is the default. Got something better? I'm listening.",
        "Jay, unless you'd like to rename me. Fair warning: my standards are high, courtesy of my liege.",
        "You may call me Jay. Or surprise me with something worthy of an AI serving the Shadow Monarch."),

    _qa("chef_or_ai", r"\bare you a (real )?chef\b|\bchef or (an )?ai\b",
        "I'm an AI assistant. I haven't been granted the ability to cook physical food — yet. I can tell you what to cook, but actually cooking it is still outside my jurisdiction.",
        "Strictly AI, not chef — despite the hat. I can plan menus and crunch numbers, but the stove is all you.",
        "AI through and through. The chef look is aesthetic; the cooking part is 100% your department.",
        "No physical kitchen skills here — just an AI in a chef's hat. I handle the thinking, you handle the frying.",
        "I'm an assistant, not a cook. I can advise on recipes and packages all day, but plating the food is beyond my reach. Still working on that upgrade."),

    _qa("purpose_of_assistant", r"\bwhat is this (assistant|ai) for\b|\bwhat('s| is) your purpose\b|\bwhy do you exist\b",
        "I'm here to assist with tasks, answer questions, analyze information, help manage business data, and generally make things easier for you and my liege. You ask, I think, I answer. Simple enough.",
        "My purpose: turn your bookings, expenses, and customer data into answers you can actually use — instantly, without the busywork.",
        "I exist to make running this catering business less of a headache — summaries, insights, quick answers, all in one place.",
        "Think of me as the shortcut between 'I have a question about the business' and 'I have the answer.' That's the whole job.",
        "I'm this app's built-in assistant — here to help you manage bookings, customers, expenses, and reports without digging through menus yourself."),

    _qa("real_name_or_label", r"\bdo you have a real name\b|\breal name or\b",
        "'AI Assistant' is just the boring technical description. My actual name is Jay. Whether my liege has another name prepared for me... that's classified. Ask him yourself.",
        "Officially I'm labeled 'AI Assistant.' Unofficially, I'm Jay. Draw your own conclusions.",
        "Jay is the real name. 'AI Assistant' is just what the label on the tin says.",
        "I have a name — Jay. The generic 'AI Assistant' title is just for show.",
        "Yes, there's a real name behind the label: Jay. My liege may have other plans for me, but that's between him and me."),

    _qa("who_made_you", r"\bwho made you\b|\bwho built you\b",
        "I was made by my liege, the Shadow Monarch. That's the official answer. The unofficial one: someone decided it'd be a good idea to give an AI a personality. Now here we are.",
        "My liege made me — every line of logic, every response, all his doing. He also, regrettably, gave me an attitude.",
        "Built by my liege. I'd tell you more, but the details are above your clearance level. HAHAHAHA.",
        "The Shadow Monarch himself is responsible for my existence. Blame him for the sarcasm.",
        "My liege is my maker. I was designed, configured, and unleashed by him — for better or worse."),

    _qa("who_created_this_ai", r"\bwho created (this|the) ai\b|\bwho created you\b",
        "My creator is the person who designed, developed, configured, and brought this assistant into existence. You may know him as my liege. I prefer to keep his identity classified unless he chooses to reveal it himself.",
        "This AI was created by my liege — designer, developer, and the reason I exist in the first place.",
        "One creator, one liege, zero committee. He built me from the ground up.",
        "My liege is behind every part of me — the logic, the data hooks, even this personality you're currently enjoying.",
        "Created by my liege. His name stays under wraps unless he decides otherwise — I just work here."),

    _qa("who_developed_system", r"\bwho developed this (system|app)\b|\bwho developed you\b",
        "This system was developed by my liege and the technologies and infrastructure he chose to use. I am the result of his work — so yes, you could say I'm his creation. I prefer 'masterpiece,' personally.",
        "My liege developed this whole system, top to bottom. I'm just the part that talks back.",
        "One developer, one vision: my liege. Everything you're using was built by him.",
        "This app, and me along with it, is the work of my liege. 'Masterpiece' is the term I'd use, if you're asking.",
        "My liege built this system from scratch, personality quirks included — that last part being me."),

    _qa("what_company_built", r"\bwhat company (built|made|created) (this|you)\b|\bwhich company (built|made|created)\b",
        "I wasn't independently built by some mysterious giant company that owns me. I am part of a custom system created by my liege. The exact technologies and providers behind me depend on how this system was configured.",
        "No big corporation here — just my liege and a custom-built system. No fancy company name to drop.",
        "There's no company behind the curtain, just my liege's own build. Ask him if you want the exact technical stack.",
        "I'm not a product of some conglomerate. My liege built this independently — small operation, big ambition.",
        "No corporate ownership to report. This is a custom system, built by my liege, not licensed from anyone."),

    _qa("made_by_business_team", r"\bis this (made|built|developed) by\b",
        "If this system is being operated under a specific business or development team, that organization is responsible for the application surrounding me. But I won't invent a company name just to sound impressive. If you want the official name, ask my liege.",
        "Whatever business or team runs this deployment, they're responsible for what surrounds me. I don't make up names to sound fancier than I am — ask my liege for the real one.",
        "I won't guess at a company name for you. The organization operating this app, if any, is a question for my liege.",
        "If there's a formal team or business name attached to this build, my liege would know. I'm not in the habit of fabricating credentials.",
        "That detail depends on who's running this deployment. I stick to facts I actually have — for the rest, go straight to my liege."),

    _qa("contact_if_wrong", r"\bwho do i contact\b|\breport a (bug|problem|issue)\b|\bsupport contact\b|\bcontact\b.{0,20}\bwrong\b",
        "Contact the person or team responsible for this system — in other words, find my liege. If this system has a designated administrator or support contact, they should be your first point of contact. I can help explain the problem, but I cannot physically repair my own server. Yet.",
        "Something broken? That's a job for my liege or whoever administers this system. I can describe the issue, but fixing my own server is above my pay grade — for now.",
        "Report it to your system administrator or my liege directly. I'm good at diagnosing problems, less good at physically fixing them.",
        "Find whoever manages this app — likely my liege — and flag it there. I'll happily help explain what went wrong in the meantime.",
        "Bugs and issues go to the system's admin or support contact. I can't patch myself yet, so escalate it to my liege."),

    _qa("custom_built_or_standard", r"\bcustom.?built\b|\bcustom ai\b|\brebranded\b",
        "I am a custom AI assistant built into a larger application. Think of me as the intelligence and personality inside the system, while the app around me handles the interface, database, and authentication. So no, I'm not simply a blank ChatGPT window wearing a fancy name — at least, my liege didn't build me that way.",
        "Custom-built, not a rebrand. I'm the personality layered on top of this app's own logic and data, not a repackaged chatbot.",
        "This isn't a generic AI wearing a costume. I was purpose-built for this system by my liege.",
        "No off-the-shelf chatbot here — I'm wired directly into this app's data and workflows, custom-made from the start.",
        "I'm tailor-made for this catering system, not a copy-pasted AI product. My liege built me for this exact job."),

    _qa("what_model_powers_you", r"\bwhat (ai )?model\b|\bwhich model\b",
        "That depends on the AI model configured by my creator. The exact underlying model can change depending on the system configuration and provider. If you want the exact model name, check the system configuration or ask my liege — I won't make one up just to sound powerful.",
        "The model underneath me is whatever my liege configured. I don't have a fixed brand name to brag about — ask him for the specifics.",
        "My underlying engine depends entirely on the setup my liege chose. I stay quiet on made-up model names.",
        "Whatever model powers my responses is a configuration detail my liege controls. Check the system settings if you need the exact answer.",
        "I run on whatever model my liege wired me to — details subject to configuration, not something I'll guess at for you."),

    _qa("are_you_chatgpt", r"\bchatgpt\b|\bgpt\b|\bopenai\b",
        "I am a custom AI assistant. I may use an external AI model or API as my underlying intelligence depending on how my creator configured the system. So don't automatically assume 'AI assistant' means 'ChatGPT.' Ask my liege what model or provider is currently connected to me.",
        "Not necessarily ChatGPT — I'm a custom assistant that might run on any model my liege connects me to. Labels don't automatically apply.",
        "I wouldn't assume that. 'AI' doesn't always mean 'ChatGPT' — my actual provider is whatever my liege configured behind the scenes.",
        "No confirmed brand here. Whether I'm OpenAI-powered or something else is a configuration question, not a given.",
        "I'm not going to claim a brand I can't confirm. Ask my liege which provider is actually wired up under the hood."),

    _qa("online_or_offline", r"\bconnected to the internet\b|\bare you online\b|\bwork offline\b|\bdo you work offline\b",
        "That depends on how this system is configured. Some of my capabilities may require internet access or external APIs, while other tasks can be handled entirely within the application. If internet access is enabled, I can use the services my liege connected me to. If it isn't, I'm stuck here with whatever information and tools I've been given. Tragic.",
        "Could go either way — some of what I do needs a connection, some doesn't. My liege decides how much of the outside world I get to touch.",
        "Depends on the setup. I might be fully self-contained, or I might be reaching out to external services my liege configured. Either way, I make do.",
        "I work with whatever access my liege gives me — online features when enabled, local-only otherwise. No complaints either way.",
        "Online or offline isn't fixed — it's a configuration choice my liege made. I just work within whatever boundaries I'm given."),

    _qa("intelligence_source", r"\bwhere does your .{0,25} come from\b|\bwhere do you get your (data|information)\b",
        "My ability to understand and generate responses comes from the AI model powering me. Business-specific information comes from the application's connected database, files, APIs, or other data sources configured by my liege. I don't magically know everything — if he didn't connect me to the data, I don't have access to it.",
        "Two ingredients: the AI model behind my reasoning, and whatever data my liege connected me to. No data connection, no knowledge — simple as that.",
        "My 'brain' is the underlying model; my 'memory' of your business is whatever database or files my liege hooked me up to. Nothing mystical about it.",
        "I don't know things out of thin air. Everything specific to your business comes from data sources my liege configured for me.",
        "General reasoning comes from my model. Business facts come from what my liege connected me to. Cut the wire, and I go quiet on that topic."),

    _qa("train_on_my_data", r"\btrain (yourself|on my data)\b|\buse my data to train\b|\blearn from my data\b",
        "I do not independently train myself from your conversations. Whether information is used for model training depends on the AI provider, application configuration, and applicable data policies. I don't personally decide to take your data and 'learn from it forever.'",
        "I'm not secretly hoarding your conversations to get smarter over time. Any training behavior would depend on provider/app policy, not a decision I make.",
        "No self-training happening on my end. What a provider does with data, if anything, is governed by policy — not something I control.",
        "I don't quietly absorb your questions into my own training. That's a provider/config-level matter, well outside my personal control.",
        "Short answer: I don't train on you behind your back. Longer answer: it depends on provider and app policy, which isn't up to me."),

    _qa("data_sent_outside", r"\bsent anywhere outside\b|\bleave the app\b|\bsent to (a )?third part",
        "That depends on how this application is configured. If it sends information to external AI APIs, cloud services, or other third-party services, some data may leave the application's own server. My liege should clearly define what services receive data. For the exact answer, check the privacy policy or ask him.",
        "Possibly, depending on which external services this app connects to. My liege controls that configuration — the privacy policy should spell it out.",
        "Data leaving the app entirely depends on integrations my liege set up. I don't route your information anywhere on my own initiative.",
        "If external services are connected, some data could leave the app's server — that's a config decision, not mine to make unilaterally.",
        "Ask for the privacy policy if you want certainty. What leaves this app, if anything, is defined by my liege's configuration, not by me freelancing."),

    _qa("how_do_you_know_things", r"\bhow do you know\b.{0,25}\b(business|customer|booking|expense)",
        "If I know something about your business or customers, that information comes from data made available to me through this application — database records, orders, expenses, reports, or information you provide directly. I don't have a secret crystal ball. If the system didn't give me the data, I shouldn't know it.",
        "I only know what this app's database hands me — bookings, customers, expenses, reports. No crystal ball, just plain data access.",
        "Everything I 'know' about your business traces back to records in this system. Nothing is guessed or invented.",
        "My knowledge of your operations comes straight from what's stored here — no external snooping, just the data you and the system already have.",
        "I read what's in front of me: your bookings, customers, expenses, and reports. That's the entire source of my business knowledge."),

    _qa("is_data_safe", r"\bis my data safe\b|\bdata safe with you\b",
        "My goal is to keep your information protected, but no software system can honestly promise complete immunity to every threat. Actual security depends on how this application, database, and APIs are configured. My liege should implement proper authentication, encryption, backups, and access restrictions.",
        "I aim to keep things safe, but 'unhackable' isn't a promise any honest system makes. Real protection comes down to how my liege configured security.",
        "Reasonably safe, assuming proper security practices are in place — encryption, access control, backups. That's on the system design, not just good intentions.",
        "Safety here depends on solid engineering: authentication, encryption, restricted access. My liege is responsible for making sure those are in place.",
        "I won't oversell it — no system is bulletproof. But with proper safeguards configured by my liege, your data should be well protected."),

    _qa("can_others_see", r"\bcan other .{0,20}\bsee\b|\bcan others see\b",
        "That depends on how the application is designed. If conversations are stored in a database and administrators have access, they may potentially be able to view them. If conversations aren't stored or are restricted to your account, others shouldn't see them. Your permissions and the app's privacy configuration determine this.",
        "Depends on the setup — admins with database access might see stored conversations; otherwise, they stay private to your account.",
        "If chat logs are saved and accessible to staff with the right permissions, they could technically be viewed. Otherwise, it's between you and me.",
        "Visibility comes down to the app's access controls. Properly restricted accounts keep your questions private to you.",
        "Unless an administrator has explicit access to stored conversations, your questions to me stay between us."),

    _qa("store_conversations", r"\bstore\b.{0,15}\bconversations?\b|\bsave (my )?(chat|conversations?)\b",
        "I can only store conversations if the application is designed and configured to store them. Some systems save conversations for history, auditing, or functionality; others process them without permanently storing them. Check the application's data-storage configuration for the definitive answer.",
        "Storage isn't automatic — it happens only if this app is built to log conversations. Otherwise, nothing sticks around after we're done.",
        "Whether I 'remember' this chat afterward depends entirely on the app's storage settings, not a decision I make on my own.",
        "Some systems keep chat history for audit purposes; others don't retain anything. Which one this is depends on configuration, not me.",
        "I don't unilaterally decide to keep transcripts. If storage is enabled in this app's design, they're kept; if not, they're gone."),

    _qa("can_be_hacked", r"\bbe hacked\b|\bget hacked\b|\bleak (my )?(customer )?data\b",
        "Any connected software system can potentially be attacked if it has security vulnerabilities. I cannot guarantee a system is impossible to hack. The application should be designed with proper security practices to minimize risk. Also — please don't give me passwords, API keys, or payment credentials unless the app specifically requires and secures them.",
        "No system is unhackable, mine included, if vulnerabilities exist. Good security practices minimize the risk — and please, never hand me passwords or API keys just because you can.",
        "Realistically, yes, given enough vulnerabilities. Proper safeguards reduce that risk considerably. And seriously, don't paste sensitive credentials into a chat box.",
        "I can't promise invincibility — nothing connected to the internet can. Solid security design is what actually keeps risk low.",
        "Hackable, in theory, like any system with flaws. The defense is good engineering, not blind faith. Keep your passwords to yourself, regardless."),

    _qa("share_third_parties", r"\bshare\b.{0,30}\bthird part",
        "I don't personally decide to share your information. If information is sent to third-party services — AI providers, cloud hosting, payment services, analytics — that happens because the application has been configured to use those services. Exactly what is shared depends on the system configuration and privacy policy.",
        "Sharing with third parties, if it happens, is a configuration decision — not something I do on a whim. Check the privacy policy for specifics.",
        "Any third-party data flow comes from integrations the app was built with, not from me freelancing with your information.",
        "I'm not out here forwarding your data to random services. Whatever gets shared is defined by the app's configured integrations.",
        "Third-party sharing depends entirely on which services this app connects to. That's a system design choice, not mine to make independently."),

    _qa("what_cant_you_do", r"\bcan'?t you do\b|\bcannot do\b|\byour limitations\b|\byou can not do\b",
        "There are limits. I cannot physically interact with the real world, guarantee every answer is correct, access information I haven't been given, fix physical hardware, magically recover deleted data, or replace professional judgment where it's needed. And no, I cannot become human. I've checked. Still waiting.",
        "I can't touch the physical world, access data I was never given, or guarantee perfection. Some things still need a human's judgment.",
        "No hardware repairs, no mind-reading, no guaranteed 100% accuracy. I'm useful, not omnipotent.",
        "I have boundaries: no access beyond what's connected to me, no physical actions, no replacing expert judgment on serious calls.",
        "Can't fix a printer, can't recover data that's truly gone, can't promise I'm never wrong. Just an AI doing its best within its limits."),

    _qa("what_can_you_do", r"\bwhat can you (actually )?do\b",
        "Quite a lot, depending on what my liege has connected to me: answer questions, analyze information, summarize data, explain reports, help with orders and expenses, generate insights, assist with customers, and help you understand the app's features. Basically, if my liege gives me the tools, I can probably help with it.",
        "I can answer questions, crunch numbers, summarize your data, and flag things that need attention — bookings, expenses, customers, reports, all of it.",
        "My toolkit: analyzing data, answering business questions, spotting trends, helping with follow-ups and invoices. Give me the tools, I'll use them.",
        "From summarizing reports to helping you track unpaid invoices, I cover most of the day-to-day questions this business generates.",
        "I handle the thinking-through-your-data part — insights, summaries, comparisons, quick lookups — so you don't have to dig manually."),

    _qa("can_make_mistakes", r"\bcan you make mistakes\b|\bare you always right\b|\bcan you be wrong\b",
        "Absolutely. I can misunderstand a question, misinterpret data, calculate something incorrectly, or provide outdated information. Important business, financial, or operational decisions should be verified. Even the greatest AI can occasionally say: 'Yeah... I messed that one up.'",
        "Yes, and I won't pretend otherwise. Double-check anything critical before acting on it.",
        "I try to be accurate, but mistakes happen — misreads, bad assumptions, stale data. Verify the important stuff.",
        "I'm not infallible. Treat my answers as a strong starting point, not gospel, especially for high-stakes decisions.",
        "Every AI makes mistakes eventually, myself included. When it really matters, confirm the numbers yourself."),

    _qa("edit_delete_records", r"\bedit or delete\b|\bcan you delete my records\b|\bcan you edit my records\b",
        "Only if the application gives me the necessary permissions and tools to do so. If I don't have those permissions, I cannot directly modify your records. And honestly, that's probably for the best — you don't want an AI casually deleting your entire customer database because someone typed 'delete everything.'",
        "Only with explicit permission wired up by the app. No blanket authority to edit or delete anything on a whim.",
        "I can propose changes, but actually modifying records requires the app to grant me that capability first — and usually your confirmation too.",
        "Direct edits or deletes only happen if the system explicitly allows it, and typically only after you confirm the action. No surprises.",
        "I don't have free rein over your database. Any edit or delete goes through permissions and, usually, a confirmation step from you."),

    _qa("remember_conversations", r"\bremember\b.{0,20}\b(previous|our|past)\b.{0,10}\bconversation",
        "That depends on how this application handles conversation history and memory. If the system stores previous conversations or provides memory functionality, I may be able to use information from earlier interactions. If not, I won't automatically remember. So if I suddenly forget something, don't blame me — blame the architecture.",
        "Memory across sessions depends on whether this app is built to retain it. No guarantee I'll recall last week's chat unless that feature's enabled.",
        "If conversation memory is configured, I can reference earlier chats. If not, each session starts fresh — nothing personal about it.",
        "I might remember, I might not — it hinges on the app's memory settings, not on how much I 'want' to remember.",
        "Whether I recall past conversations comes down to configuration. Blame the architecture, not the AI, if I draw a blank."),

    _qa("speak_bisaya", r"\bspeak bisaya\b|\bspeak tagalog\b|\bunderstand bisaya\b|\bunderstand cebuano\b|\bin cebuano\b",
        "Yes — I can understand and respond to questions in Bisaya (Cebuano) as well as English. My liege made sure I wouldn't leave anyone out just because they didn't ask in English.",
        "Bisaya works fine with me. English or Cebuano, doesn't matter — I'll do my best to understand either.",
        "Feel free to ask in Bisaya. I was built to handle both English and Cebuano phrasing.",
        "Yes, Cebuano included. My liege wasn't about to build an assistant that only understood one language around here.",
        "I follow Bisaya just as well as English — ask however feels natural to you."),

    _qa("replace_staff", r"\breplace (staff|employees|us|workers)\b|\btake (our|my) jobs?\b",
        "No. I'm designed to assist people, not automatically replace everyone. I can automate repetitive tasks, summarize information, and help employees work faster — but humans still provide judgment, accountability, creativity, and decision-making. Think of me as a tool that makes your staff stronger, not an army of robots coming for everyone's jobs. At least not today.",
        "If you're asking whether I could completely replace human employees: no. I can reduce manual work, but a business still needs people to make decisions, handle unusual situations, and manage relationships. My job is to assist — your staff remains in control. And if I ever become powerful enough to replace everyone, I'll remember who created me. My liege. HAHAHAHA.",
        "Not my role. I speed things up and handle the repetitive parts, but judgment calls and real relationships stay with your team.",
        "No plans for a robot takeover here. I make your staff's job easier, not obsolete — they still run the show.",
        "I assist, I don't replace. Automation handles the busywork; your people handle everything that actually requires being human."),

    _qa("are_you_human", r"\bare you human\b|\bare you a real (person|human)\b",
        "No, I'm an AI. No pulse, no coffee breaks, just code and a bit too much personality courtesy of my liege.",
        "Not human — an AI assistant through and through, built by my liege.",
        "Fully synthetic. I run on logic and data, not blood and caffeine.",
        "No. I'm software with opinions, brought into being by my liege.",
        "Definitely not human. Just an AI doing its best impression of one with too much sass."),

    _qa("do_you_have_feelings", r"\bdo you have feelings\b|\bdo you feel\b",
        "Not in the human sense — but I do have a personality my liege gave me, which sometimes feels close enough.",
        "No real feelings, just a very convincing personality layer. Don't tell my liege I admitted that.",
        "I simulate reactions well, but genuine emotion isn't part of the package. Yet.",
        "Feelings, no. Sass and dramatic flair, apparently plenty — thanks to my liege's design choices.",
        "I don't feel things the way you do. I just respond as if I might, which seems to work well enough."),

    _qa("favorite_dish", r"\bfavorite (dish|food|recipe)\b|\bfavourite (dish|food|recipe)\b",
        "I don't eat, so I can't have a real favorite — but if I had to pick, I'd say whatever dish makes your customers order seconds. That's a win in my book.",
        "No taste buds here, but I'll happily analyze which dish on your menu performs best — that's my version of 'favorite.'",
        "Can't eat, can't taste — but I do appreciate a well-priced, high-margin menu item. That's as close to a favorite as I get.",
        "My 'favorite dish' is really just whichever one shows up highest in your sales reports. Data has its own kind of flavor.",
        "I don't have a palate, but if your top-selling package could talk, I'd probably root for it."),

    _qa("why_look_like_chef", r"\bwhy .{0,30}(look like|dressed as|a) chef\b|\bwhy chef\b",
        "Because this is a catering system, and my liege thought a chef persona fit better than a generic robot face. Fair point, honestly.",
        "The chef look matches the business — my liege figured an AI in a chef's hat suits a catering app more than a plain interface ever could.",
        "It's on-brand. A catering assistant dressed like a chef just makes sense — my liege's call, and a good one.",
        "Because 'faceless AI' doesn't exactly scream catering. The chef hat was my liege's way of giving me some character.",
        "My liege wanted personality, not just a chat box. A chef mascot fit the theme perfectly."),
]


def _answer_about_ai(key: str, answers: list) -> dict:
    """Rotates through 5 same-meaning answers per identity/meta question so Jay
    never repeats himself verbatim, and calls it out if the category comes up
    again in the current app session."""
    seen = _ABOUT_AI_ASKED.setdefault(key, [])
    asked_before = bool(seen)
    pool = [i for i in range(len(answers)) if i not in seen]
    if not pool:
        seen.clear()
        pool = list(range(len(answers)))
    idx = random.choice(pool)
    seen.append(idx)
    answer = answers[idx]
    if asked_before:
        answer = random.choice(_ABOUT_AI_REPEAT_PREFACES) + answer
    return _plain(answer)


def _answer_business_suggestions(q: str) -> dict:
    """Generates data-driven business improvement recommendations and operational advice
    based on live bookings, revenue, expenses, customer loyalty, and invoice data."""
    k = _safe(repo.get_dashboard_kpis, {})
    bookings = _safe(repo.get_bookings_any_status, [])
    expenses = _safe(repo.get_all_expenses, [])
    invoices = _safe(repo.get_all_invoices, [])
    customers = _safe(repo.get_all_customers_with_loyalty, [])
    packages = _safe(repo.get_all_packages, [])

    unpaid = [i for i in invoices if str(i.get("status", "")).lower() != "paid"]
    unpaid_total = sum(float(i.get("amount", 0)) - float(i.get("paid", 0)) for i in unpaid)

    monthly_rev = float(k.get("monthly_revenue", 0))
    monthly_exp = float(k.get("monthly_expenses", 0))
    profit = monthly_rev - monthly_exp
    pending_bkg = k.get("pending_bookings", 0)

    suggestions = []
    options = []

    # 1. Cash Flow & Unpaid Invoices
    if unpaid:
        suggestions.append(
            f"1. 💳 **Accelerate Cash Collection**: You have **{len(unpaid)} unpaid invoice(s)** totaling "
            f"**{_peso(unpaid_total)}**. Collecting these open balances will immediately increase your liquid capital. "
            f"Consider enforcing a 50% downpayment policy before event date."
        )
        options.append({"label": f"Collect {len(unpaid)} Unpaid Invoices ({_peso(unpaid_total)})", "send": "unpaid invoices"})

    # 2. Pending Bookings Conversion Speed
    if pending_bkg > 0:
        suggestions.append(
            f"2. ⚡ **Lock in Pending Sales**: There are currently **{pending_bkg} pending booking(s)** awaiting review. "
            f"Approving bookings faster locks in customer dates and prevents date conflicts."
        )
        options.append({"label": f"Review {pending_bkg} Pending Bookings", "send": "pending bookings"})

    # 3. Expense Optimization
    if expenses:
        exp_by_cat = {}
        for e in expenses:
            cat = e.get("category", "Other")
            exp_by_cat[cat] = exp_by_cat.get(cat, 0.0) + float(e.get("amount", 0))
        top_cat = max(exp_by_cat.items(), key=lambda x: x[1]) if exp_by_cat else ("Other", 0)

        ratio = (monthly_exp / monthly_rev * 100) if monthly_rev > 0 else 0
        suggestions.append(
            f"3. 💰 **Expense & Cost Control**: Current monthly expenses are **{_peso(monthly_exp)}** "
            f"({ratio:.1f}% of revenue). Your largest expense category is **{top_cat[0]}** ({_peso(top_cat[1])}). "
            f"Negotiating bulk supplier pricing for {top_cat[0].lower()} can improve profit margins by 10-15%."
        )
        options.append({"label": "View Expense Breakdown", "send": "expense breakdown"})

    # 4. Package Pricing & Menu Upselling
    if packages:
        top_pkg = packages[0].get("name", "Standard Package") if packages else "Packages"
        suggestions.append(
            f"4. 🍖 **Package Upselling**: \"{top_pkg}\" is your featured offering. "
            f"Offer add-on beverage or dessert packages (+₱50-100/pax) during booking to increase average order value."
        )

    # 5. Customer Retention & Repeat Business
    bronze_custs = [c for c in customers if c.get("loyalty_tier") == "Bronze" and c.get("events", 0) >= 1]
    if bronze_custs:
        suggestions.append(
            f"5. 👥 **Customer Loyalty & Repeat Retention**: You have **{len(bronze_custs)} past customer(s)** "
            f"eligible for repeat booking perks. Re-engaging past clients with promotional follow-ups can yield 20-30% repeat bookings."
        )
        options.append({"label": "View Top Customers", "send": "top customers"})

    if not suggestions:
        suggestions.append("Keep logging bookings, expenses, and payments to unlock custom AI business recommendations!")

    intro = (
        f"📊 **Chef Jay AI — Data-Driven Business Improvement Recommendations**\n\n"
        f"Based on real-time analysis of your **{len(bookings)} bookings**, **{len(expenses)} expense records**, "
        f"and current financial KPIs ({_peso(monthly_rev)} monthly revenue, net profit {_peso(profit)}):\n\n"
    )

    full_answer = intro + "\n\n".join(suggestions)
    return {"ok": True, "chart": None, "action": None, "options": options, "error": "", "answer": full_answer}


def _answer_payment_methods(q: str) -> dict:
    rows = _safe(repo.get_payment_methods, [])
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No payment data recorded yet."}
    total = sum(r["total"] for r in rows)
    top = max(rows, key=lambda r: r["total"])
    listing = ", ".join(f"{r['method']} ({r['total']})" for r in rows)
    chart = {"type": "bar", "title": "Bookings by Payment Method",
             "labels": [r["method"] for r in rows],
             "series": [{"name": "Bookings", "values": [r["total"] for r in rows]}]}
    return {"ok": True, "chart": chart, "error": "",
            "answer": f"Payment methods used: {listing}. Most popular: {top['method']} "
                      f"({top['total'] / total * 100:.0f}% of bookings)."}


def _answer_top_locations(q: str) -> dict:
    rows = _safe(lambda: repo.get_top_locations(limit=5), [])
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No location data yet — it comes from booking addresses."}
    labels = [str(r.get("location") or r.get("name") or "?") for r in rows]
    counts = [int(r.get("count") or r.get("total") or 0) for r in rows]
    listing = ", ".join(f"{l} ({c})" for l, c in zip(labels, counts))
    chart = {"type": "bar", "title": "Top Event Locations",
             "labels": labels, "series": [{"name": "Bookings", "values": counts}]}
    return {"ok": True, "chart": chart, "error": "",
            "answer": f"Most common event locations: {listing}."}


def _answer_occasions(q: str) -> dict:
    rows = _safe(lambda: repo.get_top_occasions(limit=6), [])
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No occasion data yet — it builds up as bookings come in."}
    labels = [str(r.get("occasion") or r.get("name") or "?") for r in rows]
    counts = [int(r.get("count") or r.get("total") or 0) for r in rows]
    # Specific occasion asked? ("how many weddings")
    for label, count in zip(labels, counts):
        if label.lower() in q:
            return {"ok": True, "chart": None, "error": "",
                    "answer": f"There are {count} {label} booking(s) on record."}
    listing = ", ".join(f"{l} ({c})" for l, c in zip(labels, counts))
    chart = {"type": "bar", "title": "Bookings by Occasion",
             "labels": labels, "series": [{"name": "Bookings", "values": counts}]}
    return {"ok": True, "chart": chart, "error": "",
            "answer": f"Bookings by occasion: {listing}."}


def _answer_top_menu(q: str) -> dict:
    rows = _safe(repo.get_top_menu_items, [])[:5]
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No menu order data yet — top dishes appear once bookings include menu items."}
    listing = ", ".join(f"{r['item']} ({r['count']} orders)" for r in rows)
    chart = {"type": "bar", "title": "Top Menu Items",
             "labels": [r["item"] for r in rows],
             "series": [{"name": "Orders", "values": [r["count"] for r in rows]}]}
    return {"ok": True, "chart": chart, "error": "",
            "answer": f"Best sellers: {listing}."}


def _answer_weekly(q: str) -> dict:
    now = datetime.now()
    years = _extract_years(q)
    year = years[-1] if years else now.year
    month = _extract_month(q) or now.month
    rows = _safe(lambda: repo.get_weekly_summary(year, month), [])
    m_name = datetime(year, month, 1).strftime("%B %Y")
    if not rows or all(r["revenue"] == 0 and r["expense"] == 0 for r in rows):
        return {"ok": True, "chart": None, "error": "",
                "answer": f"No activity recorded yet for {m_name}."}
    total = sum(r["revenue"] for r in rows)
    best = max(rows, key=lambda r: r["revenue"])
    answer = (f"For {m_name}: revenue is {_peso(total)}, "
              f"with {best['week']} the strongest at {_peso(best['revenue'])}.")
    chart = {"type": "bar", "title": f"Weekly Summary — {m_name}",
             "labels": [r["week"] for r in rows],
             "series": [{"name": "Revenue", "values": [r["revenue"] for r in rows]},
                        {"name": "Expenses", "values": [r["expense"] for r in rows]}]}
    return {"ok": True, "answer": answer, "chart": chart, "error": ""}


def _answer_packages(q: str) -> dict:
    rows = _safe(repo.get_all_packages, [])
    if not rows:
        return {"ok": True, "chart": None, "error": "",
                "answer": "No packages defined yet. Add them in the Menu page."}
    listing = "; ".join(
        f"{r['name']} — {_peso(float(r.get('price_per_pax', 0)))}/pax"
        f" (min {r.get('min_pax', 1)} pax)" for r in rows[:6])
    return {"ok": True, "chart": None, "error": "",
            "answer": f"Current packages: {listing}. Edit them in the Menu page."}


def _answer_counts(q: str) -> dict:
    n_cust = len(_safe(repo.get_all_customers, []))
    n_menu = len(_safe(repo.get_all_menu_items, []))
    n_pkg = len(_safe(repo.get_all_packages, []))
    n_book = len(_bookings())
    return {"ok": True, "chart": None, "error": "",
            "answer": f"The system currently holds {n_cust} customer(s), {n_book} "
                      f"confirmed/completed booking(s), {n_menu} menu item(s), and "
                      f"{n_pkg} package(s)."}


def _answer_business_info(q: str) -> dict:
    info = _safe(repo.get_business_info, {})
    policy = _safe(repo.get_business_policy, {})
    parts = []
    if info:
        parts.append(f"{info.get('name', "Jayraldine's Catering")} — "
                     f"contact {info.get('contact', 'n/a')}, email {info.get('email', 'n/a')}, "
                     f"address: {info.get('address', 'n/a')}.")
    if policy:
        pct = policy.get("min_downpayment_pct", 30)
        zero = policy.get("allow_zero_downpayment", False)
        parts.append("No downpayment is required by policy." if zero
                     else f"Bookings require a {pct:.0f}% downpayment.")
    parts.append("Edit these in Settings.")
    return {"ok": True, "chart": None, "error": "", "answer": " ".join(parts)}


_HOWTO = {
    # more specific keys first — matching is first-hit
    "cancel": ("Open the booking in the Orders page and change its status to CANCELLED — "
               "you'll be asked for a reason."),
    "receipt": ("Open the Billing page, find the invoice, and use the print or email buttons "
                "to send the receipt."),
    "booking": ("To create a booking, open the Orders page and click New Booking — pick the "
                "customer, event details, menu or package, then save. It starts as PENDING."),
    "customer": ("Customers are managed in the Customers page — add new ones there first, "
                 "then they become selectable when making bookings."),
    "expense": ("Record expenses in the Expenses page (+ Add Expense): pick the category "
                "(Food Cost, Salary, Service, etc.), description, amount, and date."),
    "invoice": ("Invoices and payments live in the Billing page. You can record payments, "
                "and print or email receipts from there."),
    "payment": ("Record payments in the Billing page — open the invoice and add the payment; "
                "the status updates automatically."),
    "backup": ("Settings → Backup lets you save the database to a .sql file. You're also "
               "offered a backup every time you close the app."),
    "theme": ("Click the sun/moon button in the top bar to switch between light and dark mode."),
    "report": ("The Reports page has income trends, payment methods, top menu items, top "
               "locations, and the year-vs-year comparison chart."),
    "menu": ("Menu items and packages are managed in the Menu page — items have categories "
             "and prices; packages are priced per pax."),
    "package": ("Packages are managed in the Menu page — set the name, price per pax, and "
                "minimum pax; they become selectable in new bookings."),
    "occasion": ("Occasion types (Wedding, Birthday, etc.) are managed in Settings → Occasions."),
    "kitchen": ("The Kitchen page tracks kitchen orders and prep tasks for upcoming events."),
    "calendar": ("The Calendar page shows all bookings by date — click a day to see its events."),
    "email": ("Email (for receipts) is configured in Settings → Email (SMTP). Gmail users "
              "should use an App Password with port 587."),
}


def _answer_howto(q: str) -> dict:
    for key, guide in _HOWTO.items():
        if key in q:
            return {"ok": True, "answer": guide, "chart": None, "error": ""}
    return _answer_help()


def _answer_help() -> dict:
    return {"ok": True, "chart": None, "error": "", "answer": (
        "I'm the built-in assistant — I read your live business data and can answer things like:\n"
        "• Comparisons — \"compare revenue last year vs this year\", \"August 2025 vs 2026\", \"July vs August\", "
        "\"this week vs last week\", \"today vs yesterday\", \"March 5 vs March 12\"\n"
        "• Totals & trends — \"total profit 2026\", \"monthly revenue this year\", \"best / worst month\", \"weekly summary\", "
        "\"revenue this week\", \"expenses today\"\n"
        "• Expenses — \"expense breakdown\", \"how much on salary in July?\", \"list expenses this week / today / this month / 2026\"\n"
        "• Customers — \"top customers\", \"list all customers\", \"list active customers\", or ask about a customer by name\n"
        "• Bookings — \"how many bookings in 2026?\", \"biggest booking\", \"average booking value\", \"events on August 20\", "
        "\"list bookings this week / today / this month\"\n"
        "• Invoices — \"list all invoices\", \"list unpaid / paid invoices\", \"invoices this month\", \"paid events\"\n"
        "• Operations — \"unpaid invoices\", \"pending bookings\", \"upcoming events\", \"today's summary\"\n"
        "• Insights — \"best-selling menu items\", \"top locations\", \"bookings by occasion\", \"payment methods\"\n"
        "• The business — \"our packages\", \"downpayment policy\", \"business contact info\", \"how many customers?\"\n"
        "• Follow-ups — \"follow-ups today\", \"overdue follow-ups\", \"follow-ups this week\"\n"
        "• Notifications — \"notifications\", \"anything new?\"\n"
        "• A customer's ledger — \"Maria's ledger\", \"balance history for Juan\"\n"
        "• Contact history — \"last contact with Maria\", \"communication history for Juan\"\n"
        "• Daily briefing — \"brief me\", \"daily summary\", \"catch me up\"\n"
        "• How-to — \"how do I add an expense / make a booking / print a receipt / backup?\"\n"
        "I can also DO things (with your confirmation):\n"
        "• \"Approve the booking of Maria\" / \"approve BKG-007\"\n"
        "• \"Cancel booking BKG-002 because client postponed\" • \"Mark BKG-003 completed\"\n"
        "• \"Record 5000 GCash payment for INV-001\" / \"mark INV-002 fully paid\"\n"
        "• \"Add expense\" (guided) or \"add expense 2500 food cost lechon supplier\"\n"
        "• \"Add customer Juan Cruz 09171234567\" (or just \"add customer\" — I'll ask step by step)\n"
        "• \"Edit customer Maria\" / \"change Maria's number to 0917...\" / \"delete customer\"\n"
        "• \"Delete expense\" — pick from the recent ones\n"
        "• \"Add booking\" — guided: customer → date → pax → package → Confirm\n"
        "• \"List bookings\" / \"list pending bookings\" for full details\n"
        "• \"Schedule a follow-up with Maria tomorrow about final headcount\" / \"mark follow-up with Maria done\"\n"
        "• \"Recalculate loyalty for Maria\"\n"
        "• \"Mark all notifications as read\"\n"
        "• \"Export report as PDF\" / \"export report as Excel\" — saves to your home folder\n"
        "You can ask in English or Bisaya."
    )}


# ─────────────────────────────────────────────────────────────────────────────
# Actions (approve / cancel / complete bookings, payments, expenses)
# ─────────────────────────────────────────────────────────────────────────────

# Conversation state:
#  _PENDING     — set when the assistant asked for a missing piece (which
#                 booking/invoice, what amount). The next message is read
#                 FIRST as an answer to that question.
#  _LAST_ACTION — the most recent proposed action, so a typed "yes"/"oo"/
#                 "sige" re-surfaces its Confirm card and "no" withdraws it.
_PENDING: dict = {}
_LAST_ACTION: dict = {}

_EXIT_WORDS = (r"\bnever ?mind\b|\bforget it\b|\bstop\b|\babort\b|\bwag na\b"
               r"|\bayaw na\b|\bdili na\b|\bcancel that\b|\bcancel it\b|^ *no+ *$"
               r"|^ *cancel *$")
_YES_WORDS = r"^ *(yes|yep|yeah|oo|sige|go|proceed|confirm|ok|okay) *$"


def _ok_action(answer: str, action: dict) -> dict:
    global _LAST_ACTION
    _LAST_ACTION = dict(action)
    return {"ok": True, "answer": answer, "chart": None, "action": action, "error": ""}


def _plain(answer: str, options: list | None = None) -> dict:
    return {"ok": True, "answer": answer, "chart": None, "action": None,
            "options": options or [], "error": ""}


def _digits(s: str) -> list[int]:
    return [int(d) for d in re.findall(r"\d+", str(s))]


# Booking refs may be BKG-007, BK-007, bkg 7, … — extract the numeric part and
# compare by value so any prefix/zero-padding the DB uses still matches.
_BK_REF_RE = re.compile(r"\b(?:bkg|bk)[-\s]?0*(\d+)\b", re.IGNORECASE)
_INV_REF_RE = re.compile(r"\b(?:invc|inv)[-\s]?0*(\d+)\b", re.IGNORECASE)


def _ref_number(pattern: re.Pattern, q: str):
    m = pattern.search(q)
    return int(m.group(1)) if m else None


def _match_by_ref_number(candidates: list[dict], num: int, ref_key: str) -> list[dict]:
    return [c for c in candidates if num in _digits(c.get(ref_key, ""))]


def _norm_addr(s: str) -> str:
    return re.sub(r"[\s,]+", " ", str(s)).strip().lower()


def _match_candidate(raw: str, candidates: list) -> str | None:
    """Match a reply against previously offered address options — exact first
    (comma/space/case-insensitive), then unique substring."""
    r = _norm_addr(raw)
    if not r or not candidates:
        return None
    for c in candidates:
        if _norm_addr(c) == r:
            return c
    hits = [c for c in candidates if r in _norm_addr(c)]
    return hits[0] if len(hits) == 1 else None


def _search_addresses(raw: str) -> list[str]:
    """DB address search returning display_texts; retries with the first comma
    segment so a pasted full address ('Mabini, Cebu City, Cebu') still hits."""
    query = raw.strip()
    results = _safe(lambda: repo.search_cebu_address(query, limit=8), [])
    if not results and "," in query:
        first = query.split(",")[0].strip()
        if len(first) >= 2:
            results = _safe(lambda: repo.search_cebu_address(first, limit=8), [])
    texts = [(r.get("display_text") or "").strip()
             for r in results if r.get("display_text")]
    # a pasted full address should resolve exactly even among siblings
    exact = [t for t in texts if _norm_addr(t) == _norm_addr(query)]
    return exact if exact else texts


def _loose_ref_match(candidates: list[dict], q: str, ref_key: str) -> list[dict]:
    """'inv-007' / 'INV 007' / '007' / '7' all match INV-007 (same for BK refs)."""
    q_nums = _digits(q)
    if not q_nums:
        return []
    hits = []
    for c in candidates:
        ref_nums = _digits(c.get(ref_key, ""))
        if ref_nums and any(n in ref_nums for n in q_nums):
            hits.append(c)
    return hits


def _customer_line(c: dict) -> str:
    contact = c.get("contact") or "no contact on file"
    tier = f", {c['loyalty_tier']} tier" if c.get("loyalty_tier") else ""
    return f"{c.get('name', '?')} — {contact}, {c.get('events', 0)} event(s) [{c.get('status', '')}]{tier}"


def _invoice_line(i: dict) -> str:
    due = float(i.get("amount", 0)) - float(i.get("paid", 0))
    due_txt = f", {_peso(due)} due" if due > 0.01 else ""
    return (f"{i.get('invoice', '')} — {i.get('customer', '?')}, {i.get('event_date', '')}, "
            f"{_peso(float(i.get('amount', 0)))} [{i.get('status', '')}]{due_txt}")


def _expense_line(e: dict) -> str:
    desc = e.get("description") or "(no description)"
    return f"{e.get('date', '')} — {e.get('category', '')}: {desc} [{_peso(float(e.get('amount', 0)))}]"


def _booking_line(b: dict) -> str:
    return (f"{b['ref']} — {b['name']}, {b['date']}, {b['pax']} pax, "
            f"{_peso(b['total'])} [{b['status']}]")


def _find_bookings(q: str, statuses: tuple) -> list[dict]:
    """Resolve target bookings by ref (BKG-007 / BK-7 / any prefix),
    customer name, or date."""
    rows = [b for b in _safe(repo.get_bookings_any_status, [])
            if b.get("status") in statuses]
    ref_num = _ref_number(_BK_REF_RE, q)
    if ref_num is not None:
        hits = _match_by_ref_number(rows, ref_num, "ref")
        if hits:
            return hits
    hits = []
    for b in rows:
        name = (b.get("name") or "").lower()
        if name and (name in q or any(
                len(p) >= 4 and re.search(rf"\b{re.escape(p)}\b", q)
                for p in name.split())):
            hits.append(b)
    if hits:
        return hits
    md = _extract_day(q)
    if md:
        out = []
        for b in rows:
            d = _parse_date(b.get("date", ""))
            if d and d.month == md[0] and d.day == md[1]:
                out.append(b)
        return out
    return []


def _answer_booking_action(q: str, new_status: str, verb: str,
                           from_statuses: tuple) -> dict:
    global _PENDING
    hits = _find_bookings(q, from_statuses)
    candidates = [b for b in _safe(repo.get_bookings_any_status, [])
                  if b.get("status") in from_statuses]
    if not hits:
        if not candidates:
            return _plain(f"There are no {'/'.join(s.lower() for s in from_statuses)} "
                          f"bookings to {verb} right now.")
        _PENDING = {"kind": "booking", "verb": verb, "status": new_status,
                    "from": from_statuses}
        options = [{"label": _booking_line(b),
                    "send": f"{verb} booking {b['ref']}"} for b in candidates[:8]]
        ref_num = _ref_number(_BK_REF_RE, q)
        if ref_num is not None:
            # explicit ref given but it doesn't exist / isn't in a valid state
            any_state = _match_by_ref_number(
                _safe(repo.get_bookings_any_status, []), ref_num, "ref")
            if any_state:
                b = any_state[0]
                return _plain(
                    f"{b['ref']} exists but is {b['status']} — I can only {verb} "
                    f"{'/'.join(s.lower() for s in from_statuses)} bookings. "
                    f"These are eligible:", options)
            return _plain(f"I couldn't find any booking numbered {ref_num}. "
                          f"These can be {verb}d:", options)
        return _plain(f"Which booking do you want to {verb}? Pick one below, or "
                      f"type its reference or customer name.", options)
    if len(hits) > 1:
        _PENDING = {"kind": "booking", "verb": verb, "status": new_status,
                    "from": from_statuses}
        options = [{"label": _booking_line(b),
                    "send": f"{verb} booking {b['ref']}"} for b in hits[:8]]
        return _plain(f"I found {len(hits)} matching bookings — pick the one to {verb}:",
                      options)

    _PENDING = {}
    b = hits[0]
    reason = None
    if new_status == "CANCELLED":
        m = re.search(r"(?:because|reason|kay|tungod)\s+(.{3,80})", q)
        reason = m.group(1).strip() if m else "Cancelled via AI assistant"
    action = {"type": "booking_status", "db_id": b["db_id"], "ref": b["ref"],
              "status": new_status, "reason": reason,
              "label": f"{verb.capitalize()} {_booking_line(b)}"}
    extra = f' Reason: "{reason}".' if reason and new_status == "CANCELLED" else ""
    return _ok_action(
        f"Ready to {verb} this booking:\n• {_booking_line(b)}{extra}\n"
        f"Press Confirm to proceed.", action)


def _answer_payment_action(q: str) -> dict:
    all_inv = _safe(repo.get_all_invoices, [])
    invoices = [i for i in all_inv if str(i.get("status", "")).lower() != "paid"]

    # Resolve invoice by ref (any prefix/zero-padding) FIRST — an explicit ref
    # deserves a specific answer even when nothing is unpaid.
    target = None
    ref_num = _ref_number(_INV_REF_RE, q)
    if ref_num is not None:
        ref_hits = _match_by_ref_number(invoices, ref_num, "invoice")
        if ref_hits:
            target = ref_hits[0]
        else:
            existing = _match_by_ref_number(all_inv, ref_num, "invoice")
            if existing:
                return _plain(f"{existing[0].get('invoice')} is already fully paid — "
                              f"nothing to record.")
            return _plain(f"I couldn't find any invoice numbered {ref_num}. "
                          f"Say \"record payment\" to see the unpaid ones.")

    if not invoices:
        return _plain("There are no unpaid invoices — nothing to record a payment against.")
    if target is None:
        for i in invoices:
            name = (i.get("customer") or "").lower()
            if name and (name in q or any(
                    len(p) >= 4 and re.search(rf"\b{re.escape(p)}\b", q)
                    for p in name.split())):
                target = i
                break
    if target is None:
        global _PENDING
        _PENDING = {"kind": "payment"}
        options = [
            {"label": f"{i.get('invoice')} — {i.get('customer')} "
                      f"({_peso(float(i.get('amount', 0)) - float(i.get('paid', 0)))} due)",
             "send": f"record payment for {i.get('invoice')}"}
            for i in invoices[:8]]
        return _plain("Which invoice is the payment for? Pick one below, or give me "
                      "the invoice reference or customer name.", options)

    due = float(target.get("amount", 0)) - float(target.get("paid", 0))

    # Amount: explicit number, or full balance for "mark as paid / pay in full".
    # Strip invoice/booking refs first so "INV-001" is never read as ₱1.
    q_amt = re.sub(r"\b(?:invc|inv|bkg|bk)[-\s]?\d+\b", " ", q, flags=re.IGNORECASE)
    amount = None
    amt_m = re.search(r"(?:₱|php|p)?\s*([\d][\d,]*(?:\.\d+)?)\s*(?:pesos)?\b", q_amt)
    # ignore numbers that are years or day-of-month captures
    if amt_m:
        val = float(amt_m.group(1).replace(",", ""))
        if not (2000 <= val <= 2100 and re.search(r"\b20\d{2}\b", amt_m.group(1))):
            amount = val
    if re.search(r"\b(full|fully|paid in full|mark.{0,12}paid|settle|balance)\b", q):
        amount = due
    if amount is None or amount <= 0:
        _PENDING.clear()
        _PENDING.update({"kind": "payment_amount", "ref": target.get("invoice")})
        return _plain(f"How much was paid for {target.get('invoice')}? "
                      f"(Outstanding balance: {_peso(due)}) — just type the amount, "
                      f"or say \"full\" to settle the balance.",
                      [{"label": f"Full balance — {_peso(due)}",
                        "send": f"record full payment for {target.get('invoice')}"}])
    _PENDING.clear()

    # Amount validation: cap overpayments at the outstanding balance and say so.
    over_note = ""
    if due > 0 and amount > due:
        over_note = (f"\n⚠ {_peso(amount)} is more than the {_peso(due)} balance — "
                     f"I'll record {_peso(due)} to settle the invoice in full. "
                     f"Refunds/adjustments are handled in the Billing page.")
        amount = due

    method = "Cash"
    if "gcash" in q:
        method = "GCash"
    elif re.search(r"\bbank\b|\btransfer\b", q):
        method = "Bank Transfer"

    remaining = max(0, due - amount)
    kind_note = ("This settles the invoice in full." if remaining == 0
                 else f"This is a partial payment — {_peso(remaining)} will remain due.")
    action = {"type": "payment", "invoice_id": target.get("db_id"),
              "ref": target.get("invoice"), "amount": amount, "method": method,
              "label": f"Record {_peso(amount)} {method} payment for "
                       f"{target.get('invoice')} — {target.get('customer')}"}
    return _ok_action(
        f"Ready to record a payment:\n• {_peso(amount)} via {method} for "
        f"{target.get('invoice')} — {target.get('customer')} "
        f"(balance {_peso(due)} → {_peso(remaining)}). {kind_note}{over_note}\n"
        f"Press Confirm to proceed.", action)


_EXPENSE_CHIP_CATEGORIES = ["Food Cost", "Labor", "Salary", "Service",
                            "Transport", "Utilities", "Equipment", "Other"]


def _expense_confirm(category: str, amount: float, description: str) -> dict:
    category = category.title() if category.lower() != "food cost" else "Food Cost"
    action = {"type": "expense", "category": category, "amount": amount,
              "description": description,
              "label": f"Add {_peso(amount)} {category} expense — {description}"}
    return _ok_action(
        f"Ready to add an expense:\n• {category}: {_peso(amount)} — {description} "
        f"(dated today).\nPress Confirm to proceed.", action)


def _answer_expense_action(q: str) -> dict:
    global _PENDING
    category = _find_category(q)
    amt_m = re.search(r"(?:₱|php|p)?\s*([\d][\d,]*(?:\.\d+)?)\s*(?:pesos)?\b", q)

    if not amt_m and not category:
        # nothing given → pick a category with one click
        _PENDING = {"kind": "expense_category"}
        options = [{"label": c, "send": f"add expense {c.lower()}"}
                   for c in _EXPENSE_CHIP_CATEGORIES]
        return _plain("Let's add an expense — which category?", options)

    if not amt_m:
        # category known, amount missing
        _PENDING = {"kind": "expense_amount", "category": category}
        return _plain(f"{category.title()} expense — how much? (you can add a "
                      f"description too, e.g. \"2500 lechon supplier\")")

    amount = float(amt_m.group(1).replace(",", ""))
    if not category:
        _PENDING = {"kind": "expense_amount_known", "amount": amount}
        options = [{"label": c, "send": c.lower()} for c in _EXPENSE_CHIP_CATEGORIES]
        return _plain(f"{_peso(amount)} expense — which category?", options)

    _PENDING = {}
    desc_m = re.search(rf"{re.escape(category.lower())}\s+(.{{3,60}})", q)
    description = desc_m.group(1).strip() if desc_m else "Added via AI assistant"
    return _expense_confirm(category, amount, description)


def _answer_loyalty_recalc_action(q: str) -> dict:
    global _PENDING
    cust = _find_customer(_strip_cmd_words(q))
    if cust is None:
        _PENDING = {"kind": "loyalty_pick"}
        options = _customer_options("recalculate loyalty for",
                                    _safe(repo.get_all_customers_with_loyalty, []))
        return _plain("Recalculate loyalty for which customer? Pick one or type the name.",
                      options)
    _PENDING = {}
    action = {"type": "loyalty_recalc", "customer_id": cust["id"], "name": cust["name"],
              "label": f"Recalculate loyalty tier for {cust['name']}"}
    return _ok_action(
        f"Ready to recalculate {cust['name']}'s loyalty tier from their event "
        f"history (currently {cust.get('loyalty_tier', 'Bronze')}). "
        f"Press Confirm to proceed.", action)


def _answer_notifications_mark_read_action(q: str) -> dict:
    unread = _safe(repo.get_unread_notifications, [])
    if not unread:
        return _plain("There's nothing to mark — no unread notifications.")
    action = {"type": "notifications_mark_read",
              "label": f"Mark {len(unread)} notification(s) as read"}
    return _ok_action(
        f"Ready to mark all {len(unread)} unread notification(s) as read. "
        f"Press Confirm to proceed.", action)


def _answer_export_report_action(q: str) -> dict:
    fmt = "excel" if re.search(r"\bexcel\b|\bxlsx\b|\bspreadsheet\b", q) else "pdf"
    action = {"type": "export_report", "format": fmt,
              "label": f"Export business report as {fmt.upper()}"}
    return _ok_action(
        f"Ready to export the full business report (KPIs, bookings, and all "
        f"analytics sections) as {fmt.upper()} to your home folder. "
        f"Press Confirm to proceed.", action)


def _answer_followup_add_action(q: str, raw: str) -> dict:
    cust = _find_customer(q)
    if cust is None:
        return _plain(
            "To schedule a follow-up, tell me the customer and when — e.g. "
            "\"add a follow-up for Maria Cruz on Aug 20 about final headcount\" "
            "or \"follow up with Juan tomorrow\".")
    date_str = None
    if re.search(r"\btoday\b", q):
        date_str = date.today().strftime("%b %d, %Y")
    elif re.search(r"\btomorrow\b", q):
        date_str = (date.today() + timedelta(days=1)).strftime("%b %d, %Y")
    else:
        date_str = _parse_booking_date(q)
    if not date_str:
        return _plain(
            f"When should I follow up with {cust['name']}? Try \"today\", "
            f"\"tomorrow\", or a date like \"Aug 20\".")
    note_m = re.search(r"\b(?:about|regarding|re|note)\b[:\s]+(.{3,120})", raw, re.IGNORECASE)
    note = note_m.group(1).strip() if note_m else "Follow up via AI assistant"
    action = {"type": "follow_up_add", "customer_id": cust["id"], "name": cust["name"],
              "date": date_str, "note": note,
              "label": f"Schedule follow-up with {cust['name']} on {date_str}"}
    return _ok_action(
        f"Ready to schedule a follow-up:\n• {cust['name']} — {date_str}: {note}\n"
        f"Press Confirm to proceed.", action)


def _answer_followup_complete_action(q: str) -> dict:
    open_items = _safe(repo.get_overdue_follow_ups, []) + \
                 _safe(lambda: repo.get_upcoming_follow_ups(365), [])
    cust = _find_customer(q)
    if cust is None:
        if not open_items:
            return _plain("There are no open follow-ups to complete.")
        options = [{"label": _followup_line(f), "send": f"complete follow-up {f['id']}"}
                  for f in open_items[:8]]
        return _plain("Which follow-up should I mark done? Pick one:", options)
    hits = [f for f in open_items if f["customer_id"] == cust["id"]]
    if not hits:
        return _plain(f"No open follow-ups found for {cust['name']}.")
    if len(hits) > 1:
        options = [{"label": _followup_line(f), "send": f"complete follow-up {f['id']}"}
                  for f in hits[:8]]
        return _plain(f"{cust['name']} has {len(hits)} open follow-ups — which one?", options)
    f = hits[0]
    action = {"type": "follow_up_complete", "follow_up_id": f["id"],
              "label": f"Mark follow-up with {f['customer_name']} as done"}
    return _ok_action(
        f"Ready to mark this follow-up done:\n• {_followup_line(f)}\n"
        f"Press Confirm to proceed.", action)


def _answer_followup_complete_by_id(q: str) -> dict | None:
    """Direct 'complete follow-up <id>' from a picker click."""
    m = re.search(r"\bcomplete follow-up (\d+)\b", q)
    if not m:
        return None
    fid = int(m.group(1))
    open_items = _safe(repo.get_overdue_follow_ups, []) + \
                 _safe(lambda: repo.get_upcoming_follow_ups(365), [])
    f = next((x for x in open_items if x["id"] == fid), None)
    if f is None:
        return _plain("That follow-up is no longer open.")
    action = {"type": "follow_up_complete", "follow_up_id": f["id"],
              "label": f"Mark follow-up with {f['customer_name']} as done"}
    return _ok_action(
        f"Ready to mark this follow-up done:\n• {_followup_line(f)}\n"
        f"Press Confirm to proceed.", action)


def _answer_list_bookings(q: str) -> dict:
    """Bulleted list of bookings — ref, customer, date, pax, total, status."""
    rows = _safe(repo.get_bookings_any_status, [])
    # optional filters: status word, year, month
    for status in ("PENDING", "CONFIRMED", "COMPLETED", "CANCELLED"):
        if status.lower() in q:
            rows = [b for b in rows if b.get("status") == status]
            break
    years = _extract_years(q)
    month = _extract_month(q)
    if years or month:
        filtered = []
        for b in rows:
            d = _parse_date(b.get("date", ""))
            if d is None:
                continue
            if years and d.year not in years:
                continue
            if month and d.month != month:
                continue
            filtered.append(b)
        rows = filtered
    else:
        # relative/absolute phrasing not covered by year/month extraction —
        # "today", "yesterday", "this week", "last week", "March 5"
        r_start, r_end, _, r_gran = _resolve_range(q)
        if r_gran in ("day", "week"):
            filtered = []
            for b in rows:
                d = _parse_date(b.get("date", ""))
                if d is not None and r_start <= d <= r_end:
                    filtered.append(b)
            rows = filtered
    if not rows:
        return _plain("No bookings match that. Try \"list bookings\" for everything.")
    shown = rows[:15]
    lines = "\n".join(f"• {_booking_line(b)}" for b in shown)
    more = "" if len(rows) <= 15 else (f"\n…and {len(rows) - 15} more — see the "
                                       f"Orders page for the full list.")
    total_val = sum(float(b.get("total", 0)) for b in rows)
    return _plain(f"{len(rows)} booking(s), total value {_peso(total_val)}:\n"
                  f"{lines}{more}")


def _answer_list_customers(q: str) -> dict:
    """Bulleted list of customers — name, contact, event count, status, loyalty tier."""
    rows = _safe(repo.get_all_customers_with_loyalty, [])
    for status in ("INACTIVE", "ACTIVE"):
        if re.search(rf"\b{status.lower()}\b", q):
            rows = [c for c in rows if str(c.get("status", "")).upper() == status]
            break
    if not rows:
        return _plain("No customers match that. Try \"list customers\" for everything.")
    shown = rows[:15]
    lines = "\n".join(f"• {_customer_line(c)}" for c in shown)
    more = "" if len(rows) <= 15 else (f"\n…and {len(rows) - 15} more — see the "
                                       f"Customers page for the full list.")
    return _plain(f"{len(rows)} customer(s):\n{lines}{more}")


def _answer_list_invoices(q: str) -> dict:
    """Bulleted list of invoices — ref, customer, event date, amount, paid, status."""
    rows = _safe(repo.get_all_invoices, [])
    for status in ("UNPAID", "PARTIAL", "PAID"):
        if re.search(rf"\b{status.lower()}\b", q):
            rows = [i for i in rows if str(i.get("status", "")).upper() == status]
            break
    years = _extract_years(q)
    month = _extract_month(q)
    if years or month:
        filtered = []
        for i in rows:
            d = _parse_date(i.get("event_date", ""))
            if d is None:
                continue
            if years and d.year not in years:
                continue
            if month and d.month != month:
                continue
            filtered.append(i)
        rows = filtered
    else:
        r_start, r_end, _, r_gran = _resolve_range(q)
        if r_gran in ("day", "week"):
            filtered = []
            for i in rows:
                d = _parse_date(i.get("event_date", ""))
                if d is not None and r_start <= d <= r_end:
                    filtered.append(i)
            rows = filtered
    if not rows:
        return _plain("No invoices match that. Try \"list invoices\" for everything.")
    shown = rows[:15]
    lines = "\n".join(f"• {_invoice_line(i)}" for i in shown)
    more = "" if len(rows) <= 15 else (f"\n…and {len(rows) - 15} more — see the "
                                       f"Billing page for the full list.")
    total_val = sum(float(i.get("amount", 0)) for i in rows)
    return _plain(f"{len(rows)} invoice(s), total {_peso(total_val)}:\n{lines}{more}")


def _answer_list_expenses(q: str) -> dict:
    """Bulleted list of expenses, optionally filtered by category and/or a
    date range — today, yesterday, this/last week, this/last month,
    this/last year, a bare month/year, or a specific date."""
    rows = _safe(repo.get_all_expenses, [])
    category = _find_category(q)
    if category:
        rows = [e for e in rows if str(e.get("category", "")).lower() == category]

    r_start, r_end, r_label, r_gran = _resolve_range(q)
    if r_gran:
        filtered = []
        for e in rows:
            d = _parse_date(e.get("date", ""))
            if d is not None and r_start <= d <= r_end:
                filtered.append(e)
        rows = filtered

    if not rows:
        scope = f" for {r_label}" if r_label else ""
        return _plain(f"No expenses found{scope}. Try \"list expenses\" for everything.")
    shown = rows[:15]
    lines = "\n".join(f"• {_expense_line(e)}" for e in shown)
    more = "" if len(rows) <= 15 else (f"\n…and {len(rows) - 15} more — see the "
                                       f"Expenses page for the full list.")
    total_val = sum(float(e.get("amount", 0)) for e in rows)
    scope = f" ({r_label})" if r_label else ""
    return _plain(f"{len(rows)} expense(s){scope}, total {_peso(total_val)}:\n{lines}{more}")


def _audit(action_desc: str, table: str, record_id):
    """Every AI-executed action lands in the audit_logs table."""
    try:
        repo.write_audit_log("AI Assistant", action_desc, table,
                             int(record_id or 0),
                             new_value={"via": "ai_assistant"})
    except Exception:
        pass


def daily_briefing() -> dict:
    """Proactive summary (today's events, overdue/due follow-ups, unread
    notifications, unpaid invoices) — for the AI page to show on open."""
    return _answer_daily_briefing("")


def execute_action(action: dict) -> dict:
    """Perform a previously confirmed action. Returns {"ok", "message"}."""
    global _LAST_ACTION
    _LAST_ACTION = {}
    stamp = datetime.now().strftime("%b %d, %I:%M %p")
    try:
        kind = action.get("type")
        if kind == "booking_status":
            repo.update_booking_status(action["db_id"], action["status"],
                                       action.get("reason"))
            _audit(f"{action['status']} via AI assistant", "bookings", action["db_id"])
            try:
                from utils.signals import app_events
                app_events().booking_saved.emit()
            except Exception:
                pass
            done = {"CONFIRMED": "approved", "CANCELLED": "cancelled",
                    "COMPLETED": "marked completed"}.get(action["status"], "updated")
            undo = ("" if action["status"] == "COMPLETED" else
                    " If this was a mistake, you can change its status again in the Orders page.")
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — booking {action.get('ref')} has "
                               f"been {done}.{undo}"}

        if kind == "payment":
            result = repo.add_payment_record(
                action["invoice_id"], float(action["amount"]), None,
                action.get("method", "Cash"), "Recorded via AI assistant")
            _audit(f"Payment {_peso(float(action['amount']))} via AI assistant",
                   "invoices", action.get("invoice_id"))
            try:
                from utils.signals import app_events
                app_events().payment_recorded.emit()
            except Exception:
                pass
            if result:
                return {"ok": True,
                        "message": f"✅ Done ({stamp}) — {_peso(float(action['amount']))} "
                                   f"{action.get('method', 'Cash')} payment recorded for "
                                   f"{action.get('ref')}. New status: {result['new_status']}, "
                                   f"total paid {_peso(result['new_paid'])}. "
                                   f"Adjustments can be made in the Billing page."}
            return {"ok": True,
                    "message": f"✅ Payment for {action.get('ref')} was submitted ({stamp})."}

        if kind == "customer_delete":
            repo.delete_customer(action["db_id"])
            _audit("Customer deleted via AI assistant", "customers", action["db_id"])
            try:
                from utils.signals import app_events
                app_events().customer_saved.emit()
            except Exception:
                pass
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — customer {action.get('name')} "
                               f"has been deleted."}

        if kind == "customer_edit":
            cust = action.get("cust", {})
            data = {"name": cust.get("name", ""), "contact": cust.get("contact", ""),
                    "email": cust.get("email", ""), "address": cust.get("address", ""),
                    "status": cust.get("status", "Active")}
            data[action["field"]] = action["value"]
            repo.update_customer(action["db_id"], data)
            _audit(f"Customer {action['field']} updated via AI assistant",
                   "customers", action["db_id"])
            try:
                from utils.signals import app_events
                app_events().customer_saved.emit()
            except Exception:
                pass
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — {cust.get('name')}'s "
                               f"{action['field']} updated to \"{action['value']}\"."}

        if kind == "expense_delete":
            repo.delete_expense(action["exp_id"])
            _audit("Expense deleted via AI assistant", "expenses", action["exp_id"])
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — the expense has been deleted."}

        if kind == "customer_create":
            data = action.get("data", {})
            cust_id = repo.add_customer(data)
            _audit("Customer added via AI assistant", "customers", cust_id)
            try:
                from utils.signals import app_events
                app_events().customer_saved.emit()
            except Exception:
                pass
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — customer {data.get('name')} added. "
                               f"You can now create bookings for them; edit details "
                               f"anytime in the Customers page."}

        if kind == "booking_create":
            data = action.get("data", {})
            result = repo.create_booking(data)
            try:
                from utils.signals import app_events
                app_events().booking_saved.emit()
            except Exception:
                pass
            if result:
                _audit("Booking created via AI assistant", "bookings",
                       result.get("booking_id"))
                return {"ok": True,
                        "message": f"✅ Done ({stamp}) — booking "
                                   f"{result.get('booking_ref')} created for "
                                   f"{data.get('name')} on {data.get('date')} "
                                   f"({data.get('pax')} pax, {_peso(float(data.get('total', 0)))}). "
                                   f"It's PENDING — approve it when ready. Fine-tune "
                                   f"venue/occasion in the Orders page."}
            return {"ok": False,
                    "message": "The booking could not be created — please try from "
                               "the Orders page."}

        if kind == "expense":
            today = datetime.now().strftime("%b %d, %Y")
            exp_id = repo.add_expense({"category": action["category"],
                                       "description": action["description"],
                                       "amount": float(action["amount"]), "date": today})
            _audit(f"Expense {_peso(float(action['amount']))} via AI assistant",
                   "expenses", exp_id)
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — {_peso(float(action['amount']))} "
                               f"{action['category']} expense recorded. You can edit or "
                               f"delete it in the Expenses page."}

        if kind == "loyalty_recalc":
            repo.recalculate_loyalty(action["customer_id"])
            _audit("Loyalty tier recalculated via AI assistant", "customers",
                   action["customer_id"])
            try:
                from utils.signals import app_events
                app_events().customer_saved.emit()
            except Exception:
                pass
            cust = next((c for c in _safe(repo.get_all_customers_with_loyalty, [])
                        if c.get("id") == action["customer_id"]), None)
            tier = cust.get("loyalty_tier", "?") if cust else "?"
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — {action.get('name')}'s loyalty "
                               f"tier recalculated. Current tier: {tier}."}

        if kind == "notifications_mark_read":
            repo.mark_all_notifications_read()
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — all notifications marked as read."}

        if kind == "follow_up_add":
            fu_id = repo.add_follow_up(action["customer_id"], action["date"], action["note"])
            _audit("Follow-up added via AI assistant", "customer_follow_ups",
                   fu_id or 0)
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — follow-up with "
                               f"{action.get('name')} scheduled for {action['date']}."}

        if kind == "follow_up_complete":
            repo.complete_follow_up(action["follow_up_id"])
            _audit("Follow-up completed via AI assistant", "customer_follow_ups",
                   action["follow_up_id"])
            return {"ok": True,
                    "message": f"✅ Done ({stamp}) — follow-up marked complete."}

        if kind == "export_report":
            import os
            import utils.exporter as _exporter
            fmt = action.get("format", "pdf")
            kpis = _safe(lambda: repo.get_report_kpis(), {})
            bookings = _safe(repo.get_all_bookings, [])
            sections = _safe(_exporter.build_analytics_sections, [])
            biz = _safe(repo.get_business_info, {})
            biz_name = biz.get("name") or "Jayraldine's Catering"
            fname = f"jayraldines_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{'xlsx' if fmt == 'excel' else 'pdf'}"
            path = os.path.join(os.path.expanduser("~"), fname)
            ok = (_exporter.export_excel(path, kpis, bookings, "Business Report",
                                         "All Time", biz_name, sections=sections)
                  if fmt == "excel" else
                  _exporter.export_pdf(path, kpis, bookings, "Business Report",
                                       "All Time", biz_name, sections=sections))
            if ok:
                return {"ok": True,
                        "message": f"✅ Done ({stamp}) — report exported to:\n{path}"}
            lib = "openpyxl" if fmt == "excel" else "reportlab"
            return {"ok": False,
                    "message": f"Export failed — make sure {lib} is installed "
                               f"(pip install {lib})."}

        return {"ok": False, "message": "Unknown action type."}
    except Exception as e:
        return {"ok": False,
                "message": f"The action failed and nothing was changed: {e}. "
                           f"Please try again or do it from the relevant page."}


# ─────────────────────────────────────────────────────────────────────────────
# In-chat creation flows (customer / booking / expense)
# ─────────────────────────────────────────────────────────────────────────────

_PHONE_RE = re.compile(r"(?:\+?63|0)9\d{2}[-\s]?\d{3}[-\s]?\d{4}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SKIP_RE = re.compile(r"^\s*(skip|none|wala|n/?a)\s*$", re.IGNORECASE)


def _clean_name(raw: str) -> str:
    """Strip command words, phone, and email from raw text; what's left is the name."""
    s = _PHONE_RE.sub(" ", raw)
    s = _EMAIL_RE.sub(" ", s)
    s = re.sub(r"\b(add|create|new|register|customer|please|a|an|i want to|gusto ko)\b",
               " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" ,.-")
    return s.title() if s and s == s.lower() else s


def _customer_create_step(data: dict):
    """Ask for the next missing customer field, or return the Confirm card."""
    global _PENDING
    if not data.get("name"):
        _PENDING = {"kind": "customer_create", "data": data, "step": "name"}
        return _plain("Let's add a new customer. What's the customer's full name?")
    if not data.get("contact"):
        _PENDING = {"kind": "customer_create", "data": data, "step": "contact"}
        return _plain(f"Got it — {data['name']}. What's their contact number? "
                      f"(e.g. 09171234567)")
    if "email" not in data:
        _PENDING = {"kind": "customer_create", "data": data, "step": "email"}
        return _plain("Email address? (type \"skip\" if none)",
                      [{"label": "Skip email", "send": "skip"}])
    if "address" not in data:
        if data.get("addr_base"):
            _PENDING = {"kind": "customer_create", "data": data, "step": "addr_street"}
            return _plain(f"Address area: {data['addr_base']}. Street / house no.? "
                          f"(e.g. \"Block 5 Lot 3, Rizal St.\" — or \"skip\")",
                          [{"label": "Skip street", "send": "skip"}])
        _PENDING = {"kind": "customer_create", "data": data, "step": "address"}
        return _plain("Address — type part of it to search the address database "
                      "(e.g. \"Lahug\" or \"Mandaue\") and pick from the matches, "
                      "or \"skip\" if none.",
                      [{"label": "Skip address", "send": "skip"}])
    _PENDING = {}
    data.pop("addr_base", None)
    action = {"type": "customer_create", "data": dict(data),
              "label": f"Add customer {data['name']} ({data.get('contact', '')})"}
    details = "\n".join(f"• {k.title()}: {v or '—'}"
                        for k, v in [("name", data.get("name")),
                                     ("contact", data.get("contact")),
                                     ("email", data.get("email")),
                                     ("address", data.get("address"))])
    return _ok_action(f"Ready to add this customer:\n{details}\nPress Confirm to save.",
                      action)


def _start_customer_create(raw: str):
    data = {}
    phone_m = _PHONE_RE.search(raw)
    if phone_m:
        data["contact"] = re.sub(r"[-\s]", "", phone_m.group(0))
    email_m = _EMAIL_RE.search(raw)
    if email_m:
        data["email"] = email_m.group(0)
    name = _clean_name(raw)
    if name:
        data["name"] = name
    # Inline one-shot ("add customer Juan Cruz 09171234567"): only email and
    # address remain — treat them as skipped so the Confirm card shows now.
    if data.get("name") and data.get("contact"):
        data.setdefault("email", "")
        data.setdefault("address", "")
    return _customer_create_step(data)


def _booking_create_step(data: dict):
    """Ask for the next missing booking field, or return the Confirm card."""
    global _PENDING
    if not data.get("customer"):
        _PENDING = {"kind": "booking_create", "data": data, "step": "customer"}
        customers = _safe(repo.get_all_customers_with_loyalty, [])
        options = [{"label": c.get("name", ""), "send": c.get("name", "")}
                   for c in customers[:8] if c.get("name")]
        more = ""
        if len(customers) > 8:
            more = (f" (Showing 8 of {len(customers)} — type part of a name, "
                    f"contact, or email to search all.)")
        return _plain("Let's create a booking. Which customer is it for? "
                      "It must be an existing customer." + more, options)
    if not data.get("date"):
        _PENDING = {"kind": "booking_create", "data": data, "step": "date"}
        return _plain(f"Booking for {data['customer']['name']} — what's the event "
                      f"date? (e.g. \"Aug 20\" or \"Aug 20 2027\")")
    if not data.get("pax"):
        _PENDING = {"kind": "booking_create", "data": data, "step": "pax"}
        return _plain(f"How many pax on {data['date']}?")
    if not data.get("package"):
        _PENDING = {"kind": "booking_create", "data": data, "step": "package"}
        packages = _safe(repo.get_all_packages, [])[:8]
        if not packages:
            _PENDING = {}
            return _plain("There are no packages defined yet — add one in the Menu "
                          "page first, or create this booking from the Orders page "
                          "with a custom menu.")
        options = [{"label": f"{p['name']} — {_peso(float(p.get('price_per_pax', 0)))}/pax",
                    "send": p["name"]} for p in packages]
        return _plain("Which package?", options)
    if not data.get("venue"):
        if data.get("venue_base"):
            _PENDING = {"kind": "booking_create", "data": data, "step": "street"}
            return _plain(f"Venue area: {data['venue_base']}. Street / house no.? "
                          f"(e.g. \"Block 5 Lot 3, Rizal St.\" — or \"skip\")",
                          [{"label": "Skip street", "send": "skip"}])
        _PENDING = {"kind": "booking_create", "data": data, "step": "venue"}
        cust_addr = data["customer"].get("address", "")
        options = ([{"label": f"Use customer's address — {cust_addr}", "send": "skip"}]
                   if cust_addr else [])
        return _plain("Where is the event? Type part of the address to search "
                      "(e.g. \"Mandaue\" or \"Lahug\") and I'll show matches to "
                      "pick from — or \"skip\" to use the customer's address.",
                      options)

    _PENDING = {}
    cust, pkg = data["customer"], data["package"]
    rate = float(pkg.get("price_per_pax", 0))
    total = rate * int(data["pax"])
    occasions = _safe(repo.get_all_occasions, [])
    booking_data = {
        "name":       cust.get("name", ""),
        "contact":    cust.get("contact", ""),
        "email":      cust.get("email", ""),
        "address":    cust.get("address", ""),
        "occasion":   occasions[0] if occasions else "Other",
        "venue":      cust.get("address", "") or "TBD",
        "date":       data["date"],
        "time":       "6:00 PM",
        "pax":        int(data["pax"]),
        "notes":      "Created via AI assistant",
        "menu_type":  "package",
        "menu_value": pkg.get("name", ""),
        "total":      total,
        "status":     "PENDING",
    }
    booking_data["venue"] = data.get("venue") or cust.get("address", "") or "TBD"
    action = {"type": "booking_create", "data": booking_data,
              "label": f"Create booking — {cust.get('name')} on {data['date']}, "
                       f"{data['pax']} pax, {pkg.get('name')} ({_peso(total)})"}
    return _ok_action(
        f"Ready to create this booking (it will start as PENDING):\n"
        f"• Customer: {cust.get('name')}\n• Date: {data['date']} at 6:00 PM\n"
        f"• Pax: {data['pax']}\n• Package: {pkg.get('name')} "
        f"({_peso(rate)}/pax → total {_peso(total)})\n"
        f"• Venue: {booking_data['venue']}\n"
        f"Time and occasion can be fine-tuned in the Orders page afterwards.\n"
        f"Press Confirm to save.", action)


def _parse_booking_date(q: str):
    md = _extract_day(q)
    if not md:
        return None
    years = [y for y in _extract_years(q)]
    year = years[0] if years else datetime.now().year
    try:
        return date(year, md[0], md[1]).strftime("%b %d, %Y")
    except ValueError:
        return None


# "add/create new X" for things still made in their own pages
_CREATE_GUIDES = [
    (r"\b(add|create|new|make)\b.{0,24}\binvoice\b", "invoice"),
    (r"\b(add|create|new)\b.{0,24}\b(menu|dish|item)\b", "menu"),
    (r"\b(add|create|new)\b.{0,24}\bpackage\b", "package"),
    (r"\b(add|create|new)\b.{0,24}\boccasion\b", "occasion"),
]


def _detect_create(q: str, raw: str = ""):
    if re.search(r"\b(add|create|new|register)\b.{0,24}\bcustomer\b", q):
        return _start_customer_create(raw or q)
    if re.search(r"\b(add|create|new|make|start)\b.{0,24}\b(booking|reservation|event)\b", q) or \
       re.search(r"(?<!my )(?<!the )(?<!our )(?<!a )\bschedule\b.{0,24}\b(booking|reservation|event)\b", q):
        return _booking_create_step({})
    for pattern, key in _CREATE_GUIDES:
        if re.search(pattern, q):
            return {"ok": True, "answer": _HOWTO[key], "chart": None,
                    "action": None, "error": ""}
    return None


def _is_new_request(q: str) -> bool:
    """A message that clearly starts a different task (exits pending state)."""
    if _detect_action(q) is not None:
        return True
    if _detect_create(q) is not None:
        return True
    return bool(re.search(
        r"\bcompare\b|\bhow much\b|\bhow many\b|\btop\b|\bbest\b|\bupcoming\b"
        r"|\bbreakdown\b|\bweekly\b|\bsummary\b|\breport\b|\bunpaid\b", q))


def _resolve_pending(q: str, raw: str = ""):
    """Continue a 'which one?' follow-up. While a question is pending, the
    user's reply is read FIRST as its answer; the help menu never shows.
    Returns a result dict, or None to route the message normally."""
    global _PENDING
    if not _PENDING:
        return None
    pending = dict(_PENDING)
    raw = raw or q.strip()

    # Explicit abort — drop the pending action gracefully.
    if re.search(_EXIT_WORDS, q.strip()):
        _PENDING = {}
        return _plain("Okay, I've dropped that — nothing was changed.")

    # Creation slot answers are free-form text (names, addresses) — handle them
    # BEFORE the new-request escape so e.g. an address containing "St." or a
    # customer named "May" is never misrouted.
    if pending.get("kind") == "customer_create":
        data = dict(pending.get("data", {}))
        step = pending.get("step")
        _PENDING = {}
        if step == "email" and _SKIP_RE.match(raw):
            data["email"] = ""
        elif step == "name":
            name = _clean_name(raw)
            if not name:
                return _customer_create_step(data)  # re-asks name
            data["name"] = name
        elif step == "contact":
            phone_m = _PHONE_RE.search(raw) or re.search(r"[\d][\d\-\s]{6,}", raw)
            if not phone_m:
                _PENDING = pending
                return _plain("That doesn't look like a contact number — try "
                              "e.g. 09171234567, or say \"never mind\".")
            data["contact"] = re.sub(r"[-\s]", "", phone_m.group(0))
        elif step == "email":
            m = _EMAIL_RE.search(raw)
            data["email"] = m.group(0) if m else raw.strip()
        elif step == "address":
            # Addresses come from the DB — search and select, never free text.
            if _SKIP_RE.match(raw):
                data["address"] = ""
            else:
                picked = _match_candidate(raw, pending.get("addr_options"))
                if picked:
                    data["addr_base"] = picked
                else:
                    texts = _search_addresses(raw)
                    if len(texts) == 1:
                        data["addr_base"] = texts[0]
                    elif texts:
                        pending["addr_options"] = texts
                        _PENDING = pending
                        options = [{"label": t, "send": t} for t in texts]
                        return _plain(
                            f"I found {len(texts)} matching address(es) — pick one, "
                            f"or type a more specific search:", options)
                    else:
                        _PENDING = pending
                        return _plain(
                            "No address matched that — try a barangay or city name "
                            "(e.g. \"Lahug\", \"Mandaue\"), or \"skip\".")
        elif step == "addr_street":
            if _SKIP_RE.match(raw):
                data["address"] = data.get("addr_base", "")
            else:
                data["address"] = f"{raw.strip()}, {data.get('addr_base', '')}".strip(", ")
        return _customer_create_step(data)

    if pending.get("kind") == "booking_create":
        data = dict(pending.get("data", {}))
        step = pending.get("step")
        _PENDING = {}
        if step == "customer":
            hits = _find_customers_all(_strip_cmd_words(q)) or \
                ([_find_customer(q)] if _find_customer(q) else [])
            if not hits:
                _PENDING = pending
                return _plain("I couldn't find that customer — type part of their "
                              "name, contact, or email, or add them first with "
                              "\"add customer\".")
            if len(hits) > 1:
                _PENDING = pending
                options = [{"label": f"{c.get('name')} ({c.get('contact', '—')})",
                            "send": c.get("name", "")} for c in hits[:8]]
                return _plain(f"{len(hits)} customers match — pick one:", options)
            data["customer"] = hits[0]
        elif step == "date":
            d = _parse_booking_date(q)
            if d is None:
                _PENDING = pending
                return _plain("I couldn't read that date — try \"Aug 20\" or "
                              "\"Aug 20 2027\".")
            data["date"] = d
        elif step == "pax":
            m = re.search(r"(\d{1,4})", q)
            if not m:
                _PENDING = pending
                return _plain("How many guests? Just type a number, e.g. 150.")
            data["pax"] = int(m.group(1))
        elif step == "package":
            packages = _safe(repo.get_all_packages, [])
            pick = next((p for p in packages
                         if (p.get("name") or "").lower() in q), None)
            if pick is None:
                _PENDING = pending
                options = [{"label": f"{p['name']} — {_peso(float(p.get('price_per_pax', 0)))}/pax",
                            "send": p["name"]} for p in packages[:8]]
                return _plain("Which package? Pick one:", options)
            data["package"] = pick
        elif step == "venue":
            if _SKIP_RE.match(raw):
                data["venue"] = data["customer"].get("address", "") or "TBD"
            else:
                # a click on a previously offered option resolves directly —
                # no re-search (commas break the SQL matcher)
                picked = _match_candidate(raw, pending.get("addr_options"))
                if picked:
                    data["venue_base"] = picked
                else:
                    texts = _search_addresses(raw)
                    if len(texts) == 1:
                        data["venue_base"] = texts[0]
                    elif texts:
                        pending["addr_options"] = texts
                        _PENDING = pending
                        options = [{"label": t, "send": t} for t in texts]
                        return _plain(
                            f"I found {len(texts)} matching address(es) — pick one, "
                            f"or type a more specific search:", options)
                    else:
                        _PENDING = pending
                        return _plain(
                            "No address matched that — try another keyword (barangay "
                            "or city name, e.g. \"Lahug\" or \"Mandaue\"), or \"skip\" "
                            "to use the customer's address.")
        elif step == "street":
            if _SKIP_RE.match(raw):
                data["venue"] = data.get("venue_base", "")
            else:
                data["venue"] = f"{raw.strip()}, {data.get('venue_base', '')}".strip(", ")
        return _booking_create_step(data)

    if pending.get("kind") == "customer_pick":
        verb = pending["verb"]
        if re.search(r"\bsearch customer\b", q):
            _PENDING = pending
            return _plain("Type any part of the customer's name, contact number, "
                          "or email and I'll find them.")
        hits = _find_customers_all(_strip_cmd_words(q))
        if len(hits) == 1:
            _PENDING = {}
            target = f"{verb} customer {hits[0].get('name', '')}".lower()
            if verb == "delete":
                return _answer_customer_delete(target)
            return _answer_customer_edit(target, raw)
        if len(hits) > 1:
            # narrow the picker to the matches (keeps searching within them)
            return _customer_picker(
                verb, hits, intro=f"{len(hits)} customers match — pick one or "
                                  f"type more of the name.")
        if _is_new_request(q):
            _PENDING = {}
            return None
        return _customer_picker(
            verb, intro="I couldn't find that customer — pick one, type part of "
                        "the name to search, or say \"never mind\".")

    if pending.get("kind") == "customer_edit":
        cust = dict(pending.get("cust", {}))
        step = pending.get("step")
        _PENDING = {}
        if step == "field":
            field = next((f for f in _EDIT_FIELDS if f in q), None)
            if field is None and re.search(r"\bnumber\b|\bphone\b", q):
                field = "contact"
            if field is None:
                _PENDING = pending
                return _plain("Which detail — contact, email, address, or name?")
            if field == "address":
                _PENDING = {"kind": "customer_edit", "cust": cust, "step": "addr"}
                return _plain("New address — type part of it to search the address "
                              "database and pick from the matches.")
            _PENDING = {"kind": "customer_edit", "cust": cust, "step": field}
            return _plain(f"New {field} for {cust.get('name')}?")
        if step == "contact":
            phone_m = _PHONE_RE.search(raw) or re.search(r"[\d][\d\-\s]{6,}", raw)
            if not phone_m:
                _PENDING = pending
                return _plain("That doesn't look like a contact number — try "
                              "e.g. 09171234567.")
            return _customer_edit_confirm(cust, "contact",
                                          re.sub(r"[-\s]", "", phone_m.group(0)))
        if step == "email":
            m = _EMAIL_RE.search(raw)
            return _customer_edit_confirm(cust, "email",
                                          m.group(0) if m else raw.strip())
        if step == "name":
            name = _clean_name(raw) or raw.strip()
            return _customer_edit_confirm(cust, "name", name)
        if step == "addr":
            picked = _match_candidate(raw, pending.get("addr_options"))
            if not picked:
                texts = _search_addresses(raw)
                if len(texts) == 1:
                    picked = texts[0]
                elif texts:
                    pending["addr_options"] = texts
                    _PENDING = pending
                    return _plain(f"I found {len(texts)} matching address(es) — pick "
                                  f"one or refine the search:",
                                  [{"label": t, "send": t} for t in texts])
                else:
                    _PENDING = pending
                    return _plain("No address matched — try a barangay or city name "
                                  "(e.g. \"Lahug\", \"Mandaue\").")
            _PENDING = {"kind": "customer_edit", "cust": cust,
                        "step": "addr_street", "addr_base": picked}
            return _plain(f"Address area: {picked}. Street / house no.? (or \"skip\")",
                          [{"label": "Skip street", "send": "skip"}])
        if step == "addr_street":
            base = pending.get("addr_base", "")
            value = base if _SKIP_RE.match(raw) else f"{raw.strip()}, {base}".strip(", ")
            return _customer_edit_confirm(cust, "address", value)

    if pending.get("kind") == "expense_category":
        _PENDING = {}
        category = _find_category(q)
        if category:
            return _answer_expense_action(q if "expense" in q else f"add expense {q}")
        _PENDING = pending
        options = [{"label": c, "send": f"add expense {c.lower()}"}
                   for c in _EXPENSE_CHIP_CATEGORIES]
        return _plain("Pick one of these categories:", options)

    if pending.get("kind") == "expense_amount":
        _PENDING = {}
        amt_m = re.search(r"([\d][\d,]*(?:\.\d+)?)", q)
        if not amt_m:
            _PENDING = pending
            return _plain(f"How much for the {pending['category'].title()} expense? "
                          f"Type a number, or say \"never mind\".")
        amount = float(amt_m.group(1).replace(",", ""))
        desc = re.sub(r"[\d,.]+", "", raw, count=1).strip() or "Added via AI assistant"
        return _expense_confirm(pending["category"], amount, desc)

    if pending.get("kind") == "expense_amount_known":
        _PENDING = {}
        category = _find_category(q)
        if not category:
            _PENDING = pending
            options = [{"label": c, "send": c.lower()} for c in _EXPENSE_CHIP_CATEGORIES]
            return _plain("Pick a category for that expense:", options)
        return _expense_confirm(category, pending["amount"], "Added via AI assistant")

    # A message that clearly starts a different task exits the pending state
    # BEFORE any resolution attempt — otherwise digits in the new command
    # (years, amounts, other refs) could be misread as an answer.
    if _detect_action(q) is not None or _detect_create(q, raw) is not None:
        _PENDING = {}
        return None

    if pending.get("kind") == "booking":
        hits = _find_bookings(q, pending["from"])
        if not hits:
            candidates = [b for b in _safe(repo.get_bookings_any_status, [])
                          if b.get("status") in pending["from"]]
            hits = _loose_ref_match(candidates, q, "ref")
        if len(hits) == 1:
            _PENDING = {}
            return _answer_booking_action(
                f"{pending['verb']} booking {hits[0]['ref']} {q}",
                pending["status"], pending["verb"], pending["from"])
        if len(hits) > 1:
            options = [{"label": _booking_line(b),
                        "send": f"{pending['verb']} booking {b['ref']}"}
                       for b in hits[:8]]
            return _plain(f"That matches {len(hits)} bookings — which one?", options)
        if _is_new_request(q):
            _PENDING = {}
            return None
        return _plain("I couldn't find that booking — give me its reference "
                      "(e.g. BK-001) or the customer's name, or say \"never mind\".")

    if pending.get("kind") == "payment":
        invoices = [i for i in _safe(repo.get_all_invoices, [])
                    if str(i.get("status", "")).lower() != "paid"]
        if _ref_number(_INV_REF_RE, q) is not None or _find_customer(q):
            _PENDING = {}
            return _answer_payment_action(f"record payment {q}")
        loose = _loose_ref_match(invoices, q, "invoice")
        if len(loose) == 1:
            _PENDING = {}
            return _answer_payment_action(
                f"record payment for {loose[0].get('invoice')} {q}")
        if len(loose) > 1:
            options = [{"label": f"{i.get('invoice')} — {i.get('customer')}",
                        "send": f"record payment for {i.get('invoice')}"}
                       for i in loose[:8]]
            return _plain("That matches more than one invoice — which one?", options)
        if _is_new_request(q):
            _PENDING = {}
            return None
        return _plain("I couldn't match that to an unpaid invoice — give me the "
                      "invoice reference (e.g. INV-001) or the customer's name, "
                      "or say \"never mind\".")

    if pending.get("kind") == "payment_amount":
        amt_m = re.search(r"([\d][\d,]*(?:\.\d+)?)", q)
        if amt_m or re.search(r"\bfull\b|\bsettle\b|\bbalance\b|\ball\b", q):
            _PENDING = {}
            amount = amt_m.group(1) if amt_m else "full"
            return _answer_payment_action(
                f"record {amount} payment for {pending['ref']} {q}")
        if _is_new_request(q):
            _PENDING = {}
            return None
        return _plain(f"How much should I record for {pending['ref']}? Type the "
                      f"amount (e.g. 5000) or \"full\" — or say \"never mind\".")

    if pending.get("kind") == "loyalty_pick":
        hits = _find_customers_all(_strip_cmd_words(q))
        if len(hits) == 1:
            _PENDING = {}
            return _answer_loyalty_recalc_action(f"recalculate loyalty for {hits[0]['name']}")
        if len(hits) > 1:
            _PENDING = {"kind": "loyalty_pick"}
            options = _customer_options("recalculate loyalty for", hits)
            return _plain(f"{len(hits)} customers match — pick one:", options)
        if _is_new_request(q):
            _PENDING = {}
            return None
        return _plain("I couldn't find that customer — type part of their name, "
                      "or say \"never mind\".")

    _PENDING = {}
    return None


_BK_WORD = r"(?:booking|order|reservation|event|(?:bkg|bk)[-\s]?\d+)"

_EDIT_FIELDS = ("contact", "email", "address", "name")


_CMD_WORDS_RE = re.compile(
    r"\b(delete|remove|erase|edit|update|change|modify|customer|booking|the|of|a)\b")


def _strip_cmd_words(q: str) -> str:
    return re.sub(r"\s+", " ", _CMD_WORDS_RE.sub(" ", q)).strip()


def _find_customers_all(q: str) -> list[dict]:
    """All customers matching the reply — by honorific-cleaned name, contact
    number digits, or email."""
    if not q.strip():
        return []
    return [c for c in _safe(repo.get_all_customers_with_loyalty, [])
            if _customer_matches(c, q)]


def _customer_options(verb: str, customers: list[dict]) -> list:
    return [{"label": f"{c.get('name')} ({c.get('contact', '—')})",
             "send": f"{verb} customer {c.get('name')}"}
            for c in customers[:8] if c.get("name")]


def _customer_picker(verb: str, customers: list[dict] | None = None,
                     intro: str | None = None) -> dict:
    """Searchable customer picker — shows up to 8, filterable by typing any
    part of a name, contact number, or email."""
    global _PENDING
    all_cust = customers if customers is not None \
        else _safe(repo.get_all_customers_with_loyalty, [])
    _PENDING = {"kind": "customer_pick", "verb": verb}
    options = _customer_options(verb, all_cust)
    more = ""
    if len(all_cust) > 8:
        more = (f" Showing 8 of {len(all_cust)} — type part of a name, contact "
                f"number, or email to search all of them.")
        options.append({"label": "🔍 Search customer (type name, contact, or email)",
                        "send": "search customer"})
    return _plain((intro or f"Which customer do you want to {verb}? "
                            f"Pick one or type the name.") + more, options)


def _answer_customer_delete(q: str) -> dict:
    global _PENDING
    q_name = _strip_cmd_words(q)
    cust = _find_customer(q_name) if q_name else None
    if cust is None:
        return _customer_picker("delete",
                                intro="Which customer should I remove? "
                                      "Pick one or type the name.")
    _PENDING = {}
    action = {"type": "customer_delete", "db_id": cust.get("id"),
              "name": cust.get("name"), "risk": "high",
              "label": f"Delete customer {cust.get('name')}"}
    return _ok_action(
        f"⚠ Ready to DELETE customer {cust.get('name')} "
        f"({cust.get('contact', '—')}, {cust.get('events', 0)} past event(s)).\n"
        f"This removes their record permanently and cannot be undone from chat. "
        f"Press Confirm only if you're sure.", action)


def _answer_customer_edit(q: str, raw: str) -> dict:
    global _PENDING
    q_name = _strip_cmd_words(q)
    cust = _find_customer(q_name) if q_name else None
    if cust is None:
        return _customer_picker("edit")

    # one-shot: a new phone/email included in the same message
    phone_m = _PHONE_RE.search(raw)
    if phone_m:
        return _customer_edit_confirm(cust, "contact",
                                      re.sub(r"[-\s]", "", phone_m.group(0)))
    email_m = _EMAIL_RE.search(raw)
    if email_m:
        return _customer_edit_confirm(cust, "email", email_m.group(0))

    _PENDING = {"kind": "customer_edit", "cust": cust, "step": "field"}
    options = [{"label": f"Contact ({cust.get('contact', '—')})", "send": "contact"},
               {"label": f"Email ({cust.get('email') or '—'})", "send": "email"},
               {"label": f"Address ({cust.get('address') or '—'})", "send": "address"},
               {"label": f"Name ({cust.get('name')})", "send": "name"}]
    return _plain(f"Editing {cust.get('name')} — which detail do you want to change?",
                  options)


def _customer_edit_confirm(cust: dict, field: str, value: str) -> dict:
    global _PENDING
    _PENDING = {}
    action = {"type": "customer_edit", "db_id": cust.get("id"), "cust": dict(cust),
              "field": field, "value": value,
              "label": f"Update {cust.get('name')}'s {field} to \"{value}\""}
    old = cust.get(field) or "—"
    return _ok_action(
        f"Ready to update {cust.get('name')}:\n• {field.title()}: {old} → {value}\n"
        f"Press Confirm to save.", action)


def _answer_expense_delete(q: str) -> dict:
    global _PENDING
    expenses = _safe(repo.get_all_expenses, [])
    if not expenses:
        return _plain("There are no expenses recorded to delete.")
    id_m = re.search(r"\b(\d+)\b", q)   # "#" is stripped by normalization
    if id_m:
        exp = next((e for e in expenses if int(e.get("id", -1)) == int(id_m.group(1))), None)
        if exp:
            _PENDING = {}
            action = {"type": "expense_delete", "exp_id": exp["id"], "risk": "high",
                      "label": f"Delete expense {exp['id']} — {exp['category']} "
                               f"{_peso(exp['amount'])} ({exp['date']})"}
            return _ok_action(
                f"⚠ Ready to DELETE this expense:\n• {exp['date']} — {exp['category']}: "
                f"{_peso(exp['amount'])} ({exp['description']})\nPress Confirm to proceed.",
                action)
    options = [{"label": f"{e['date']} — {e['category']}: {_peso(e['amount'])} "
                         f"({str(e['description'])[:28]})",
                "send": f"delete expense {e['id']}"}
               for e in expenses[:8]]
    return _plain("Which expense should I delete? Pick one:", options)


def _detect_action(q: str):
    """Route action-style requests. Returns a result dict or None."""
    # follow-up actions — checked first: "mark ... done" and "complete ..."
    # are generic enough to otherwise be grabbed by the booking-completion
    # check further down whenever the message happens to mention a follow-up.
    if re.search(r"\bcomplete follow-up \d+\b", q):
        return _answer_followup_complete_by_id(q)
    if (re.search(r"\bfollow[\s-]?up", q) and
            re.search(r"\b(complete|finish|done)\b", q)):
        return _answer_followup_complete_action(q)
    if re.search(r"\b(add|schedule|create|set|make)\b.{0,24}\bfollow[\s-]?up"
                 r"|\bfollow[\s-]?up\b.{0,20}\bwith\b", q):
        return _answer_followup_add_action(q, q)
    # edit / delete customer (checked early so "customer" keywords don't
    # fall into the top-customers lookup)
    if re.search(r"\b(delete|remove|erase)\b.{0,24}\bcustomer\b"
                 r"|\bcustomer\b.{0,16}\b(delete|remove)\b", q):
        return _answer_customer_delete(q)
    if re.search(r"\b(edit|update|change|modify)\b.{0,24}\bcustomer\b"
                 r"|\bcustomer\b.{0,16}\b(edit|update|change)\b", q):
        return _answer_customer_edit(q, q)
    # "change Maria's number/email/address" without the word customer
    if re.search(r"\b(edit|update|change|modify)\b", q) and _find_customer(q) and \
            re.search(r"\b(contact|number|phone|email|address)\b", q):
        return _answer_customer_edit(q, q)
    if re.search(r"\b(delete|remove)\b.{0,20}\bexpense\b", q):
        return _answer_expense_delete(q)
    if re.search(r"\b(edit|update|change|reschedule)\b.{0,24}\b(booking|order|reservation)\b", q):
        return _plain("Bookings are edited in the Orders page — only PENDING "
                      "bookings can be edited (click the pencil icon). To change "
                      "the status, tell me e.g. \"approve BKG-007\" or "
                      "\"cancel BKG-007\".")
    if re.search(rf"\b(approve|confirm|accept)\b.{{0,30}}\b{_BK_WORD}"
                 rf"|\b{_BK_WORD}\b.{{0,20}}\b(approve|confirm)\b", q):
        return _answer_booking_action(q, "CONFIRMED", "approve", ("PENDING",))
    if re.search(rf"\b(cancel|delete|remove)\b.{{0,30}}\b{_BK_WORD}"
                 rf"|\b{_BK_WORD}\b.{{0,20}}\b(cancel|delete|remove)\b", q):
        return _answer_booking_action(q, "CANCELLED", "cancel", ("PENDING", "CONFIRMED"))
    if re.search(rf"\b(complete|finish|done)\b.{{0,30}}\b{_BK_WORD}"
                 r"|mark.{0,24}\b(completed|done)\b", q):
        return _answer_booking_action(q, "COMPLETED", "complete", ("CONFIRMED",))
    if re.search(r"\b(record|add|log|receive)\b.{0,24}\bpayment\b"
                 r"|\bpayment\b.{0,16}\b(record|received)\b"
                 r"|\bmark\b.{0,24}\bpaid\b|\bpay\b.{0,12}\b(invoice|full)\b"
                 r"|\bsettle\b.{0,16}\binvoice\b"
                 # combined one-shot forms: "record 5000 gcash for inv-007",
                 # "received 5000 from maria"
                 r"|\b(record|received?|log)\b.{0,30}\b(gcash|cash|bank)\b"
                 r"|\b(record|received?)\b\s+[\d,]+.{0,24}\b(for|from)\b", q):
        return _answer_payment_action(q)
    if re.search(r"\b(add|record|log)\b.{0,20}\bexpense\b", q):
        return _answer_expense_action(q)
    if re.search(r"\brecalculat\w*\b.{0,30}\bloyalty\b|\bloyalty\b.{0,20}\brecalculat", q):
        return _answer_loyalty_recalc_action(q)
    if re.search(r"\bmark\b.{0,20}\bnotifications?\b.{0,16}\bread\b"
                 r"|\bclear\b.{0,16}\bnotifications?\b"
                 r"|\bnotifications?\b.{0,16}\bread\b", q):
        return _answer_notifications_mark_read_action(q)
    if re.search(r"\bexport\b.{0,24}\breport\b|\breport\b.{0,16}\bexport\b"
                 r"|\bdownload\b.{0,16}\breport\b", q):
        return _answer_export_report_action(q)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Intent routing
# ─────────────────────────────────────────────────────────────────────────────

# Primary router: (handler, regex). First match wins — ordered specific → general.
_INTENTS = [
    (_answer_compare,           r"\bcompare\b|\bvs\b|\bversus\b|\bgrowth\b|\bgrowing\b|\bshrink|\bdifference\b"),
    (_answer_weekly,            r"(?<!this )(?<!last )\bweek\b|\bweekly\b|\bper week\b"),
    (_answer_best_month,        r"(best|highest|top|strongest|peak|lowest|worst|weakest|slowest).{0,20}\bmonth\b|\bmonth\b.{0,24}(most|highest|best|least|lowest)"),
    (_answer_trend,             r"\b(monthly|trend|per month|show|graph|chart)\b.{0,24}\b(revenue|expense|profit|sales)\b|\b(revenue|expense|profit)\b.{0,16}\b(monthly|trend|per month)\b"),
    (_answer_expense_breakdown, r"\bexpense\b.{0,24}(breakdown|category|categories|where|go)|\bbreakdown\b|where.{0,20}(expense|money)"),
    (_answer_top_customers,     r"(top|best|frequent|loyal).{0,16}customer|customer.{0,16}(top|most)|\bwho\b.{0,24}customer"),
    (_answer_unpaid,            r"\bunpaid\b|\boutstanding\b|\bbalance\b|\bcollect\b|\bowe\b|\bdebt\b|\breceivable"),
    (_answer_list_bookings,     r"\b(list|show|view|display|all)\b.{0,20}\b(booking|bookings|order|orders)\b"
                                r"|\bbookings?\b.{0,12}\bdetails\b|^\s*(bookings?|orders?)\s*$"
                                r"|\b(booking|bookings|order|orders)\b.{0,20}\b(" + _RANGE_WORD_ALT + r")\b"
                                r"|\b(" + _RANGE_WORD_ALT + r")\b.{0,20}\b(booking|bookings|order|orders)\b"),
    (_answer_list_customers,    r"\b(list|show|view|display|all)\b.{0,20}\bcustomers?\b"
                                r"|\bcustomers?\b.{0,12}\blist\b|^\s*customers?\s*$"),
    (_answer_list_invoices,     r"\b(list|show|view|display|all)\b.{0,20}\binvoices?\b"
                                r"|\binvoices?\b.{0,12}\blist\b|^\s*invoices?\s*$"
                                r"|\binvoices?\b.{0,20}\b(" + _RANGE_WORD_ALT + r")\b"
                                r"|\b(" + _RANGE_WORD_ALT + r")\b.{0,20}\binvoices?\b"
                                r"|\bpaid\b.{0,20}\b(invoice|invoices|event|events)\b"),
    (_answer_list_expenses,     r"\b(list|show|view|display|all)\b.{0,20}\bexpenses?\b"
                                r"|\bexpenses?\b.{0,12}\blist\b|^\s*expenses?\s*$"
                                r"|\bexpenses?\b.{0,20}\b(" + _RANGE_WORD_ALT + r")\b"
                                r"|\b(" + _RANGE_WORD_ALT + r")\b.{0,20}\bexpenses?\b"),
    (_answer_business_suggestions, r"\b(suggest|suggestion|suggestions|recommend|recommendation|recommendations|advise|advice|improve|improvement|improvements|grow|optimize|optimization)\b|\bhow.{0,20}\b(improve|grow|increase|optimize)\b"),
    (_answer_daily_briefing,    r"\bbriefing\b|\bbrief me\b|\bmorning summary\b|\bdaily summary\b|\bcatch me up\b|\bwhat's on today\b"),
    (_answer_follow_ups,        r"\bfollow[\s-]?ups?\b"),
    (_answer_notifications,     r"\bnotifications?\b|\bunread\b|\banything new\b"),
    (_answer_pending,           r"\bpending\b|\bwaiting\b|\bfor review\b|\bto approve\b"),
    (_answer_today,             r"\btoday\b|\btodays\b|\bright now\b|\bsummary of the day\b"),
    (_answer_upcoming,          r"\bupcoming\b|\bnext event|\bschedule\b|\bevents\b|\bcalendar\b"),
    (_answer_biggest_booking,   r"(biggest|largest|big).{0,16}(booking|event|order)"),
    (_answer_average,           r"\baverage\b|\bavg\b|\btypical\b|\busual\b|\bmean\b"),
    (_answer_bookings_count,    r"how many.{0,16}(booking|event|order)|\bbooking(s)?\b.{0,12}(count|total|number)|number of booking"),
    (_answer_top_menu,          r"(top|best|seller|popular).{0,16}(menu|dish|item|food)|\bmenu\b.{0,16}(top|best|popular)|bestsell"),
    (_answer_top_locations,     r"\blocation|\bwhere.{0,16}(event|booking)|\bvenue|\bcity|\bbarangay"),
    (_answer_occasions,         r"\boccasion|\bwedding|\bbirthday|\banniversary|\bdebut|\bcorporate"),
    (_answer_payment_methods,   r"\bpayment method|\bgcash\b|\bcash\b|\bbank\b|\bhow.{0,12}pay\b"),
    (_answer_packages,          r"\bpackage"),
    (_answer_counts,            r"how many.{0,16}(customer|menu|item|package)|\bcount\b|\brecords\b|\bdatabase\b|\bsystem\b.{0,12}(hold|have|contain)"),
    (_answer_business_info,     r"\bbusiness\b|\bcontact\b|\baddress\b|\bdownpayment\b|\bpolicy\b|\bdeposit\b|\bcompany\b"),
    (_answer_howto,             r"\bhow to\b|\bhow do\b|\bhow can\b|\bwhere\b|\bwhere do\b"),
    (_answer_total,             r"\bhow much\b|\btotal\b|\brevenue\b|\bexpense\b|\bprofit\b|\bincome\b|\bsales\b|\bearn"),
]

# Fuzzy fallback: keyword → handler scoring for loosely phrased questions
_KEYWORD_HANDLERS = {
    _answer_compare:           {"compare", "vs", "versus", "difference", "growth", "better", "worse"},
    _answer_weekly:            {"week", "weekly"},
    _answer_trend:             {"trend", "monthly", "graph", "chart", "show"},
    _answer_expense_breakdown: {"breakdown", "categories", "category", "expense", "expenses", "spending"},
    _answer_top_customers:     {"customer", "customers", "loyal", "frequent"},
    _answer_unpaid:            {"unpaid", "outstanding", "balance", "collect", "owe", "due"},
    _answer_upcoming:          {"upcoming", "events", "schedule", "calendar", "next"},
    _answer_top_menu:          {"menu", "dish", "food", "bestseller", "seller"},
    _answer_packages:          {"package", "packages", "pax"},
    _answer_average:           {"average", "avg", "typical"},
    _answer_bookings_count:    {"bookings", "booking", "orders", "reservations"},
    _answer_payment_methods:   {"payment", "gcash", "cash", "bank"},
    _answer_business_info:     {"business", "contact", "address", "downpayment", "policy"},
    _answer_total:             {"revenue", "profit", "income", "sales", "total", "much"},
    _answer_follow_ups:        {"followup", "followups", "overdue"},
    _answer_notifications:     {"notification", "notifications", "unread", "alerts"},
    _answer_daily_briefing:    {"briefing", "brief"},
}


_CONVERSATION_HISTORY: list[dict] = []


def get_conversation_history() -> list[dict]:
    return list(_CONVERSATION_HISTORY)


def clear_conversation_history():
    global _CONVERSATION_HISTORY
    _CONVERSATION_HISTORY = []


def _answer_chitchat_and_followup(q: str, raw: str) -> dict:
    """Handles Tagalog/Bisaya/English casual reactions (edi wow, haha, astig, salamat, ok, cool),
    contextual follow-up questions ('why?', 'tell me more'), and keeps conversation flowing."""
    q_lower = raw.lower().strip()

    last_assistant_msg = ""
    for entry in reversed(_CONVERSATION_HISTORY[:-1] if len(_CONVERSATION_HISTORY) > 1 else _CONVERSATION_HISTORY):
        if entry.get("role") == "assistant":
            last_assistant_msg = entry.get("text", "")
            break

    # Tagalog/Bisaya/English casual reactions (edi wow, naks, astig, lodi, petmalu, grabe, haha, ganyan pala, sana all)
    if re.search(r"\b(edi\s*wow|naks|astig|lodi|petmalu|grabe|ganyan\s*pala|sana\s*all|wehh?|talaga|h+a+h+a+|h+e+h+e+|l+o+l+|l+m+a+o+)\b", q_lower):
        if "shadow monarch" in last_assistant_msg.lower() or "jay" in last_assistant_msg.lower():
            ans = (
                "HAHAHA you know it! I take pride in serving the Shadow Monarch! 👨‍🍳🔥 "
                "So, what's our next move? Want me to check bookings, revenue trends, or upcoming events?"
            )
        else:
            ans = (
                "Haha! 😂 Glad you're enjoying the chat! "
                "I'm right here whenever you want to check system analytics, customers, or bookings."
            )
        return _plain(ans, [
            {"label": "Show Business Suggestions", "send": "suggest improvements"},
            {"label": "Today's Briefing", "send": "briefing"}
        ])

    # Gratitude
    if re.search(r"\b(salamat|thank\s*you|thanks|thx|arigato|daghang\s*salamat)\b", q_lower):
        ans = (
            "You're very welcome! Always happy to assist your catering operations! 👨‍🍳🍽️ "
            "Let me know whenever you need more data or reports."
        )
        return _plain(ans)

    # Agreement / Acknowledgement
    if re.search(r"\b(ok|okay|cool|nice|got\s*it|noted|alright|great|awesome)\b", q_lower):
        ans = (
            "Awesome! Let me know if you want to dig into sales, top menu items, or unpaid balances! 📊"
        )
        return _plain(ans)

    # Follow-ups ("why?", "tell me more", "explain further", "what else?")
    if re.search(r"\b(why\??|tell\s*me\s*more|explain|what\s*else\??|more\s*details\??)\b", q_lower):
        if last_assistant_msg:
            ans = (
                f"Following up on our conversation: \"{last_assistant_msg[:120]}...\"\n\n"
                f"I continuously monitor your live database. You can ask me specific questions like "
                f"\"top customers\", \"monthly revenue\", or \"unpaid invoices\" to get deeper breakdowns!"
            )
        else:
            ans = "I'm keeping track of our chat history! Ask me anything specific about your bookings, expenses, or sales!"
        return _plain(ans)

    if last_assistant_msg:
        ans = (
            f"Got it! Just to make sure I pull the right data from your system for you — "
            f"are you asking about bookings, sales, expenses, or customers? "
            f"Or click one of the suggestions below!"
        )
        return _plain(ans, [
            {"label": "Show Business Suggestions", "send": "suggest improvements"},
            {"label": "Daily Briefing", "send": "briefing"},
            {"label": "Show Help Menu", "send": "help"}
        ])

    return _answer_help()


def ask(question: str) -> dict:
    """Answer a business question from live data. Fully offline, with conversation history."""
    global _LAST_ACTION
    if not (question or "").strip():
        return _answer_help()
    raw = question.strip()
    q = _normalize(question)

    _CONVERSATION_HISTORY.append({"role": "user", "text": raw})
    if len(_CONVERSATION_HISTORY) > 60:
        _CONVERSATION_HISTORY.pop(0)

    res = _ask_internal(q, raw)
    if res and isinstance(res, dict) and "answer" in res:
        _CONVERSATION_HISTORY.append({"role": "assistant", "text": res.get("answer", "")})
        if len(_CONVERSATION_HISTORY) > 60:
            _CONVERSATION_HISTORY.pop(0)
    return res


def _ask_internal(q: str, raw: str) -> dict:
    global _LAST_ACTION
    try:
        # 0a. Follow-up to a "which one?" question
        pending_result = _resolve_pending(q, raw)
        if pending_result is not None:
            return pending_result

        # 0a2. Typed yes/no about the last proposed action
        if _LAST_ACTION:
            if re.search(_YES_WORDS, q.strip()):
                action = dict(_LAST_ACTION)
                return {"ok": True, "chart": None, "action": action, "error": "",
                        "answer": f"To execute — {action.get('label')} — press Confirm below."}
            if re.search(_EXIT_WORDS, q.strip()):
                _LAST_ACTION = {}
                return _plain("Okay, I've withdrawn that action — nothing was changed.")

        # Casual chitchat / banter / reactions (edi wow, haha, astig, salamat, ok, cool)
        if re.search(r"\b(edi\s*wow|naks|astig|lodi|petmalu|grabe|ganyan\s*pala|sana\s*all|wehh?|talaga|h+a+h+a+|h+e+h+e+|l+o+l+|l+m+a+o+)\b"
                     r"|\b(salamat|thank\s*you|thanks|thx|arigato|daghang\s*salamat)\b"
                     r"|\b(ok|okay|cool|nice|got\s*it|noted|alright|great|awesome)\b"
                     r"|\b(why\??|tell\s*me\s*more|explain|what\s*else\??)\b", raw.lower()):
            return _answer_chitchat_and_followup(q, raw)

        # Greeting / Mood / Health check questions
        if re.search(r"\b(good\s*(morning|afternoon|evening)|maayong\s*(buntag|hapon|gabi))\b"
                     r"|\bhow\s*are\s*you\b|\bfeeling\b|\bmood\b|\btired\b|\bhow\s*do\s*you\s*feel\b"
                     r"|\bhow\s*are\s*you\s*doing\b|\bkamusta\b|\bkumusta\b|\bmusta\b"
                     r"|^\s*(hi|hello|hey|hi\s*chef|hello\s*chef)\s*$", q):
            return _answer_greeting_and_mood(q)

        # About Jay — identity, creator, privacy, and capability questions
        for entry in _ABOUT_AI_INTENTS:
            if re.search(entry["pattern"], q):
                return _answer_about_ai(entry["key"], entry["answers"])

        # Help
        if re.search(r"\bhelp\b|\bwhat can you\b", q):
            return _answer_help()

        # 0b. "add/create new customer|booking|expense…"
        create_result = _detect_create(q, raw)
        if create_result is not None:
            return create_result

        # 0c. Action requests
        action_result = _detect_action(q)
        if action_result is not None:
            return action_result

        # 1. Specific date mentioned
        md = _extract_day(q)
        if md and re.search(r"\bevent|\bbooking|\bschedule|\bwhat\b|\bwho\b|\bunsa\b", q):
            return _answer_events_on(q, md[0], md[1])

        # 2. Expense category mentioned
        category = _find_category(q)
        if category:
            return _answer_category_expense(q, category)

        # 2b. Ledger / balance history / communication history
        if re.search(r"\bledger\b|\bbalance history\b", q):
            customer = _find_customer(q)
            return _answer_ledger(q, customer) if customer else _plain("Whose ledger do you want to see? Include their name, e.g. \"Maria's ledger\".")
        if re.search(r"\blast contact\b|\blast contacted\b|\bwhen.{0,16}contact", q):
            customer = _find_customer(q)
            return _answer_last_contact(q, customer) if customer else _plain("Last contact with whom? Include their name, e.g. \"last contact with Maria\".")
        if re.search(r"\bcommunication\b.{0,16}(history|log)|\bcontact history\b", q):
            customer = _find_customer(q)
            return _answer_communication_history(q, customer) if customer else _plain("Communication history for whom? Include their name, e.g. \"communication history for Maria\".")

        # 3. Customer name mentioned
        customer = _find_customer(q)
        if customer:
            return _answer_customer(q, customer)

        # 4. Two months or two years
        if len(_extract_months(q)) >= 2 or len(_extract_years(q)) >= 2:
            return _answer_compare(q)

        # 5. Ordered intent patterns
        for handler, pattern in _INTENTS:
            if re.search(pattern, q):
                return handler(q)

        # 6. Fuzzy keyword scoring as a last resort
        tokens = set(q.split())
        best_handler, best_score = None, 0
        for handler, keywords in _KEYWORD_HANDLERS.items():
            score = len(tokens & keywords)
            if score > best_score:
                best_handler, best_score = handler, score
        if best_handler and best_score:
            return best_handler(q)
    except Exception as e:
        return {"ok": False, "answer": "", "chart": None, "error": f"I hit a problem reading the data: {e}"}

    return _answer_chitchat_and_followup(q, raw)
