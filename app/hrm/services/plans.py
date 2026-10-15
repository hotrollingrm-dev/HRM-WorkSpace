"""Monthly plan: draft working copy, publish snapshots, progress, today views."""
from __future__ import annotations

import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (Category, MonthlyPlan, PlanEntry, PlanRow, PlanVersion,
                      Subcategory, TaskProgress, WorkItem, audit, jdump, jload,
                      now_iso)
from ..timeutil import (TimeError, entry_op_day, find_overlaps, month_days,
                        validate_range)

SNAP_FIELDS = ("uid", "work_item_id", "category_id", "title_th", "title_jp", "date",
               "start_at", "end_at", "shift", "time_slot", "location", "notes",
               "mbo_ref", "source_type", "source_ref", "original_date")
DIFF_FIELDS = ("date", "start_at", "end_at", "shift", "title_th", "location", "notes")


class PlanError(ValueError):
    pass


def norm_title(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def content_key(d: str, start_at: str | None, title: str) -> str:
    return f"{d}|{start_at or '-'}|{norm_title(title)}"


def get_plan(db: Session, year: int, month: int, create: bool = True) -> MonthlyPlan | None:
    if not (1 <= month <= 12 and 2000 <= year <= 2100):
        raise PlanError("ปี/เดือนไม่ถูกต้อง")
    p = db.scalar(select(MonthlyPlan).where(MonthlyPlan.year == year, MonthlyPlan.month == month))
    if not p and create:
        p = MonthlyPlan(year=year, month=month)
        db.add(p)
        db.flush()
    return p


def plan_for_date(db: Session, d: str) -> MonthlyPlan:
    dd = date.fromisoformat(d)
    return get_plan(db, dd.year, dd.month)


def active_entries(db: Session, plan_id: int) -> list[PlanEntry]:
    return list(db.scalars(select(PlanEntry).where(
        PlanEntry.plan_id == plan_id, PlanEntry.deleted_at.is_(None)
    ).order_by(PlanEntry.date, PlanEntry.start_at, PlanEntry.id)))


def entry_dict(e: PlanEntry) -> dict:
    return {f: getattr(e, f) for f in SNAP_FIELDS} | {
        "id": e.id, "manually_edited": e.manually_edited, "updated_at": e.updated_at}


def mark_dirty(p: MonthlyPlan) -> None:
    p.draft_dirty = True


def ensure_row(db: Session, plan: MonthlyPlan, work_item_id: int) -> None:
    exists = db.scalar(select(PlanRow).where(PlanRow.plan_id == plan.id,
                                             PlanRow.work_item_id == work_item_id))
    if not exists:
        n = len(list(db.scalars(select(PlanRow.id).where(PlanRow.plan_id == plan.id))))
        db.add(PlanRow(plan_id=plan.id, work_item_id=work_item_id, sort_order=n * 10))
        db.flush()   # session uses autoflush=False; make the row visible to the next check


def _check_date_in_plan(plan: MonthlyPlan, d: str) -> None:
    dd = date.fromisoformat(d)
    if (dd.year, dd.month) != (plan.year, plan.month):
        raise PlanError(f"วันที่ {d} ไม่อยู่ในเดือนของแผน {plan.year}-{plan.month:02d}")


def create_entries(db: Session, user_id: int, plan: MonthlyPlan, *, dates: list[str],
                   work_item_id: int | None = None, category_id: int | None = None,
                   title_th: str | None = None, start_at_by_date: dict | None = None,
                   shift: str | None = None, location: str = "", notes: str = "",
                   source_type: str = "manual") -> list[PlanEntry]:
    """Quick Entry: one save → one entry per selected date."""
    if not dates:
        raise PlanError("เลือกอย่างน้อย 1 วัน")
    if len(set(dates)) != len(dates):
        raise PlanError("มีวันที่ซ้ำในรายการที่เลือก")
    if shift not in (None, "", "D", "N"):
        raise PlanError("กะต้องเป็น D หรือ N")
    wi = None
    if work_item_id:
        wi = db.get(WorkItem, work_item_id)
        if not wi or not wi.active:
            raise PlanError("ไม่พบรายการงาน หรือรายการถูกปิดใช้งาน")
        title_th = wi.name_th
        category_id = wi.subcategory.category_id
        location = location or wi.location
    if not (title_th or "").strip():
        raise PlanError("ต้องระบุชื่องาน")
    out = []
    for d in sorted(dates):
        _check_date_in_plan(plan, d)
        s_at, e_at = (start_at_by_date or {}).get(d, (None, None))
        try:
            validate_range(s_at, e_at)
        except TimeError as ex:
            raise PlanError(str(ex)) from ex
        e = PlanEntry(plan_id=plan.id, work_item_id=work_item_id, category_id=category_id,
                      title_th=title_th.strip(), title_jp=wi.name_jp if wi else None,
                      date=d, start_at=s_at, end_at=e_at, shift=shift or None,
                      location=location, notes=notes, source_type=source_type,
                      original_date=d, created_by=user_id, updated_by=user_id)
        e.content_key = content_key(d, s_at, e.title_th)
        db.add(e)
        out.append(e)
    if work_item_id:
        ensure_row(db, plan, work_item_id)
    mark_dirty(plan)
    db.flush()
    audit(db, user_id, "create_entries", "plan", plan.id,
          {"uids": [e.uid for e in out], "dates": sorted(dates)})
    return out


EDITABLE = ("date", "start_at", "end_at", "shift", "title_th", "location", "notes")


def update_entry(db: Session, user_id: int, e: PlanEntry, changes: dict) -> PlanEntry:
    plan = db.get(MonthlyPlan, e.plan_id)
    before = entry_dict(e)
    for k in EDITABLE:
        if k in changes:
            setattr(e, k, changes[k] or None if k in ("start_at", "end_at", "shift") else changes[k])
    if e.shift not in (None, "D", "N"):
        raise PlanError("กะต้องเป็น D หรือ N")
    _check_date_in_plan(plan, e.date)
    try:
        validate_range(e.start_at, e.end_at)
    except TimeError as ex:
        raise PlanError(str(ex)) from ex
    if e.source_type == "import":
        e.manually_edited = True
    e.content_key = content_key(e.date, e.start_at, e.title_th)
    e.updated_by = user_id
    e.updated_at = now_iso()
    mark_dirty(plan)
    audit(db, user_id, "update_entry", "entry", e.uid,
          {"before": {k: before[k] for k in EDITABLE}, "after": {k: getattr(e, k) for k in EDITABLE}})
    return e


def delete_entry(db: Session, user_id: int, e: PlanEntry) -> None:
    e.deleted_at = now_iso()
    e.updated_by = user_id
    mark_dirty(db.get(MonthlyPlan, e.plan_id))
    audit(db, user_id, "delete_entry", "entry", e.uid, {"date": e.date, "title": e.title_th})


def toggle_cell(db: Session, user_id: int, plan: MonthlyPlan, work_item_id: int, d: str) -> dict:
    """Matrix click: add an all-day entry for (item, date) or remove it if exactly one exists."""
    existing = [e for e in active_entries(db, plan.id) if e.work_item_id == work_item_id and e.date == d]
    if existing:
        if len(existing) > 1 or existing[0].start_at:
            return {"action": "open", "uids": [e.uid for e in existing]}
        delete_entry(db, user_id, existing[0])
        return {"action": "removed", "uid": existing[0].uid}
    e = create_entries(db, user_id, plan, dates=[d], work_item_id=work_item_id)[0]
    return {"action": "added", "uid": e.uid}


def latest_version(db: Session, plan_id: int) -> PlanVersion | None:
    return db.scalar(select(PlanVersion).where(PlanVersion.plan_id == plan_id)
                     .order_by(PlanVersion.revision.desc()).limit(1))


def _diff(prev: list[dict], cur: list[dict]) -> dict:
    pm = {e["uid"]: e for e in prev}
    cm = {e["uid"]: e for e in cur}
    added = [u for u in cm if u not in pm]
    removed = [u for u in pm if u not in cm]
    changed = []
    for u in cm:
        if u in pm:
            f = [k for k in DIFF_FIELDS if pm[u].get(k) != cm[u].get(k)]
            if f:
                changed.append({"uid": u, "fields": f,
                                "before": {k: pm[u].get(k) for k in f},
                                "after": {k: cm[u].get(k) for k in f}})
    return {"added": added, "removed": removed, "changed": changed,
            "removed_titles": {u: pm[u]["title_th"] for u in removed}}


def pending_diff(db: Session, plan: MonthlyPlan) -> dict:
    snap = [{f: getattr(e, f) for f in SNAP_FIELDS} for e in active_entries(db, plan.id)]
    prev = latest_version(db, plan.id)
    d = _diff(jload(prev.snapshot_json) if prev else [], snap)
    titles = {e["uid"]: (e["title_th"], e["date"]) for e in snap}
    d["titles"] = titles
    d["next_revision"] = (prev.revision if prev else 0) + 1
    return d


def publish(db: Session, user_id: int, plan: MonthlyPlan, note: str = "") -> PlanVersion:
    snap = [{f: getattr(e, f) for f in SNAP_FIELDS} for e in active_entries(db, plan.id)]
    prev = latest_version(db, plan.id)
    prev_snap = jload(prev.snapshot_json) if prev else []
    diff = _diff(prev_snap, snap)
    if prev and not (diff["added"] or diff["removed"] or diff["changed"]):
        raise PlanError("ไม่มีการเปลี่ยนแปลงจาก REV ล่าสุด")
    rev = (prev.revision if prev else 0) + 1
    v = PlanVersion(plan_id=plan.id, revision=rev, published_by=user_id, note=note,
                    snapshot_json=jdump(snap), diff_json=jdump(diff))
    db.add(v)
    plan.current_revision = rev
    plan.last_published_at = v.published_at
    plan.draft_dirty = False
    audit(db, user_id, "publish", "plan", plan.id,
          {"revision": rev, "counts": {k: len(diff[k]) for k in ("added", "removed", "changed")}})
    db.flush()
    return v


def published_entries(db: Session, plan: MonthlyPlan) -> tuple[list[dict], PlanVersion | None]:
    v = latest_version(db, plan.id)
    return (jload(v.snapshot_json) if v else []), v


def copy_prior_month(db: Session, user_id: int, plan: MonthlyPlan, with_dates: bool) -> dict:
    py, pm = (plan.year - 1, 12) if plan.month == 1 else (plan.year, plan.month - 1)
    prev = get_plan(db, py, pm, create=False)
    if not prev:
        raise PlanError("ไม่มีแผนของเดือนก่อนหน้า")
    rows = list(db.scalars(select(PlanRow).where(PlanRow.plan_id == prev.id).order_by(PlanRow.sort_order)))
    for r in rows:
        ensure_row(db, plan, r.work_item_id)
    copied, skipped = 0, []
    if with_dates:
        valid_days = {d.day for d in month_days(plan.year, plan.month)}
        have = {(e.work_item_id, e.date) for e in active_entries(db, plan.id)}
        for e in active_entries(db, prev.id):
            if not e.work_item_id:
                continue   # imported meetings are month-specific
            day = int(e.date[8:])
            if day not in valid_days:
                skipped.append(e.date)
                continue
            nd = date(plan.year, plan.month, day).isoformat()
            if (e.work_item_id, nd) in have:
                continue
            ne = create_entries(db, user_id, plan, dates=[nd], work_item_id=e.work_item_id,
                                shift=e.shift, notes=e.notes, source_type="copy")
            copied += len(ne)
    mark_dirty(plan)
    db.flush()
    return {"rows": len(rows), "entries": copied, "skipped_dates": skipped}


def set_progress(db: Session, user, uid: str, status: str, note: str = "") -> TaskProgress:
    from ..auth import RANK
    allowed = {"planned", "in_progress", "on_hold", "pending_review", "completed", "cancelled"}
    if status not in allowed:
        raise PlanError("สถานะไม่ถูกต้อง")
    if status in ("completed", "cancelled") and RANK[user.role] < RANK["leader"]:
        raise PlanError("ต้องเป็น Leader ขึ้นไปจึงยืนยัน 'เสร็จ' หรือ 'ยกเลิก' ได้ — ใช้ 'ส่งตรวจ' แทน")
    tp = db.get(TaskProgress, uid) or TaskProgress(entry_uid=uid)
    old = tp.status
    tp.status, tp.note, tp.updated_by, tp.updated_at = status, note, user.id, now_iso()
    db.add(tp)
    audit(db, user.id, "progress", "entry", uid, {"from": old, "to": status, "note": note})
    return tp


def progress_map(db: Session, uids: list[str]) -> dict[str, dict]:
    if not uids:
        return {}
    rows = db.scalars(select(TaskProgress).where(TaskProgress.entry_uid.in_(uids)))
    return {r.entry_uid: {"status": r.status, "note": r.note, "updated_at": r.updated_at} for r in rows}


def category_lookup(db: Session) -> dict:
    cats = {c.id: c for c in db.scalars(select(Category))}
    items = {w.id: w for w in db.scalars(select(WorkItem))}
    subs = {s.id: s for s in db.scalars(select(Subcategory))}
    return {"cats": cats, "items": items, "subs": subs}


def decorate(db: Session, entries: list[dict], lk: dict | None = None) -> list[dict]:
    lk = lk or category_lookup(db)
    prog = progress_map(db, [e["uid"] for e in entries])
    out = []
    for e in entries:
        cat = lk["cats"].get(e.get("category_id"))
        wi = lk["items"].get(e.get("work_item_id"))
        sub = lk["subs"].get(wi.subcategory_id) if wi else None
        out.append(e | {
            "category": {"id": cat.id, "name_th": cat.name_th, "name_jp": cat.name_jp,
                         "color": cat.color} if cat else None,
            "subcategory": sub.name_th if sub else None,
            "progress": prog.get(e["uid"], {"status": "planned"}),
            "op_day": entry_op_day(e["date"], e.get("start_at")).isoformat(),
        })
    return out


def published_for_op_days(db: Session, days: list[date]) -> list[dict]:
    """Published entries (latest REV of each month) whose operational day is in `days`."""
    months = sorted({(d.year, d.month) for d in days} |
                    {((d + timedelta(days=1)).year, (d + timedelta(days=1)).month) for d in days})
    want = {d.isoformat() for d in days}
    out = []
    for y, m in months:
        p = get_plan(db, y, m, create=False)
        if not p:
            continue
        snap, v = published_entries(db, p)
        for e in snap:
            if entry_op_day(e["date"], e.get("start_at")).isoformat() in want:
                out.append(e | {"revision": v.revision})
    out.sort(key=lambda e: (e["start_at"] is None, e["start_at"] or "", e["date"], e["title_th"]))
    return out


def overlaps_for(entries: list[dict]) -> list:
    return find_overlaps(entries)
