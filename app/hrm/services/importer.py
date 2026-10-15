"""Import the 'Monthly schedule' workbook (meetings/events) with preview.

Rules (FILE_AUDIT §2, Handover §9):
* Day cells hold serial 1..31 (shown as 1900-01-xx). Month = sheet name; year = user-selected.
* Every row is validated against the weekday text in column C. Mismatch → reject (never guess).
* A cell may contain several events, one per line. Lines without a time → Unscheduled.
* Nothing imported ever creates task progress / completion.
* Re-import: identical content → skip_duplicate; same source cell, different content →
  update_candidate (opt-in); manually edited target → conflict (never overwritten).
"""
from __future__ import annotations

import hashlib
import io
import re
from datetime import date, datetime, timedelta

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (Category, ImportBatch, ImportRow, PlanEntry, audit, jdump,
                      jload, now_iso)
from ..timeutil import TZ, fmt_dt
from .plans import content_key, get_plan, mark_dirty, norm_title

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august",
               "september", "october", "november", "december"]
WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

# Layout profiles: column letters (FILE_AUDIT §2.1)
PROFILES = {
    "P1": {"desc": "May/Jun layout", "header_cell": "E", "header_text": "เช้า",
           "halves": [("morning", {"mbo": "D", "text": "E", "room": "F", "tags": ["G", "H"]}),
                      ("afternoon", {"mbo": "I", "text": "J", "room": "K", "tags": ["L", "M"]})]},
    "P2": {"desc": "Jul–Dec layout", "header_cell": "F", "header_text": "เช้า",
           "halves": [("morning", {"mbo": "D", "text": "F", "room": "E", "tags": []}),
                      ("afternoon", {"mbo": "G", "text": "I", "room": "H", "tags": []}),
                      ("other", {"mbo": None, "text": "J", "room": None, "tags": []})]},
}

TIME_RE = re.compile(
    r"^\s*['’`]?\s*(\d{1,2})\s*[:.]\s*(\d{2})\s*(?:น\.?)?\s*[-–~]\s*(\d{1,2})\s*[:.]\s*(\d{2})\s*(?:น\.?)?\s*['’`]?\s*(.*)$")


class ImportError_(ValueError):
    pass


def _s(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def parse_line(line: str) -> dict:
    m = TIME_RE.match(line)
    if not m:
        return {"time": None, "title": line.strip()}
    h1, m1, h2, m2, rest = int(m[1]), int(m[2]), int(m[3]), int(m[4]), m[5].strip()
    if not (0 <= h1 <= 23 and 0 <= m1 <= 59 and 0 <= h2 <= 23 and 0 <= m2 <= 59):
        return {"time": None, "title": line.strip(), "bad_time": True}
    return {"time": (f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"), "title": rest}


def split_events(text: str) -> list[dict]:
    """A new event starts at the first line or at any line that begins with a time range.
    Untimed lines that follow belong to the current event (wrapped text, attendees …):
    joined to the title when the title is very short (e.g. "#1"), otherwise kept as notes."""
    events: list[dict] = []
    for i, raw in enumerate(text.replace("\r", "").split("\n"), 1):
        line = raw.strip()
        if not line:
            continue
        p = parse_line(line)
        if p["time"] is None and events:
            ev = events[-1]
            if len(ev["title"]) <= 4:
                ev["title"] = (ev["title"] + " " + line).strip()
            else:
                ev["notes"] = (ev.get("notes", "") + " / " + line).strip(" /")
            ev["raw"] += " ⏎ " + line
            continue
        events.append({"line_no": i, "raw": line, **p})
    return events


def detect_month(sheet_name: str) -> int | None:
    n = sheet_name.strip().lower()
    if n in MONTHS:
        return MONTHS[n]
    if n in MONTH_NAMES:
        return MONTH_NAMES.index(n) + 1
    return None


class Grid:
    """Fast cell access over a read-only worksheet (first MAX_COL columns only).
    `g["B12"].value` mimics openpyxl so the parsing code stays readable."""
    MAX_COL, MAX_ROW = 20, 600

    class _C:
        __slots__ = ("value",)

        def __init__(self, v):
            self.value = v

    def __init__(self, ws):
        self.title = ws.title
        self.rows = [tuple(r) for r in ws.iter_rows(min_row=1, max_row=self.MAX_ROW, max_col=self.MAX_COL,
                                                    values_only=True)]
        while self.rows and all(v is None for v in self.rows[-1]):
            self.rows.pop()
        self.max_row = len(self.rows)

    def __getitem__(self, ref: str):
        m = re.fullmatch(r"([A-Z]+)(\d+)", ref)
        col = 0
        for ch in m[1]:
            col = col * 26 + ord(ch) - 64
        r = int(m[2])
        if r > self.max_row or col > self.MAX_COL:
            return self._C(None)
        row = self.rows[r - 1]
        return self._C(row[col - 1] if col <= len(row) else None)


def detect_profile(ws) -> tuple[str | None, int | None]:
    for r in range(1, 8):
        if _s(ws[f"B{r}"].value).startswith("วันที่"):
            for name, p in PROFILES.items():
                if p["header_text"] in _s(ws[f"{p['header_cell']}{r}"].value):
                    return name, r
    return None, None


def _title_month(ws) -> int | None:
    for r in (1, 2):
        t = _s(ws[f"B{r}"].value).lower()
        for i, n in enumerate(MONTH_NAMES, 1):
            if t.startswith(n) or t.startswith(n[:3] + "."):
                return i
    return None


def parse_workbook(data: bytes, year: int) -> dict:
    # read_only: the source has sheets with thousands of merged ranges up to column XFD;
    # a full load takes >10 s, read-only ~0.2 s. Merges are not needed for parsing.
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    sheets, rows = [], []
    for raw_ws in wb.worksheets:
        info = {"sheet": raw_ws.title, "status": "skipped", "reason": "", "warnings": []}
        sheets.append(info)
        month = detect_month(raw_ws.title)
        if not month:
            info["reason"] = "ชื่อ sheet ไม่ใช่เดือน (เช่น Master plan / HOT Plan) — ยังไม่รองรับ (Q-IM5)"
            continue
        ws = Grid(raw_ws)
        prof, hdr = detect_profile(ws)
        if not month:
            info["reason"] = "ชื่อ sheet ไม่ใช่เดือน (เช่น Master plan / HOT Plan) — ยังไม่รองรับ (Q-IM5)"
            continue
        if not prof:
            info["reason"] = "ไม่พบรูปแบบหัวตารางที่รู้จัก"
            continue
        tm = _title_month(ws)
        if tm and tm != month:
            info["warnings"].append(
                f"หัวเอกสาร B1/B2 ระบุเดือน {MONTH_NAMES[tm - 1].title()} แต่ชื่อ sheet = {ws.title} — ใช้ชื่อ sheet + ตรวจชื่อวัน")
        info.update(status="parsed", profile=prof, month=month)

        # day blocks: row of a day number in col B until next day number
        starts = []
        for r in range(hdr + 1, ws.max_row + 1):
            v = ws[f"B{r}"].value
            day = None
            if isinstance(v, datetime) and v.year == 1900 and v.month == 1:
                day = v.day
            elif isinstance(v, (int, float)) and 1 <= int(v) <= 31:
                day = int(v)
            if day:
                starts.append((r, day))
        seen_days = {}
        for bi, (r0, day) in enumerate(starts):
            if bi + 1 < len(starts):
                r1 = starts[bi + 1][0]
            else:  # last day: typical block height, stop at footer/legend rows
                heights = sorted(b[0] - a[0] for a, b in zip(starts, starts[1:])) or [2]
                r1 = min(ws.max_row + 1, r0 + heights[len(heights) // 2])
                for rr in range(r0 + 1, r1):
                    if _s(ws[f"C{rr}"].value) and _s(ws[f"C{rr}"].value)[:3].lower() not in WEEKDAYS:
                        r1 = rr
                        break
            wd_text = _s(ws[f"C{r0}"].value)
            issues, d_iso = [], None
            try:
                dd = date(year, month, day)
                d_iso = dd.isoformat()
                if wd_text[:3].lower() in WEEKDAYS and WEEKDAYS[dd.weekday()] != wd_text[:3].lower():
                    issues.append({"level": "error", "code": "weekday_mismatch",
                                   "msg": f"B{r0} วันที่ {day} ระบุ {wd_text} แต่ {d_iso} เป็น {WEEKDAYS[dd.weekday()].title()}"})
                elif not wd_text:
                    issues.append({"level": "warn", "code": "no_weekday", "msg": f"C{r0} ไม่มีชื่อวันให้ตรวจ"})
            except ValueError:
                issues.append({"level": "error", "code": "invalid_date",
                               "msg": f"B{r0} วันที่ {day} ไม่มีในเดือน {month}/{year}"})
            if day in seen_days:
                issues.append({"level": "error", "code": "duplicate_day",
                               "msg": f"B{r0} วันที่ {day} ซ้ำกับ B{seen_days[day]}"})
            seen_days.setdefault(day, r0)

            for r in range(r0, r1):
                for slot, cols in PROFILES[prof]["halves"]:
                    text = _s(ws[f"{cols['text']}{r}"].value)
                    if not text:
                        continue
                    mbo = " ".join(_s(ws[f"{cols['mbo']}{r}"].value).split()) if cols["mbo"] else ""
                    room = " ".join(_s(ws[f"{cols['room']}{r}"].value).split()) if cols["room"] else ""
                    tags = [f"{_s(ws[f'{c}{hdr}'].value) or c}:{_s(ws[f'{c}{r}'].value)}"
                            for c in cols["tags"] if _s(ws[f"{c}{r}"].value)]
                    for ev in split_events(text):
                        row_issues = list(issues)
                        s_at = e_at = None
                        if ev.get("bad_time"):
                            row_issues.append({"level": "warn", "code": "bad_time",
                                               "msg": "รูปแบบเวลาไม่ถูกต้อง → Unscheduled"})
                        if ev["time"] and d_iso:
                            st = datetime.combine(date.fromisoformat(d_iso),
                                                  datetime.strptime(ev["time"][0], "%H:%M").time(), TZ)
                            en = datetime.combine(date.fromisoformat(d_iso),
                                                  datetime.strptime(ev["time"][1], "%H:%M").time(), TZ)
                            if en <= st:
                                en += timedelta(days=1)
                                row_issues.append({"level": "warn", "code": "cross_midnight",
                                                   "msg": "เวลาสิ้นสุดน้อยกว่าเวลาเริ่ม → ถือว่าข้ามเที่ยงคืน กรุณาตรวจ"})
                            s_at, e_at = fmt_dt(st), fmt_dt(en)
                        elif not ev["time"]:
                            row_issues.append({"level": "info", "code": "unscheduled",
                                               "msg": "ไม่มีเวลา → Unscheduled (ไม่เดาเวลา)"})
                        title = ev["title"] or ev["raw"]
                        if mbo and re.fullmatch(r"\d{5,}", mbo):
                            row_issues.append({"level": "warn", "code": "mbo_numeric",
                                               "msg": f"เลข MBO '{mbo}' อาจเป็นหลายรายการที่ Excel รวมเป็นตัวเลข (Q-IM3)"})
                        notes = ev.get("notes", "")
                        if tags:
                            notes = (notes + " · " if notes else "") + "แท็ก " + ", ".join(tags)
                        rows.append({
                            "sheet": ws.title, "cell_ref": f"{cols['text']}{r}", "line_no": ev["line_no"],
                            "raw_text": ev["raw"], "date": d_iso, "start_at": s_at, "end_at": e_at,
                            "title": title.strip(), "location": room, "mbo_ref": mbo,
                            "time_slot": slot, "notes": notes, "issues": row_issues,
                        })
        info["days"] = len(starts)
    wb.close()
    return {"sheets": sheets, "rows": rows}


def _initial_action(db: Session, r: dict) -> tuple[str, str | None]:
    if any(i["level"] == "error" for i in r["issues"]):
        return "reject", None
    key = content_key(r["date"], r["start_at"], r["title"])
    dup = db.scalar(select(PlanEntry).where(PlanEntry.content_key == key, PlanEntry.deleted_at.is_(None)))
    if dup:
        return "skip_duplicate", dup.uid
    ref = f"{r['sheet']}!{r['cell_ref']}#{r['line_no']}"
    same_src = db.scalar(select(PlanEntry).where(PlanEntry.source_ref == ref,
                                                 PlanEntry.source_type == "import",
                                                 PlanEntry.deleted_at.is_(None),
                                                 PlanEntry.date == r["date"]))
    if same_src:
        return ("conflict" if same_src.manually_edited else "update_candidate"), same_src.uid
    return "add", None


def create_batch(db: Session, user_id: int, filename: str, data: bytes, year: int) -> ImportBatch:
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        raise ImportError_("รองรับเฉพาะไฟล์ .xlsx / .xlsm")
    if not (2000 <= year <= 2100):
        raise ImportError_("ปีไม่ถูกต้อง")
    sha = hashlib.sha256(data).hexdigest()
    try:
        parsed = parse_workbook(data, year)
    except Exception as ex:  # corrupt / not a workbook
        raise ImportError_(f"เปิดไฟล์ไม่ได้: {ex}") from ex
    prev = db.scalar(select(ImportBatch).where(ImportBatch.sha256 == sha,
                                               ImportBatch.status == "committed"))
    b = ImportBatch(filename=filename, sha256=sha, target_year=year, uploaded_by=user_id)
    db.add(b)
    db.flush()
    counts: dict[str, int] = {}
    for r in parsed["rows"]:
        action, match = _initial_action(db, r)
        counts[action] = counts.get(action, 0) + 1
        db.add(ImportRow(batch_id=b.id, sheet=r["sheet"], cell_ref=r["cell_ref"], line_no=r["line_no"],
                         raw_text=r["raw_text"], date=r["date"], start_at=r["start_at"], end_at=r["end_at"],
                         title=r["title"], location=r["location"], mbo_ref=r["mbo_ref"],
                         time_slot=r["time_slot"],
                         issues_json=jdump(r["issues"] + ([{"level": "info", "code": "notes", "msg": r["notes"]}]
                                                          if r["notes"] else [])),
                         action=action, match_entry_uid=match))
    b.summary_json = jdump({"sheets": parsed["sheets"], "counts": counts,
                            "previous_commit_same_file": prev.id if prev else None})
    audit(db, user_id, "import_preview", "import_batch", b.id, {"filename": filename, "sha256": sha})
    db.flush()
    return b


ALLOWED_ACTIONS = {"add", "skip", "skip_duplicate", "update_candidate", "update", "reject", "conflict"}


def update_row(db: Session, row: ImportRow, changes: dict) -> ImportRow:
    b = db.get(ImportBatch, row.batch_id)
    if b.status != "preview":
        raise ImportError_("batch นี้ยืนยันแล้ว แก้ไม่ได้")
    if "action" in changes:
        a = changes["action"]
        if a not in ("add", "skip", "update"):
            raise ImportError_("เลือกได้: add / skip / update")
        if a == "update" and row.action not in ("update_candidate", "update"):
            raise ImportError_("อัปเดตได้เฉพาะแถวที่เป็น update_candidate (แถวที่ถูกแก้มือแล้วจะไม่ถูกทับ)")
        if a == "add" and row.action in ("reject",) and not changes.get("date"):
            raise ImportError_("แถวที่ถูกปฏิเสธต้องแก้วันที่ก่อนจึงเพิ่มได้")
        row.action = a
    for k in ("title", "date", "start_at", "end_at", "location"):
        if k in changes:
            setattr(row, k, changes[k] or None if k in ("start_at", "end_at") else changes[k])
    if "date" in changes and changes["date"]:
        date.fromisoformat(changes["date"])
        issues = [i for i in jload(row.issues_json) if i["level"] != "error"]
        issues.append({"level": "info", "code": "user_fixed", "msg": f"ผู้ใช้แก้วันที่เป็น {changes['date']}"})
        row.issues_json = jdump(issues)
        if row.action == "reject":
            row.action = "add"
    from ..timeutil import validate_range
    validate_range(row.start_at, row.end_at)
    return row


def commit_batch(db: Session, user_id: int, b: ImportBatch) -> dict:
    if b.status != "preview":
        raise ImportError_("batch นี้ไม่ได้อยู่ในสถานะ preview")
    sched = db.scalar(select(Category).where(Category.is_schedule.is_(True)))
    rows = list(db.scalars(select(ImportRow).where(ImportRow.batch_id == b.id)))
    added = updated = 0
    for r in rows:
        if r.action == "add" and r.date:
            p = get_plan(db, int(r.date[:4]), int(r.date[5:7]))
            notes = "; ".join(i["msg"] for i in jload(r.issues_json) if i["code"] == "notes")
            e = PlanEntry(plan_id=p.id, category_id=sched.id if sched else None, title_th=r.title,
                          date=r.date, start_at=r.start_at, end_at=r.end_at, time_slot=r.time_slot,
                          location=r.location, mbo_ref=r.mbo_ref, notes=notes, source_type="import",
                          source_ref=f"{r.sheet}!{r.cell_ref}#{r.line_no}", import_batch_id=b.id,
                          original_date=r.date, created_by=user_id, updated_by=user_id,
                          content_key=content_key(r.date, r.start_at, r.title))
            db.add(e)
            db.flush()
            r.entry_uid = e.uid
            mark_dirty(p)
            added += 1
        elif r.action == "update" and r.match_entry_uid:
            e = db.scalar(select(PlanEntry).where(PlanEntry.uid == r.match_entry_uid))
            if e and not e.manually_edited and e.deleted_at is None:
                e.title_th, e.start_at, e.end_at, e.location = r.title, r.start_at, r.end_at, r.location
                e.content_key = content_key(e.date, e.start_at, e.title_th)
                e.import_batch_id, e.updated_by, e.updated_at = b.id, user_id, now_iso()
                r.entry_uid = e.uid
                mark_dirty(get_plan(db, int(e.date[:4]), int(e.date[5:7])))
                updated += 1
    b.status = "committed"
    s = jload(b.summary_json)
    s["committed"] = {"added": added, "updated": updated, "at": now_iso()}
    b.summary_json = jdump(s)
    audit(db, user_id, "import_commit", "import_batch", b.id, s["committed"])
    db.flush()
    return s["committed"]


def revert_batch(db: Session, user_id: int, b: ImportBatch) -> dict:
    if b.status != "committed":
        raise ImportError_("ย้อนกลับได้เฉพาะ batch ที่ยืนยันแล้ว")
    removed, kept = 0, []
    for e in db.scalars(select(PlanEntry).where(PlanEntry.import_batch_id == b.id,
                                                PlanEntry.source_type == "import",
                                                PlanEntry.deleted_at.is_(None))):
        if e.manually_edited:
            kept.append(e.uid)
            continue
        e.deleted_at = now_iso()
        mark_dirty(get_plan(db, int(e.date[:4]), int(e.date[5:7])))
        removed += 1
    b.status = "reverted"
    audit(db, user_id, "import_revert", "import_batch", b.id, {"removed": removed, "kept_edited": kept})
    db.flush()
    return {"removed": removed, "kept_manually_edited": kept}


def norm(s):  # re-export for tests
    return norm_title(s)
