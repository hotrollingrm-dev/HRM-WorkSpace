"""Time rules. All datetimes are Asia/Bangkok (+07:00, no DST)."""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta, timezone

TZ = timezone(timedelta(hours=7))
OP_DAY_START = time(8, 0)


class TimeError(ValueError):
    pass


def parse_dt(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ)


def fmt_dt(dt: datetime) -> str:
    return dt.astimezone(TZ).replace(microsecond=0).isoformat()


def combine(d: date | str, hhmm: str) -> datetime:
    if isinstance(d, str):
        d = date.fromisoformat(d)
    h, m = hhmm.split(":")
    h, m = int(h), int(m)
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise TimeError(f"เวลาไม่ถูกต้อง: {hhmm}")
    return datetime.combine(d, time(h, m), TZ)


def build_range(d: str, start_hhmm: str, end_hhmm: str | None = None,
                duration_min: int | None = None) -> tuple[str, str, bool]:
    """Return (start_iso, end_iso, crossed_midnight).

    End earlier than or equal to start (clock time) means next calendar day.
    """
    start = combine(d, start_hhmm)
    if end_hhmm:
        end = combine(d, end_hhmm)
        crossed = end <= start
        if crossed:
            end += timedelta(days=1)
    elif duration_min:
        if duration_min <= 0:
            raise TimeError("ระยะเวลาต้องมากกว่า 0")
        end = start + timedelta(minutes=duration_min)
        crossed = end.date() != start.date()
    else:
        raise TimeError("ต้องระบุเวลาสิ้นสุดหรือระยะเวลา")
    return fmt_dt(start), fmt_dt(end), crossed


def validate_range(start_iso: str | None, end_iso: str | None) -> None:
    if (start_iso is None) != (end_iso is None):
        raise TimeError("ต้องระบุทั้งเวลาเริ่มและเวลาสิ้นสุด หรือไม่ระบุทั้งคู่ (Unscheduled)")
    if start_iso and parse_dt(end_iso) <= parse_dt(start_iso):
        raise TimeError("เวลาสิ้นสุดต้องมากกว่าเวลาเริ่ม")


def op_day_of(dt: datetime) -> date:
    """Operational day: [D 08:00, D+1 08:00)."""
    dt = dt.astimezone(TZ)
    return (dt - timedelta(hours=8)).date()


def op_day_window(d: date) -> tuple[datetime, datetime]:
    start = datetime.combine(d, OP_DAY_START, TZ)
    return start, start + timedelta(days=1)


def entry_op_day(entry_date: str, start_iso: str | None) -> date:
    if start_iso:
        return op_day_of(parse_dt(start_iso))
    return date.fromisoformat(entry_date)


def month_days(year: int, month: int) -> list[date]:
    n = calendar.monthrange(year, month)[1]
    return [date(year, month, i) for i in range(1, n + 1)]


def find_overlaps(entries: list[dict]) -> list[tuple[str, str]]:
    """Pairs of uids whose timed ranges overlap (warning only, never blocking)."""
    timed = sorted((e for e in entries if e.get("start_at")), key=lambda e: e["start_at"])
    out = []
    for i, a in enumerate(timed):
        a_end = parse_dt(a["end_at"])
        for b in timed[i + 1:]:
            if parse_dt(b["start_at"]) >= a_end:
                break
            out.append((a["uid"], b["uid"]))
    return out


DEFAULT_PLANNING_BANDS = {
    "_note": "Planning UI bands (user specified). Color only — no OT label. See OPEN_QUESTIONS Q-SH1.",
    "day": {"start": "08:00", "end": "20:00",
            "segments": [{"start": "08:00", "end": "17:00", "tone": "day-core"},
                         {"start": "17:00", "end": "20:00", "tone": "day-late"}]},
    "night": {"start": "20:00", "end": "08:00",
              "segments": [{"start": "20:00", "end": "05:00", "tone": "night-core"},
                           {"start": "05:00", "end": "08:00", "tone": "night-late"}]},
}

OFFICIAL_ROSTER_TIMES = {
    "_note": "ผู้ใช้ยืนยัน 15 ต.ค. 2026: ใช้เวลากะตาม PDF เป็นเวลากะทางการ (Q-SH1). "
             "แถบสีวางแผน 08–20 / 20–08 ยังใช้แสดงผลเท่านั้น",
    "source_ref": "ตารางกะ 3 Group.pdf — legend bottom-right",
    "D": {"start": "08:00", "end": "20:15"},
    "N": {"start": "20:00", "end": "08:15"},
    "confirmed": True,
}


def shift_window(d: date, code: str, times: dict = OFFICIAL_ROSTER_TIMES) -> tuple[datetime, datetime]:
    """Official start/end of a D or N shift that *starts* on date d."""
    t = times[code]
    s = combine(d, t["start"])
    e = combine(d, t["end"])
    if e <= s:
        e += timedelta(days=1)
    return s, e
