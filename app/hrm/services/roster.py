"""Group shift calendar (3 groups × 2 shifts) from the scanned PDF.

The PDF is an image, so its codes come from a reviewed transcription
(hrm/data/roster_pdf_codes.py) plus pixel-detected cell fills
(hrm/data/roster_pdf_fills.json). Import = preview with checksums → user confirms → commit.
Scheduled ≠ present: nothing here records attendance.
"""
from __future__ import annotations

import calendar
import json
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Employee, RosterBatch, Setting, ShiftDay, audit, jdump, jload, now_iso
from ..timeutil import OFFICIAL_ROSTER_TIMES, TZ, shift_window

from .. import config


class RosterError(ValueError):
    pass


class _Src:
    """Roster transcription loaded from company_data/roster_codes.json (company data, kept out of Git)."""
    def __init__(self):
        f = config.COMPANY_DIR / "roster_codes.json"
        if not f.exists():
            raise RosterError("ไม่พบไฟล์ตารางกะ company_data/roster_codes.json บนเครื่องนี้ — ดูคู่มือติดตั้ง ขั้นตอนใส่ไฟล์ข้อมูลบริษัท")
        d = json.loads(f.read_text(encoding="utf-8"))
        self.SOURCE, self.CODES, self.SUMMARY_2026 = d["source"], d["codes"], d["summary_2026"]
        self.WD = {k: tuple(v) for k, v in d["wd"].items()}
        self.DAY_MARKS = d.get("day_marks", {})


def _fills_path() -> Path:
    return config.COMPANY_DIR / "roster_fills.json"
TEAMS = ("A", "B", "C")
FILL_TH = {"special": "ทำงานวันหยุดนักขัตฤกษ์ (ช่องสีเหลืองใน PDF — ผู้ใช้ยืนยัน 15 ต.ค. 2026)",
           "substitution": "ช่องสีเขียว — Substitution of working days"}


def _source_cells() -> dict:
    SRC = _Src()
    fp = _fills_path()
    fills = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}
    cells = {}
    for ym, groups in SRC.CODES.items():
        y, m = map(int, ym.split("-"))
        for t in TEAMS:
            for i, code in enumerate(groups[t]):
                d = date(y, m, i + 1).isoformat()
                cells.setdefault(d, {})[t] = [code, fills.get(d, {}).get(t)]
    return cells


def run_checks(cells: dict) -> dict:
    """Checksums against numbers printed in the PDF + structural rules."""
    SRC = _Src()
    wd_rows, wd_bad = 0, []
    for ym, wd in SRC.WD.items():
        y, m = map(int, ym.split("-"))
        n = calendar.monthrange(y, m)[1]
        for t, expect in zip(TEAMS, wd):
            codes = [cells[date(y, m, i).isoformat()][t][0] for i in range(1, n + 1)]
            got = sum(c in "DN" for c in codes)
            wd_rows += 1
            if got != expect:
                wd_bad.append(f"{ym} ทีม {t}: นับได้ {got} แต่ PDF ระบุ WD {expect}")
    summary = {}
    for t, label in zip(TEAMS, ("Group 1", "Group 2", "Group 3")):
        codes = [v[t][0] for d, v in cells.items() if d.startswith("2026-")]
        got = {k: codes.count(k) for k in "DNHS"}
        summary[t] = {"label": label, "counted": got, "printed": SRC.SUMMARY_2026[label],
                      "match": got == SRC.SUMMARY_2026[label]}
    coverage = []
    for d, v in sorted(cells.items()):
        col = sorted(v[t][0] for t in TEAMS)
        if col not in (["D", "H", "N"], ["S", "S", "S"]):
            subs = [t for t in TEAMS if v[t][1] == "substitution"]
            coverage.append({"date": d, "codes": {t: v[t][0] for t in TEAMS},
                             "explained_by_substitution": bool(subs)})
    special_on_holiday = [d for d, v in cells.items() for t in TEAMS if v[t][1] == "special" and v[t][0] == "H"]
    ok = not wd_bad and all(s["match"] for s in summary.values()) and all(c["explained_by_substitution"] for c in coverage)
    return {"ok": ok, "months": len(SRC.CODES), "days": len(cells), "wd_rows_checked": wd_rows, "wd_mismatches": wd_bad,
            "summary_2026": summary, "group_mapping": "Group 1/2/3 = A/B/C (ยอดรวมปี 2026 ตรงทุกค่าเมื่อจับคู่แบบนี้)",
            "coverage_exceptions": coverage, "special_on_holiday": special_on_holiday,
            "fills": {"special": sum(1 for v in cells.values() for t in TEAMS if v[t][1] == "special"),
                      "substitution": sum(1 for v in cells.values() for t in TEAMS if v[t][1] == "substitution")},
            "shutdown_days_2026": sum(1 for d, v in cells.items() if d.startswith("2026-") and v["A"][0] == "S"),
            "provisional_from": "2027-01-01", "provisional_note": "PDF: \"Calendar of 2027 might be changed\""}


def create_preview(db: Session, user_id: int) -> RosterBatch:
    cells = _source_cells()
    b = RosterBatch(source=_Src().SOURCE, created_by=user_id,
                    method="ถอดจากภาพสแกน 300 dpi ด้วยการอ่านทีละช่อง + ตรวจสีพื้นช่องด้วยโปรแกรม",
                    checks_json=jdump(run_checks(cells)), data_json=jdump(cells))
    db.add(b)
    db.flush()
    audit(db, user_id, "roster_preview", "roster_batch", b.id, {})
    return b


def commit(db: Session, user_id: int, b: RosterBatch) -> dict:
    if b.status != "preview":
        raise RosterError("batch นี้ไม่ได้อยู่ในสถานะรอยืนยัน")
    cells = jload(b.data_json)
    existing = {(s.date, s.team): s for s in db.scalars(select(ShiftDay))}
    added = updated = kept = 0
    for d, teams in cells.items():
        for t, (code, fill) in teams.items():
            ref = f"PDF {d[:7]} Group {t} วันที่ {int(d[8:])}"
            cur = existing.get((d, t))
            if cur is None:
                db.add(ShiftDay(date=d, team=t, code=code, fill=fill, source_ref=ref, batch_id=b.id, updated_by=user_id))
                added += 1
            elif cur.manually_edited:
                kept += 1
            elif (cur.code, cur.fill) != (code, fill):
                cur.code, cur.fill, cur.batch_id, cur.updated_by, cur.updated_at = code, fill, b.id, user_id, now_iso()
                updated += 1
    b.status = "committed"
    res = {"added": added, "updated": updated, "kept_manually_edited": kept}
    audit(db, user_id, "roster_commit", "roster_batch", b.id, res)
    db.flush()
    return res


def edit_day(db: Session, user_id: int, d: str, team: str, code: str) -> ShiftDay:
    if team not in TEAMS or code not in ("D", "N", "H", "S"):
        raise RosterError("ทีมต้องเป็น A/B/C และรหัสต้องเป็น D, N, H หรือ S")
    s = db.scalar(select(ShiftDay).where(ShiftDay.date == d, ShiftDay.team == team))
    if not s:
        raise RosterError("ยังไม่มีตารางกะของวันนี้ — นำเข้าตารางกะก่อน")
    before = s.code
    s.code, s.manually_edited, s.updated_by, s.updated_at = code, True, user_id, now_iso()
    audit(db, user_id, "roster_edit", "shift_day", f"{d}/{team}", {"from": before, "to": code})
    return s


def teams_on(db: Session, d: date) -> dict:
    rows = {s.team: s for s in db.scalars(select(ShiftDay).where(ShiftDay.date == d.isoformat()))}
    return {t: {"code": rows[t].code, "fill": rows[t].fill, "edited": rows[t].manually_edited} for t in rows}


def month_codes(db: Session, first: date, last: date) -> dict:
    out = {}
    for s in db.scalars(select(ShiftDay).where(ShiftDay.date >= first.isoformat(), ShiftDay.date <= last.isoformat())):
        out.setdefault(s.date, {})[s.team] = s.code
    return out


def _times(db: Session) -> dict:
    st = db.get(Setting, "official_roster_times")
    return jload(st.value_json) if st else OFFICIAL_ROSTER_TIMES


def shift_card(db: Session, op_day: date, now=None) -> dict:
    """Who is *scheduled* for the D shift of op_day and the N shift starting that evening."""
    staff = list(db.scalars(select(Employee).where(Employee.active.is_(True)).order_by(Employee.team, Employee.sort_order)))
    members = {}
    for e in staff:
        members.setdefault(e.team, []).append({"name": e.name, "nickname": e.nickname, "position": e.position})
    day = teams_on(db, op_day)
    if not day:
        return {"status": "no_calendar", "teams": members,
                "message": "ยังไม่ได้นำเข้าตารางกะของวันนี้ — นำเข้าได้ที่ ตั้งค่า → ตารางกะ"}
    times = _times(db)
    shifts = []
    for code in ("D", "N"):
        team = next((t for t, v in day.items() if v["code"] == code), None)
        others = [t for t, v in day.items() if v["code"] == code and t != team]
        s, e = shift_window(op_day, code, times)
        shifts.append({"code": code, "team": team, "also": others, "start": s.isoformat(), "end": e.isoformat(),
                       "members": members.get(team, []) if team else [],
                       "fill": day.get(team, {}).get("fill") if team else None})
    off = [{"team": t, "code": v["code"]} for t, v in sorted(day.items()) if v["code"] in ("H", "S")]
    provisional = op_day.isoformat() >= "2027-01-01"
    phase = None
    if now is not None:
        for sh in shifts:
            if sh["start"] <= now.isoformat() < sh["end"]:
                phase = sh["code"] if phase is None else "handover"
    return {"status": "scheduled", "op_day": op_day.isoformat(), "shifts": shifts, "off": off, "teams": members,
            "now_phase": phase, "provisional": provisional,
            "times": {"D": times["D"], "N": times["N"]},
            "message": " · ".join(f"กะ {s['code']} ทีม {s['team'] or '—'}" for s in shifts),
            "note": "ตามตารางกะ (ไม่ใช่การบันทึกเข้างานจริง)"}
