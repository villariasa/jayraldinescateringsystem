"""
Session-Only Alarm & Reminder Manager for Chef Jay AI.

Features:
- Purely in-memory: no database storage, no persistence across restarts.
- 100% thread-safe: timer checking runs on the Qt main GUI thread.
- Natural-language parsing:
    * Relative durations: "alarm 1 minute", "set an alarm 1 minute", "in 15 minutes", "in 2 hours", "ping me in 90 seconds"
    * Same-day absolute times: "at 3pm", "at 7:30 tonight", "at noon", "at 18:00"
    * Dated / future times: "tomorrow at 9am", "next Monday at noon", "on August 20 at 8am", "for 12/25 at 8am"
    * Attached messages: "remind me in 20 minutes to check the oven" -> message: "check the oven"
    * Ambiguity handling: detects past same-day times (e.g. 3pm when it's already 4pm) and prompts for confirmation.
- Concurrency: multiple simultaneous alarms & reminders active at once.
- Management: list active alarms, cancel by time/ID/all, snooze fired alarms.
- Native delivery: triggers system sound, app toasts, floating mascot alerts, and chat messages.
"""

import re
import threading
import calendar
from datetime import datetime, date, time as dt_time, timedelta
from typing import Optional, Tuple, List, Dict, Any

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

_MONTH_NAMES = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "mayo": 5, "jun": 6, "june": 6,
    "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
    "enero": 1, "pebrero": 2, "marso": 3, "abril": 4, "hunyo": 6,
    "hulyo": 7, "agosto": 8, "setyembre": 9, "oktubre": 10, "nobyembre": 11, "disyembre": 12
}

_WEEKDAYS = {
    "monday": 0, "mon": 0, "lunes": 0,
    "tuesday": 1, "tue": 1, "tues": 1, "martes": 1,
    "wednesday": 2, "wed": 2, "miyerkules": 2, "miercoles": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3, "huwebes": 3, "jueves": 3,
    "friday": 4, "fri": 4, "biyernes": 4, "viernes": 4,
    "saturday": 5, "sat": 5, "sabado": 5,
    "sunday": 6, "sun": 6, "domingo": 6
}


def _strip_fillers(text: str) -> str:
    """Cleans up leading filler words in attached messages."""
    msg = text.strip()
    for _ in range(3):
        msg = msg.strip(" :-.,\"'")
        msg = re.sub(r"^(to|that|about|for|please|na|nga|in|at)\s+", "", msg, flags=re.IGNORECASE).strip()
    return msg


class ReminderManager(QObject):
    """Singleton session-only reminder & alarm coordinator."""
    alarm_fired = Signal(dict)
    alarm_created = Signal(dict)
    alarm_cancelled = Signal(dict)
    all_cancelled = Signal(int)

    def __init__(self):
        super().__init__()
        self._reminders: Dict[int, Dict[str, Any]] = {}
        self._next_id: int = 1
        self._last_fired: Optional[Dict[str, Any]] = None
        self._pending_clarification: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

        # Master tick timer running strictly on the main thread
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._check_alarms)
        self._tick_timer.start(500)

    def _check_alarms(self):
        """Called every 500ms on the main Qt thread to check and trigger due alarms."""
        now = datetime.now()
        due_list = []
        with self._lock:
            for r in self._reminders.values():
                if r.get("is_active") and now >= r.get("target_dt", now):
                    r["is_active"] = False
                    due_list.append(dict(r))

        for entry in due_list:
            self._last_fired = dict(entry)
            # 1. Audio chime / beep
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                try:
                    QApplication.beep()
                except Exception:
                    pass

            # 2. Push app notification signal
            try:
                from utils.signals import app_events
                app_events().notification_push.emit()
            except Exception:
                pass

            # 3. Emit alarm_fired signal
            self.alarm_fired.emit(entry)

    def get_active(self) -> List[Dict[str, Any]]:
        """Returns active alarms sorted by scheduled target time."""
        with self._lock:
            active = [dict(r) for r in self._reminders.values() if r.get("is_active")]
        return sorted(active, key=lambda x: x["target_dt"])

    def get_last_fired(self) -> Optional[Dict[str, Any]]:
        return self._last_fired

    def set_pending_clarification(self, info: Optional[Dict[str, Any]]):
        self._pending_clarification = info

    def get_pending_clarification(self) -> Optional[Dict[str, Any]]:
        return self._pending_clarification

    def add_reminder(self, target_dt: datetime, message: str = "",
                     kind: str = "alarm", raw_text: str = "") -> Dict[str, Any]:
        """Schedules a new in-memory alarm (thread-safe)."""
        now = datetime.now()
        with self._lock:
            rem_id = self._next_id
            self._next_id += 1

            label = message.strip() if message.strip() else ("Alarm" if kind == "alarm" else "Reminder")

            entry = {
                "id": rem_id,
                "target_dt": target_dt,
                "message": label,
                "kind": kind,
                "raw_text": raw_text,
                "created_at": now,
                "is_active": True
            }
            self._reminders[rem_id] = entry

        # Immediately trigger check if scheduled time is already due
        if target_dt <= now:
            QTimer.singleShot(0, self._check_alarms)

        self.alarm_created.emit(entry)
        return entry

    def cancel_reminder(self, identifier: Any) -> Tuple[bool, str]:
        """Cancels a reminder by ID, time string, or keywords in message."""
        active = self.get_active()
        if not active:
            return False, "You don't have any active alarms to cancel."

        # Case 1: Integer ID
        if isinstance(identifier, int):
            with self._lock:
                target = self._reminders.get(identifier)
                if target and target.get("is_active"):
                    target["is_active"] = False
                    self.alarm_cancelled.emit(target)
                    time_str = target["target_dt"].strftime("%I:%M %p").lstrip("0")
                    return True, f"Cancelled alarm #{target['id']} ({time_str} — {target['message']})."
            return False, f"Alarm #{identifier} was not found or has already expired."

        # Case 2: String query (e.g. "3pm", "oven", "1")
        q = str(identifier).strip().lower()
        if q.isdigit():
            return self.cancel_reminder(int(q))

        # Check by message or time match
        with self._lock:
            for r in self._reminders.values():
                if not r.get("is_active"):
                    continue
                t_str = r["target_dt"].strftime("%I:%M %p").lower()
                t_str_compact = t_str.replace(" ", "").replace(":00", "")
                msg = r["message"].lower()
                if q in msg or q in t_str or q in t_str_compact:
                    r["is_active"] = False
                    self.alarm_cancelled.emit(r)
                    time_disp = r["target_dt"].strftime("%I:%M %p").lstrip("0")
                    return True, f"Cancelled alarm #{r['id']} ({time_disp} — {r['message']})."

        return False, f"I couldn't find an active alarm matching \"{identifier}\"."

    def cancel_all(self) -> int:
        """Cancels all active alarms."""
        count = 0
        with self._lock:
            for r in self._reminders.values():
                if r.get("is_active"):
                    r["is_active"] = False
                    count += 1
        self.all_cancelled.emit(count)
        return count

    def snooze_last(self, minutes: int = 5) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Snoozes the last fired alarm for N minutes."""
        if not self._last_fired:
            active = self.get_active()
            if active:
                base = active[0]
            else:
                return False, None
        else:
            base = self._last_fired

        new_dt = datetime.now() + timedelta(minutes=minutes)
        msg = f"[Snoozed] {base['message']}".replace("[Snoozed] [Snoozed]", "[Snoozed]")
        entry = self.add_reminder(new_dt, message=msg, kind=base.get("kind", "alarm"),
                                  raw_text=f"Snoozed {minutes}m")
        return True, entry


_MANAGER: Optional[ReminderManager] = None


def reminder_manager() -> ReminderManager:
    """Global singleton access for ReminderManager."""
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ReminderManager()
    return _MANAGER


# ─────────────────────────────────────────────────────────────────────────────
# Natural Language Parser for Times and Messages
# ─────────────────────────────────────────────────────────────────────────────

def parse_alarm_request(text: str, now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Parses natural-language alarm / reminder queries into actionable structures.

    Returns dict with keys:
        - "ok": bool
        - "target_dt": datetime or None
        - "message": str
        - "kind": "alarm" or "reminder"
        - "status": "ready" | "ambiguous_past" | "needs_time" | "unparseable" | "list" | "cancel" | "cancel_all" | "snooze"
        - "clarification": str
        - "options": list of suggested prompt chips
        - "meta": dict
    """
    if now is None:
        now = datetime.now()

    raw = text.strip()
    q = raw.lower()

    # 1. Check for Snooze intent
    snooze_m = re.search(r"\b(?:snooze|pahulay)\b(?:\s+(?:for\s+)?(\d+)\s*(?:m|min|mins|minutes|minutos)?)?", q)
    if snooze_m and (q.startswith("snooze") or q.startswith("pahulay") or "snooze" in q):
        mins = int(snooze_m.group(1)) if snooze_m.group(1) else 5
        return {
            "ok": True,
            "status": "snooze",
            "minutes": mins,
            "message": "",
            "kind": "alarm",
            "target_dt": None
        }

    # 2. Check for List / Show Alarms intent
    if re.search(r"\b(?:what|list|show|view|check|get|display|unsa)\b.{0,25}\b(?:alarms?|reminders?|timers?|pahinumdom)\b"
                 r"|^\s*(?:alarms?|reminders?|timers?|active alarms?)\s*$", q):
        return {
            "ok": True,
            "status": "list",
            "message": "",
            "kind": "alarm",
            "target_dt": None
        }

    # 3. Check for Cancel All intent
    if re.search(r"\b(?:cancel|clear|delete|remove|stop|undanga?)\s+(?:all|everything|every|tanan)\b.{0,20}\b(?:alarms?|reminders?|timers?)\b"
                 r"|^\s*(?:cancel\s+all|clear\s+alarms?|stop\s+all)\s*$", q):
        return {
            "ok": True,
            "status": "cancel_all",
            "message": "",
            "kind": "alarm",
            "target_dt": None
        }

    # 4. Check for Cancel Specific intent
    cancel_m = re.search(r"\b(?:cancel|delete|remove|stop|i-cancel)\b(?:\s+(?:my|the|alarm|reminder|timer|number|#))*\s+([a-zA-Z0-9\s:._\-]+)", q)
    if cancel_m and any(w in q for w in ["cancel", "delete", "remove", "stop", "i-cancel"]):
        if not re.search(r"\b(?:remind\s+me|set\s+alarm)\b", q):
            target_str = cancel_m.group(1).strip()
            target_str = re.sub(r"\b(?:alarm|reminder|timer)\b", "", target_str).strip()
            return {
                "ok": True,
                "status": "cancel",
                "target": target_str,
                "message": "",
                "kind": "alarm",
                "target_dt": None
            }

    # Determine kind
    kind = "reminder" if "remind" in q or "pahinumdom" in q or "ping" in q else "alarm"

    # ── CASE A: Relative Durations ("alarm 1 minute", "set an alarm 1 minute", "in 15 minutes", "in 2 hours and 30 mins", "for 10 mins") ──
    rel_match = re.search(
        r"\b(?:in|human\s+sa|after|for)?\s*(?:an?\s+hour|half\s+an?\s+hour|(?:\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|minutes?|mins?|m|seconds?|secs?|s|ka\s+minutos?|ka\s+oras)(?:\s*(?:and|,)?\s*\d+\s*(?:minutes?|mins?|m|seconds?|secs?|s))?))\b",
        q
    )

    if rel_match:
        time_span_str = rel_match.group(0)
        delta = _parse_relative_duration(time_span_str)
        if delta and delta.total_seconds() > 0:
            target_dt = now + delta
            msg = _extract_message_from_relative(raw, time_span_str)
            return {
                "ok": True,
                "status": "ready",
                "target_dt": target_dt,
                "message": msg,
                "kind": kind,
                "time_display": _format_target_time(target_dt, now)
            }

    # ── CASE B: Dated Times ("tomorrow at 9am", "on Aug 20 at 3pm", "next Monday at noon", "for 12/25 at 8am") ──
    dated_res = _parse_dated_time(q, raw, now)
    if dated_res:
        dated_res["kind"] = kind
        return dated_res

    # ── CASE C: Same-Day Absolute Times ("at 3pm", "at 7:30 tonight", "at noon", "at 18:00") ──
    abs_res = _parse_sameday_time(q, raw, now)
    if abs_res:
        abs_res["kind"] = kind
        return abs_res

    # ── CASE D: User said "remind me" or "set alarm" but time was unparseable / missing ──
    if re.search(r"\b(?:remind\s+me|set\s+(?:an?\s+)?alarm|alarm\s+me|pahinumdomi\s+ko|ping\s+me)\b", q):
        msg = _clean_bare_reminder_message(raw)
        return {
            "ok": False,
            "status": "needs_time",
            "message": msg,
            "kind": kind,
            "target_dt": None,
            "clarification": f"When would you like me to set the {kind}? For example:\n"
                             f"• \"in 15 minutes to {msg or 'check the kitchen'}\"\n"
                             f"• \"at 3:30 PM today\"\n"
                             f"• \"tomorrow at 9:00 AM\"",
            "options": [
                {"label": "In 15 minutes", "send": f"remind me in 15 minutes to {msg}" if msg else "remind me in 15 minutes"},
                {"label": "In 30 minutes", "send": f"remind me in 30 minutes to {msg}" if msg else "remind me in 30 minutes"},
                {"label": "In 1 hour", "send": f"remind me in 1 hour to {msg}" if msg else "remind me in 1 hour"},
                {"label": "Tomorrow 9:00 AM", "send": f"remind me tomorrow at 9am to {msg}" if msg else "remind me tomorrow at 9am"}
            ]
        }

    return {
        "ok": False,
        "status": "unparseable",
        "message": "",
        "kind": kind,
        "target_dt": None
    }


def _parse_relative_duration(text: str) -> Optional[timedelta]:
    """Calculates timedelta from strings like '1 minute', 'in 1 hour and 30 mins', 'in 45 seconds'."""
    t = text.lower()
    if "half an hour" in t or "half hour" in t:
        return timedelta(minutes=30)
    if "an hour" in t:
        return timedelta(hours=1)
    if "a minute" in t:
        return timedelta(minutes=1)

    hours = 0.0
    minutes = 0.0
    seconds = 0.0

    hr_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h|ka\s+oras)", t)
    if hr_m:
        hours = float(hr_m.group(1))

    min_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m|ka\s+minutos?)", t)
    if min_m:
        minutes = float(min_m.group(1))

    sec_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)", t)
    if sec_m:
        seconds = float(sec_m.group(1))

    total = timedelta(hours=hours, minutes=minutes, seconds=seconds)
    return total if total.total_seconds() > 0 else None


def _extract_message_from_relative(raw: str, time_span_str: str) -> str:
    """Extracts custom user message, e.g. 'check the oven'."""
    s = raw
    s = re.sub(re.escape(time_span_str), "", s, flags=re.IGNORECASE)
    s = re.sub(r"\b(?:remind\s+me|set\s+(?:an?\s+)?alarm|alarm\s+me|pahinumdomi\s+ko|ping\s+me|alarms?|reminders?|timers?)\b", "", s, flags=re.IGNORECASE)
    s = _strip_fillers(s)
    return s if s else "Alarm / Reminder"


def _parse_sameday_time(q: str, raw: str, now: datetime) -> Optional[Dict[str, Any]]:
    """Parses same-day times like 'at 3pm', 'at 7:30 tonight', 'at noon', 'at 18:45'."""
    hour = None
    minute = 0
    is_pm = None

    time_match = re.search(
        r"\b(?:at|sa|alas|for)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|in the morning|tonight|this evening|this afternoon)?\b"
        r"|\b(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)?\b"
        r"|\b(?:at|sa|for)\s+(noon|midnight)\b",
        q
    )

    if not time_match:
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)\b", q)

    if not time_match:
        return None

    full_match_text = time_match.group(0)

    if "noon" in full_match_text:
        hour, minute = 12, 0
    elif "midnight" in full_match_text:
        hour, minute = 0, 0
    else:
        g = [x for x in time_match.groups() if x is not None]
        h_str = g[0]
        hour = int(h_str)
        minute = 0
        ampm = ""

        for part in g[1:]:
            if part.isdigit() and len(part) == 2:
                minute = int(part)
            elif any(x in part.lower() for x in ["am", "pm", "tonight", "evening", "afternoon", "morning"]):
                ampm = part.lower()

        if "tonight" in q or "evening" in q or "afternoon" in q or "gabi" in q or "hapon" in q:
            if hour < 12:
                hour += 12
        elif "am" in ampm or "morning" in ampm or "buntag" in q:
            if hour == 12:
                hour = 0
        elif "pm" in ampm:
            if hour < 12:
                hour += 12
        elif hour < 7:
            hour += 12

    if hour is None or not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    scheduled_time = dt_time(hour, minute, 0)
    target_dt = datetime.combine(now.date(), scheduled_time)

    # Extract attached message
    msg = raw
    msg = re.sub(re.escape(full_match_text), "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"\b(?:remind\s+me|set\s+(?:an?\s+)?alarm|alarm\s+me|pahinumdomi\s+ko|ping\s+me|alarms?|reminders?|timers?|tonight|this\s+evening|this\s+afternoon|today)\b", "", msg, flags=re.IGNORECASE)
    msg = _strip_fillers(msg) or "Alarm / Reminder"

    # Ambiguity check: If the time has ALREADY PASSED today
    if target_dt <= now:
        suggested_dt = target_dt + timedelta(days=1)
        time_fmt = target_dt.strftime("%I:%M %p").lstrip("0")
        current_fmt = now.strftime("%I:%M %p").lstrip("0")
        return {
            "ok": False,
            "status": "ambiguous_past",
            "target_dt": target_dt,
            "suggested_dt": suggested_dt,
            "message": msg,
            "time_display": time_fmt,
            "clarification": f"{time_fmt} has already passed today (current time: {current_fmt}). "
                             f"Did you mean {time_fmt} tomorrow?",
            "options": [
                {"label": f"Yes, set for {time_fmt} tomorrow", "send": f"set alarm tomorrow at {time_fmt} to {msg}" if msg != "Alarm / Reminder" else f"set alarm tomorrow at {time_fmt}"},
                {"label": "Cancel", "send": "never mind"}
            ]
        }

    return {
        "ok": True,
        "status": "ready",
        "target_dt": target_dt,
        "message": msg,
        "time_display": _format_target_time(target_dt, now)
    }


def _parse_dated_time(q: str, raw: str, now: datetime) -> Optional[Dict[str, Any]]:
    """Parses future/dated inputs like 'tomorrow at 9am', 'on Aug 20 at 8am', 'next Monday at noon'."""
    target_date = None
    matched_phrases = []

    # Check "tomorrow" / "ugma"
    if "tomorrow" in q or "ugma" in q:
        target_date = now.date() + timedelta(days=1)
        matched_phrases.append("tomorrow")
        matched_phrases.append("ugma")

    # Check "next <weekday>" or "on <weekday>"
    if target_date is None:
        for w_name, w_idx in _WEEKDAYS.items():
            if re.search(rf"\b(?:next|this|on|sa)\s+{w_name}\b|\b{w_name}\b", q):
                days_ahead = (w_idx - now.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target_date = now.date() + timedelta(days=days_ahead)
                matched_phrases.append(w_name)
                break

    # Check "on August 20" or "Aug 20"
    if target_date is None:
        for m_name, m_num in _MONTH_NAMES.items():
            m_match = re.search(rf"\b(?:on|sa|for)?\s*{m_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", q)
            if m_match:
                day = int(m_match.group(1))
                year = now.year
                try:
                    cand = date(year, m_num, day)
                    if cand < now.date():
                        cand = date(year + 1, m_num, day)
                    target_date = cand
                    matched_phrases.append(m_match.group(0))
                    break
                except ValueError:
                    pass

    # Check "12/25" or "2026-08-20" or "08/20"
    if target_date is None:
        slash_m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", q)
        if slash_m:
            m_val, d_val = int(slash_m.group(1)), int(slash_m.group(2))
            y_val = int(slash_m.group(3)) if slash_m.group(3) else now.year
            if y_val < 100:
                y_val += 2000
            try:
                cand = date(y_val, m_val, d_val)
                if cand < now.date() and not slash_m.group(3):
                    cand = date(y_val + 1, m_val, d_val)
                target_date = cand
                matched_phrases.append(slash_m.group(0))
            except ValueError:
                pass

    if target_date is None:
        return None

    hour = 9
    minute = 0
    time_str_matched = ""

    time_match = re.search(
        r"\b(?:at|sa|alas)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.|in the morning|in the afternoon|in the evening|tonight|noon|midnight)?\b",
        q
    )
    explicit_time = re.search(r"\b(?:at|sa|alas)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|noon|midnight)\b|\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", q)
    if explicit_time:
        t_part = explicit_time.group(0)
        time_str_matched = t_part
        if "noon" in t_part:
            hour, minute = 12, 0
        elif "midnight" in t_part:
            hour, minute = 0, 0
        else:
            nums = re.findall(r"\d+", t_part)
            if nums:
                hour = int(nums[0])
                minute = int(nums[1]) if len(nums) > 1 else 0
                if "pm" in t_part and hour < 12:
                    hour += 12
                elif "am" in t_part and hour == 12:
                    hour = 0
                elif hour < 7 and "am" not in t_part:
                    hour += 12

    target_dt = datetime.combine(target_date, dt_time(hour, minute, 0))

    msg = raw
    for p in matched_phrases:
        msg = re.sub(re.escape(p), "", msg, flags=re.IGNORECASE)
    if time_str_matched:
        msg = re.sub(re.escape(time_str_matched), "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"\b(?:remind\s+me|set\s+(?:an?\s+)?alarm|alarm\s+me|pahinumdomi\s+ko|ping\s+me|alarms?|reminders?|timers?|next|on|at|for|tomorrow|ugma)\b", "", msg, flags=re.IGNORECASE)
    msg = _strip_fillers(msg)
    if not msg:
        msg = "Alarm / Reminder"

    return {
        "ok": True,
        "status": "ready",
        "target_dt": target_dt,
        "message": msg,
        "time_display": _format_target_time(target_dt, now)
    }


def _clean_bare_reminder_message(raw: str) -> str:
    s = re.sub(r"\b(?:remind\s+me|set\s+(?:an?\s+)?alarm|alarm\s+me|pahinumdomi\s+ko|ping\s+me|alarms?|reminders?|timers?)\b", "", raw, flags=re.IGNORECASE)
    return _strip_fillers(s)


def _format_target_time(target: datetime, now: datetime) -> str:
    """Formats scheduled time cleanly (e.g. 'Today at 3:15 PM', 'Tomorrow at 9:00 AM')."""
    delta_days = (target.date() - now.date()).days
    time_str = target.strftime("%I:%M %p").lstrip("0")
    if delta_days == 0:
        return f"Today at {time_str}"
    elif delta_days == 1:
        return f"Tomorrow at {time_str}"
    else:
        return f"{target.strftime('%a, %b %d')} at {time_str}"
