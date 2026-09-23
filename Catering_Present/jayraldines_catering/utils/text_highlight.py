"""
utils/text_highlight.py
-----------------------
Small dependency-free helper to highlight a search term inside a piece of text
for display in a Qt rich-text QLabel. HTML-escapes the text first, then wraps
each case-insensitive match of the query in a subtle colored span.
"""

import html


def highlight_html(text, query, color: str = "#FACC15") -> str:
    """Return `text` as HTML with every case-insensitive occurrence of `query`
    wrapped in a highlighted span. If `query` is empty or not found, returns the
    plain HTML-escaped text (safe to drop into a RichText QLabel either way)."""
    raw = "" if text is None else str(text)
    escaped = html.escape(raw)

    q = (query or "").strip()
    if not q:
        return escaped

    # Match on the ESCAPED text using the ESCAPED query so entity boundaries
    # (e.g. & -> &amp;) never get split mid-entity.
    needle = html.escape(q)
    if not needle:
        return escaped

    hay_lower = escaped.lower()
    needle_lower = needle.lower()

    out = []
    i = 0
    n = len(needle_lower)
    span_open = (
        f'<span style="background:{color}33;color:{color};'
        f'border-radius:3px;padding:0 1px;">'
    )
    while True:
        j = hay_lower.find(needle_lower, i)
        if j == -1:
            out.append(escaped[i:])
            break
        out.append(escaped[i:j])
        out.append(span_open)
        out.append(escaped[j:j + n])
        out.append("</span>")
        i = j + n
    return "".join(out)
