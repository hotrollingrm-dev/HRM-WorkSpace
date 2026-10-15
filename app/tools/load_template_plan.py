"""Optional: load the planned marks of a Template month sheet (e.g. '10') into that month's
Draft, so the export can be compared side-by-side with the original.

Every ✔/● in the template is loaded as a *planned* entry (never as completed — FILE_AUDIT §1.5-1).
Usage:  python -m tools.load_template_plan 10 2026
"""
from __future__ import annotations

import sys
from datetime import date

import openpyxl
from sqlalchemy import select

from hrm import config
from hrm.db import init_engine, session_scope
from hrm.models import User, WorkItem
from hrm.services import plans as P


def load(sheet: str, year: int, db) -> int:
    ws = openpyxl.load_workbook(config.TEMPLATE_PATH)[sheet]
    month = int(sheet)
    plan = P.get_plan(db, year, month)
    admin = db.scalar(select(User).order_by(User.id))
    by_ref = {w.source_ref: w for w in db.scalars(select(WorkItem))}
    n = 0
    for r in range(7, 29):
        w = by_ref.get(f"Template 10!D{r}")
        if not w:
            continue
        P.ensure_row(db, plan, w.id)
        db.flush()
        days = [c - 12 for c in range(13, 44) if ws.cell(r, c).value in ("✔", "●")]
        dates = [date(year, month, d).isoformat() for d in days if d <= 31]
        existing = {e.date for e in P.active_entries(db, plan.id) if e.work_item_id == w.id}
        dates = [d for d in dates if d not in existing]
        if dates:
            P.create_entries(db, admin.id, plan, dates=dates, work_item_id=w.id, source_type="copy",
                             notes=f"โหลดจาก Template sheet {sheet}")
            n += len(dates)
    return n


if __name__ == "__main__":
    init_engine()
    with session_scope() as db:
        print("loaded", load(sys.argv[1], int(sys.argv[2]), db), "planned entries")
