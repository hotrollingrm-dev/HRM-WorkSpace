"""First-run seeding.

Master data rows are taken from the Template sheet `10` (rows 7–28) and carry a
`source_ref` back to the cell. They are *editable starting points*, not company
standards. Japanese names are left empty (→ [รอแปล]) because no reviewed
translation exists. Holidays are read from the Template's AU5:AV27 table.
"""
from __future__ import annotations

import secrets
from datetime import datetime

import openpyxl
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .auth import hash_password
from .models import (Category, Employee, Holiday, Setting, Subcategory, User, WorkItem,
                     jdump, jload)
from .timeutil import DEFAULT_PLANNING_BANDS, OFFICIAL_ROSTER_TIMES

T = "Template 10!"

# (category th, color, [ (subcategory th, [(item, frequency, location, cell)]) ])
def load_master_seed() -> dict | None:
    """Starting task list from company_data/master_seed.json (company data, kept out of Git)."""
    f = config.COMPANY_DIR / "master_seed.json"
    if not f.exists():
        return None
    import json
    return json.loads(f.read_text(encoding="utf-8"))


def _setting(db: Session, key: str, value) -> None:
    if not db.get(Setting, key):
        db.add(Setting(key=key, value_json=jdump(value)))


def seed_holidays_from_template(db: Session) -> int:
    if not config.TEMPLATE_PATH.exists():
        return 0
    wb = openpyxl.load_workbook(config.TEMPLATE_PATH, read_only=False)
    ws = wb[config.TEMPLATE_SHEET]
    n = 0
    for r in range(5, 28):
        d, name = ws.cell(r, 47).value, ws.cell(r, 48).value   # AU, AV
        if isinstance(d, datetime) and name:
            key = d.date().isoformat()
            if not db.get(Holiday, key):
                db.add(Holiday(date=key, name_th=str(name).strip(), source_ref=f"{T}AU{r}"))
                n += 1
    wb.close()
    return n


def seed_employees_from_template(db: Session) -> int:
    """Read the 12 staff rows of Template sheet 10 (B33:I44). Names are not hard-coded in source."""
    if not config.TEMPLATE_PATH.exists() or db.scalar(select(Employee).limit(1)):
        return 0
    wb = openpyxl.load_workbook(config.TEMPLATE_PATH, read_only=True)
    ws = wb[config.TEMPLATE_SHEET]
    rows = list(ws.iter_rows(min_row=33, max_row=44, min_col=1, max_col=9, values_only=True))
    wb.close()
    n = 0
    for i, (_no, code, name, _d, _e, _f, nick, team, pos) in enumerate(rows):
        if not name:
            continue
        team = str(team or "").strip().upper()
        db.add(Employee(code=str(code or "").strip(), name=" ".join(str(name).split()), nickname=str(nick or "").strip(),
                        team=team if team in ("A", "B", "C") else "A", position=str(pos or "").strip(),
                        sort_order=i * 10, source_ref=f"{T}B{33 + i}:I{33 + i}"))
        n += 1
    return n


MARK_CONFIRMED = {"planned": "✔", "completed": "✔",
                  "_note": "ผู้ใช้ยืนยัน 15 ต.ค. 2026: ✔ = แผนที่วางไว้ (Q-EX1). ช่อง 'ผล Actual' ของ Template จึงนับจำนวนแผน"}


def seed(db: Session, *, with_master: bool = True) -> str | None:
    """Idempotent. Returns generated admin password on first run (else None)."""
    generated = None
    if not db.scalar(select(User).limit(1)):
        pw = config.ADMIN_PASSWORD or secrets.token_urlsafe(9)
        if not config.ADMIN_PASSWORD:
            generated = pw
        db.add(User(username=config.ADMIN_USERNAME, display_name="ผู้ดูแลระบบ",
                    role="admin", password_hash=hash_password(pw)))

    master = load_master_seed() if with_master else None
    if master and not db.scalar(select(Category).where(Category.is_schedule.is_(False)).limit(1)):
        for ci, cat in enumerate(master["categories"]):
            c = Category(name_th=cat["category"], color=cat["color"], code=cat["code"], sort_order=ci * 10,
                         source_ref=T + cat["source_cell"], export_label=cat.get("export_label"))
            db.add(c)
            db.flush()
            for si, sub in enumerate(cat["subcategories"]):
                s = Subcategory(category_id=c.id, name_th=sub["name"], sort_order=si * 10,
                                source_ref=T + sub["items"][0]["source_cell"])
                db.add(s)
                db.flush()
                for ii, it in enumerate(sub["items"]):
                    db.add(WorkItem(subcategory_id=s.id, name_th=it["name"], frequency_label=it["frequency"],
                                    location=it["location"], sort_order=ii * 10, source_ref=T + it["source_cell"],
                                    code=f"{cat['code']}-{si + 1:02d}{ii + 1:02d}"))
    if with_master and not db.scalar(select(Category).where(Category.is_schedule.is_(True)).limit(1)):
        sc = (master or {}).get("schedule_category") or {"name": "ประชุม / กิจกรรม", "color": "#4A6488", "code": "MTG"}
        db.add(Category(name_th=sc["name"], color=sc["color"], code=sc["code"],
                        sort_order=900, is_schedule=True, source_ref="Handover §7"))

    _setting(db, "planning_bands", DEFAULT_PLANNING_BANDS)
    _setting(db, "official_roster_times", OFFICIAL_ROSTER_TIMES)
    ort = db.get(Setting, "official_roster_times")
    if ort and not (jload(ort.value_json) or {}).get("confirmed"):
        ort.value_json = jdump(OFFICIAL_ROSTER_TIMES)      # migrate: user confirmed 08:00–20:15 / 20:00–08:15
    _setting(db, "export_mark_mode", MARK_CONFIRMED)
    mk = db.get(Setting, "export_mark_mode")
    if mk and "Q-EX1 — Template DV" in (jload(mk.value_json) or {}).get("_note", ""):
        mk.value_json = jdump(MARK_CONFIRMED)          # migrate the pre-confirmation default
    _setting(db, "permissions", {"publish": "viewer",
                                 "_note": "ผู้ใช้ยืนยัน 15 ต.ค. 2026: ทุกบทบาท Publish ได้ (Q-SY1)"})
    db.flush()
    if not db.scalar(select(Holiday).limit(1)):
        seed_holidays_from_template(db)
    if with_master:
        seed_employees_from_template(db)
    db.commit()
    return generated
