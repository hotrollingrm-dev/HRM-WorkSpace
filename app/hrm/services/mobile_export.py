"""'ไฟล์สำหรับมือถือ' — a small CSV of the *published* plan for the next 8 operational days.

The user drags this file into their own Google Drive by hand; a Google Apps Script page
(google_apps_script/) reads the newest copy and shows it on phones. This module never sends
anything anywhere — it only builds the file. Personnel names are never included: the shift
rows carry team letters (A/B/C) only. User decision 16 Oct 2026 (manual upload, option 2).
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from ..models import Holiday
from ..timeutil import TZ, op_day_of
from . import plans as P
from . import roster as R

DAYS = 8
FILENAME = "HRM_mobile.csv"
COLUMNS = ["type", "date", "start", "end", "shift", "title", "category", "color", "status", "location", "notes"]
STATUS_TH = {"planned": "แผน", "in_progress": "กำลังทำ", "on_hold": "พักงาน", "pending_review": "รอตรวจ",
             "completed": "เสร็จแล้ว", "cancelled": "ยกเลิก"}


def _hhmm(iso: str | None) -> str:
    return iso[11:16] if iso else ""


def rows(db: Session, start: date | None = None, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(TZ)
    start = start or op_day_of(now)
    days = [start + timedelta(days=i) for i in range(DAYS)]
    lk = P.category_lookup(db)
    entries = P.decorate(db, P.published_for_op_days(db, days), lk)
    out = [{"type": "meta", "date": start.isoformat(), "title": now.replace(microsecond=0).isoformat(),
            "notes": f"HRM WorkSpace · {DAYS} วัน"}]
    for d in days:
        key = d.isoformat()
        sh = R.shift_card(db, d, now)
        hol = db.get(Holiday, key)
        if sh.get("status") == "scheduled":          # team letters only — never member names
            team = {s["code"]: s["team"] or "" for s in sh["shifts"]}
            out.append({"type": "shift", "date": key, "start": team.get("D", ""), "end": team.get("N", ""),
                        "shift": "".join(o["team"] for o in sh.get("off", [])),
                        "title": hol.name_th if hol else ""})
        elif hol:
            out.append({"type": "shift", "date": key, "title": hol.name_th})
    for e in sorted(entries, key=lambda e: (e["op_day"], e.get("start_at") or "~", e.get("title_th") or "")):
        cat = e.get("category") or {}
        st = (e.get("progress") or {}).get("status", "planned")
        out.append({"type": "task", "date": e["op_day"], "start": _hhmm(e.get("start_at")), "end": _hhmm(e.get("end_at")),
                    "shift": e.get("shift") or "", "title": e.get("title_th") or "",
                    "category": cat.get("name_th") or "", "color": cat.get("color") or "#7F8898",
                    "status": STATUS_TH.get(st, st), "location": e.get("location") or "", "notes": e.get("notes") or ""})
    return out


def build_csv(db: Session, start: date | None = None) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows(db, start):
        w.writerow({k: r.get(k, "") for k in COLUMNS})
    return ("﻿" + buf.getvalue()).encode("utf-8")      # BOM so Excel shows Thai correctly
