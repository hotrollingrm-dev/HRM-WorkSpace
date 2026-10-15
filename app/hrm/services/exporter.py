"""Export a month into the original HRM Work Management template layout.

Strategy (ARCHITECTURE §5): open the template read-only, keep sheet `10` as layout
prototype, rebuild only rows 7–28 (A:AS) using the template's own cell styles,
leave every other part (title formulas, headers, CF, DV, widths, print setup) intact.
"""
from __future__ import annotations

from copy import copy
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..models import (Category, Employee, Holiday, PlanRow, Setting, Subcategory, WorkItem,
                      jload, now_iso)
from ..timeutil import parse_dt
from .plans import active_entries, entry_dict, get_plan, progress_map, published_entries

FIRST_ROW, LAST_ROW = 7, 28          # maintenance plan body (22 rows)
STAFF_ROWS = range(33, 45)           # shift working body (12 rows)
COL_LAST = 45                        # AS
DAY1_COL = 13                        # M = day 1 ; J,K,L = previous month's last 3 days
HOLIDAY_ROWS = range(5, 28)          # AU5:AV27


class ExportError(ValueError):
    pass


def _rows_for_plan(db: Session, plan) -> list[WorkItem]:
    rows = list(db.scalars(select(PlanRow).where(PlanRow.plan_id == plan.id)))
    items = [db.get(WorkItem, r.work_item_id) for r in rows]
    items = [i for i in items if i is not None]

    def key(w: WorkItem):
        s = w.subcategory
        return (s.category.sort_order, s.category_id, s.sort_order, s.id, w.sort_order, w.id)
    return sorted(items, key=key)


def _entries(db: Session, plan, source: str) -> tuple[list[dict], int, bool]:
    if source == "draft":
        return [entry_dict(e) for e in active_entries(db, plan.id)], plan.current_revision, True
    snap, v = published_entries(db, plan)
    if not v:
        raise ExportError("เดือนนี้ยังไม่มีแผนที่ Publish — เลือก 'ส่งออกฉบับร่าง' หรือ Publish ก่อน")
    return snap, v.revision, False


def _mark_setting(db: Session) -> dict:
    s = db.get(Setting, "export_mark_mode")
    return jload(s.value_json) if s else {"planned": "●", "completed": "✔"}


def export_month(db: Session, year: int, month: int, source: str = "published",
                 out_dir: Path | None = None) -> Path:
    if not config.TEMPLATE_PATH.exists():
        raise ExportError(f"ไม่พบไฟล์ Template: {config.TEMPLATE_PATH}")
    plan = get_plan(db, year, month, create=False)
    if not plan:
        raise ExportError("ยังไม่มีแผนของเดือนนี้")
    entries, rev, is_draft = _entries(db, plan, source)
    marks = _mark_setting(db)

    # previous month (for J:L)
    first = date(year, month, 1)
    prev_days = [first - timedelta(days=i) for i in (3, 2, 1)]
    prev_entries: list[dict] = []
    pp = get_plan(db, prev_days[0].year, prev_days[0].month, create=False)
    if pp:
        try:
            prev_entries = _entries(db, pp, source)[0]
        except ExportError:
            prev_entries = []

    all_entries = entries + prev_entries
    prog = progress_map(db, [e["uid"] for e in all_entries])
    items = _rows_for_plan(db, plan)

    wb = openpyxl.load_workbook(config.TEMPLATE_PATH)
    proto_name = config.TEMPLATE_SHEET
    for n in list(wb.sheetnames):
        if n != proto_name:
            del wb[n]
    ws = wb[proto_name]
    ws.title = str(month)

    # ---- capture prototype styles BEFORE touching the body ----
    proto = {
        "cream": {c: copy(ws.cell(FIRST_ROW, c)._style) for c in range(1, COL_LAST + 1)},
        "white": {c: copy(ws.cell(12, c)._style) for c in range(1, COL_LAST + 1)},
    }
    proto["white"][2] = copy(proto["cream"][2])   # B12 is a merged child (no alignment) in the template
    bottom = {c: copy(ws.cell(LAST_ROW, c).border) for c in range(1, COL_LAST + 1)}
    a_fills = [copy(ws.cell(r, 1).fill) for r in (7, 12)]
    b_fills = [copy(ws.cell(r, 2).fill) for r in (7, 24, 25, 28)]
    c_fills = [copy(ws.cell(r, 3).fill) for r in (7, 12, 15, 16, 17, 18, 24, 25, 28)]

    for rng in [m for m in ws.merged_cells.ranges
                if m.min_row >= FIRST_ROW and m.max_row <= LAST_ROW and m.max_col <= 9]:
        ws.unmerge_cells(str(rng))

    ws["D2"] = datetime(year, month, 1)
    status_txt = "ฉบับร่าง (ยังไม่ Publish)" if is_draft else "Published"
    ws["F2"] = f"REV.{rev:02d}  ·  {status_txt}  ·  ส่งออก {now_iso()[:16].replace('T', ' ')}  ·  HRM WorkSpace"

    # ---- group rows: (category → subcategory) ----
    main_items, overflow_items = items[:LAST_ROW - FIRST_ROW + 1], items[LAST_ROW - FIRST_ROW + 1:]
    by_item: dict[int, dict[date, list[dict]]] = {}
    for e in all_entries:
        if e.get("work_item_id"):
            by_item.setdefault(e["work_item_id"], {}).setdefault(date.fromisoformat(e["date"]), []).append(e)

    # Template convention: "No." = contiguous run of same category + same frequency label
    group_idx = -1
    last_key = None
    cat_idx = {}
    row_meta = []   # (row, item, group_idx)
    for i, w in enumerate(main_items):
        k = (w.subcategory.category_id, w.frequency_label)
        if k != last_key:
            group_idx += 1
            last_key = k
        cat_idx.setdefault(w.subcategory.category_id, len(cat_idx))
        row_meta.append((FIRST_ROW + i, w, group_idx))

    for r in range(FIRST_ROW, LAST_ROW + 1):
        meta = next((m for m in row_meta if m[0] == r), None)
        band = "cream" if (meta and meta[2] % 2 == 0) or not meta else "white"
        if not meta:
            band = "white"
        for c in range(1, COL_LAST + 1):
            cell = ws.cell(r, c)
            cell._style = copy(proto[band][c])
            if r == LAST_ROW:
                cell.border = copy(bottom[c])
            if c <= COL_LAST and c != 45:
                cell.value = None
        ws.cell(r, 45).value = f'=COUNTIF($M{r}:$AQ{r},"✔")'
        if meta:
            _, w, g = meta
            ws.cell(r, 1).fill = copy(a_fills[g % 2])
            ws.cell(r, 2).fill = copy(b_fills[cat_idx[w.subcategory.category_id] % len(b_fills)])
            ws.cell(r, 3).fill = copy(c_fills[g % len(c_fills)])

    def merge_runs(col_from: int, col_to: int, keyf):
        """Merge vertical runs of equal key; write value on first row of the run."""
        i = 0
        while i < len(row_meta):
            j = i
            k = keyf(row_meta[i])
            while j + 1 < len(row_meta) and keyf(row_meta[j + 1]) == k:
                j += 1
            r0, r1 = row_meta[i][0], row_meta[j][0]
            yield r0, r1, row_meta[i]
            if r1 > r0 or col_to > col_from:
                ws.merge_cells(start_row=r0, start_column=col_from, end_row=r1, end_column=col_to)
            i = j + 1

    for r0, r1, (_, w, g) in list(merge_runs(1, 1, lambda m: m[2])):
        ws.cell(r0, 1).value = g + 1
    for r0, r1, (_, w, g) in list(merge_runs(2, 2, lambda m: m[1].subcategory.category_id)):
        c = w.subcategory.category
        ws.cell(r0, 2).value = c.export_label or (c.name_th + (f"\n{c.name_jp}" if c.name_jp else ""))
    for r0, r1, (_, w, g) in list(merge_runs(3, 3, lambda m: m[2])):
        ws.cell(r0, 3).value = w.frequency_label or None
    for (r, w, g) in row_meta:
        ws.cell(r, 4).value = w.name_th
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=7)
    for r0, r1, (_, w, g) in list(merge_runs(8, 9, lambda m: (m[2], m[1].location or f"_{m[0]}"))):
        ws.cell(r0, 8).value = w.location or None
        if w.location:
            f = copy(ws.cell(r0, 8).font)
            f.b = True
            ws.cell(r0, 8).font = f
    # blank rows keep the template's D:G and H:I merges
    for r in range(FIRST_ROW + len(row_meta), LAST_ROW + 1):
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=7)
        ws.merge_cells(start_row=r, start_column=8, end_row=r, end_column=9)

    # ---- day marks ----
    day_cols = {first + timedelta(days=i): DAY1_COL + i for i in range(31)
                if (first + timedelta(days=i)).month == month}
    day_cols.update({d: 10 + i for i, d in enumerate(prev_days)})
    for (r, w, g) in row_meta:
        planned = 0
        for d, es in by_item.get(w.id, {}).items():
            col = day_cols.get(d)
            if not col:
                continue
            live = [e for e in es if prog.get(e["uid"], {}).get("status") != "cancelled"]
            if not live:
                continue
            done = all(prog.get(e["uid"], {}).get("status") == "completed" for e in live)
            ws.cell(r, col).value = marks["completed"] if done else marks["planned"]
            if d.month == month:
                planned += 1
        ws.cell(r, 44).value = planned or None       # AR แผน Target (Q-EX2)

    # ---- shift section (rows 33–44): staff master; day codes stay blank until the
    #      group roster (PDF) is imported and confirmed. The template's day cells carry
    #      *static* fills of the old roster pattern → reset to the row's neutral band.
    team_fill = {"A": copy(ws.cell(33, 8).fill), "B": copy(ws.cell(37, 8).fill), "C": copy(ws.cell(41, 8).fill)}
    from ..models import ShiftDay
    lo, hi = min(day_cols).isoformat(), max(day_cols).isoformat()
    roster: dict[str, dict] = {}
    for sd in db.scalars(select(ShiftDay).where(ShiftDay.date >= lo, ShiftDay.date <= hi)):
        roster.setdefault(sd.team, {})[date.fromisoformat(sd.date)] = sd.code
    staff = list(db.scalars(select(Employee).where(Employee.active.is_(True))
                            .order_by(Employee.team, Employee.sort_order, Employee.id)))
    for i, r in enumerate(STAFF_ROWS):
        neutral = copy(ws.cell(r, 3).fill)
        for c in [2, 3, 7, 8, 9] + list(range(10, 44)):
            if not isinstance(ws.cell(r, c), openpyxl.cell.cell.MergedCell):
                ws.cell(r, c).value = None
                if c == 8 or c >= 10:
                    ws.cell(r, c).fill = copy(neutral)
        if i < len(staff) and staff[i].team in roster:
            for d, col in day_cols.items():
                code = roster[staff[i].team].get(d)
                if code in ("D", "N"):          # Template DV allows D / N / OT; H & S stay blank (as in the template)
                    ws.cell(r, col).value = code
        if i < len(staff):
            e = staff[i]
            code = int(e.code) if e.code.isdigit() else e.code or None
            ws.cell(r, 2).value, ws.cell(r, 3).value, ws.cell(r, 7).value = code, e.name, e.nickname or None
            ws.cell(r, 8).value, ws.cell(r, 9).value = e.team, e.position or None
            ws.cell(r, 8).fill = copy(team_fill.get(e.team, neutral))
    if not staff:
        ws.cell(33, 3).value = "[รอไฟล์รายชื่อพนักงาน]"
    overflow_staff = staff[len(STAFF_ROWS):]

    # ---- holidays table (outside print area, drives CF) ----
    hols = list(db.scalars(select(Holiday).where(Holiday.date.like(f"{year}-%")).order_by(Holiday.date)))
    for i, r in enumerate(HOLIDAY_ROWS):
        h = hols[i] if i < len(hols) else None
        ws.cell(r, 47).value = datetime.fromisoformat(h.date) if h else None
        ws.cell(r, 48).value = h.name_th if h else None
    ws.cell(4, 47).value = f"วันหยุดนักขัตฤกษ์ {year + 543} / {year}  (จากระบบ)"

    # ---- Daily Detail sheet: imported/ad-hoc entries + overflow rows ----
    _detail_sheet(wb, db, year, month, entries, prog, rev, is_draft, overflow_items, hols, overflow_staff)

    wb.active = 0
    out_dir = out_dir or config.EXPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"HRM_Work_Management_{year}-{month:02d}_REV{rev:02d}{'_DRAFT' if is_draft else ''}.xlsx"
    path = out_dir / name
    wb.save(path)
    return path


def _detail_sheet(wb, db, year, month, entries, prog, rev, is_draft, overflow_items, hols, overflow_staff):
    ds = wb.create_sheet("Daily Detail")
    thin = Side(style="thin", color="FFB7C4D3")
    head_fill = PatternFill("solid", fgColor="FFBAD3EC")
    f_head = Font(name="Tahoma", size=9.5, bold=True, color="FF1F3864")
    f_body = Font(name="Tahoma", size=9.5, color="FF1A1A1A")
    ds["A1"] = f"Daily Detail — {year}-{month:02d}  ·  REV.{rev:02d}{'  ·  ฉบับร่าง' if is_draft else ''}"
    ds["A1"].font = Font(name="Tahoma", size=13, bold=True, color="FF1F3864")
    ds["A2"] = "รายการที่ไม่อยู่ในตารางหลัก: งานนำเข้า (ประชุม/กิจกรรม), งานเฉพาะกิจ และงานที่เกิน 22 แถว"
    ds["A2"].font = Font(name="Tahoma", size=9, color="FF8A6200")
    cols = ["วันที่", "วัน", "เริ่ม", "สิ้นสุด", "ช่วง", "หมวด", "งาน", "สถานที่", "MBO", "หมายเหตุ",
            "สถานะ", "แหล่งที่มา"]
    widths = [11, 5, 7, 7, 8, 16, 52, 14, 9, 36, 13, 20]
    for i, (h, w) in enumerate(zip(cols, widths), 1):
        c = ds.cell(4, i, h)
        c.font, c.fill = f_head, head_fill
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        ds.column_dimensions[L(i)].width = w
    cats = {c.id: c.name_th for c in db.scalars(select(Category))}
    overflow_ids = {w.id for w in overflow_items}
    th_wd = ["จ", "อ", "พ", "พฤ", "ศ", "ส", "อา"]
    slot_th = {"morning": "เช้า", "afternoon": "บ่าย", "other": "อื่นๆ"}
    status_th = {"planned": "แผน", "in_progress": "กำลังทำ", "on_hold": "พักไว้",
                 "pending_review": "รอตรวจ", "completed": "เสร็จ", "cancelled": "ยกเลิก"}
    rows = [e for e in entries if not e.get("work_item_id") or e["work_item_id"] in overflow_ids]
    rows.sort(key=lambda e: (e["date"], e.get("start_at") or "99", e["title_th"]))
    r = 5
    for e in rows:
        d = date.fromisoformat(e["date"])
        st = parse_dt(e["start_at"]).strftime("%H:%M") if e.get("start_at") else "—"
        en = parse_dt(e["end_at"]) if e.get("end_at") else None
        en_s = (en.strftime("%H:%M") + (" (+1)" if en.date() != d else "")) if en else "—"
        vals = [d, th_wd[d.weekday()], st, en_s, slot_th.get(e.get("time_slot") or "", ""),
                cats.get(e.get("category_id"), ""), e["title_th"], e.get("location") or "",
                e.get("mbo_ref") or "", e.get("notes") or "",
                status_th.get(prog.get(e["uid"], {}).get("status", "planned"), ""),
                e.get("source_ref") or e.get("source_type")]
        for i, v in enumerate(vals, 1):
            c = ds.cell(r, i, v)
            c.font = f_body
            c.border = Border(bottom=Side(style="hair", color="FFC9D3DD"))
            c.alignment = Alignment(vertical="top", wrap_text=i in (7, 10))
        ds.cell(r, 1).number_format = "dd/mm/yyyy"
        r += 1
    if not rows:
        ds.cell(5, 1, "— ไม่มีรายการ —").font = f_body
    if not hols:
        ds.cell(r + 1, 1, f"⚠ ไม่มีข้อมูลวันหยุดของปี {year} ในระบบ — ตารางวันหยุด AU5:AV27 ว่าง").font = \
            Font(name="Tahoma", size=9, color="FFB00000")
    if overflow_staff:
        ds.cell(r + 2, 1, f"⚠ พนักงานเกิน 12 แถวของแบบฟอร์ม: " + ", ".join(f"{e.name} ({e.team})" for e in overflow_staff)).font = \
            Font(name="Tahoma", size=9, color="FFB00000")
    ds.freeze_panes = "A5"
    ds.page_setup.orientation = "landscape"
    ds.page_setup.fitToWidth = 1
    ds.sheet_properties.pageSetUpPr.fitToPage = True
    ds.page_setup.fitToHeight = 0
