from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .auth import (COOKIE, create_session, current_user, hash_password, require,
                   verify_password)
from .db import get_db, init_engine, session_scope
from .models import (ROLES, TEAMS, Category, Employee, Holiday, ImportBatch, ImportRow, MonthlyPlan,
                     PlanEntry, PlanRow, PlanVersion, SessionToken, Setting,
                     Subcategory, User, WorkItem, audit, jdump, jload)
from .seed import seed
from .services import exporter, importer, roster as R
from .services import plans as P
from .timeutil import TimeError, build_range, month_days, op_day_window


def create_app(db_url: str | None = None, *, seed_master: bool = True) -> FastAPI:
    config.ensure_dirs()
    init_engine(db_url)
    with session_scope() as db:
        pw = seed(db, with_master=seed_master)
        if pw:
            # Shown once in the console and kept in a local file so it is not lost when the window closes.
            (config.DATA_DIR / "FIRST_ADMIN_PASSWORD.txt").write_text(
                f"HRM WorkSpace — first admin login\nuser: {config.ADMIN_USERNAME}\npassword: {pw}\n\n"
                "เข้าสู่ระบบแล้วเปลี่ยนรหัสผ่านที่ ตั้งค่า → ผู้ใช้ → เปลี่ยนรหัสผ่านของฉัน แล้วลบไฟล์นี้\n", encoding="utf-8")
            print(f"\n  First run — admin user: {config.ADMIN_USERNAME}  password: {pw}\n")

    app = FastAPI(title="HRM WorkSpace", version="0.1.0-m1")

    @app.exception_handler(P.PlanError)
    @app.exception_handler(importer.ImportError_)
    @app.exception_handler(exporter.ExportError)
    @app.exception_handler(R.RosterError)
    @app.exception_handler(TimeError)
    async def _domain_error(_req, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    register_routes(app)
    app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")
    return app


# ------------------------------------------------------------------ schemas
class LoginIn(BaseModel):
    username: str
    password: str


class CategoryIn(BaseModel):
    name_th: str = Field(min_length=1, max_length=200)
    name_jp: str | None = None
    color: str = "#64748B"
    code: str = ""
    sort_order: int | None = None
    active: bool = True


class SubIn(BaseModel):
    category_id: int
    name_th: str = Field(min_length=1, max_length=200)
    name_jp: str | None = None
    sort_order: int | None = None
    active: bool = True


class ItemIn(BaseModel):
    subcategory_id: int
    name_th: str = Field(min_length=1, max_length=200)
    name_jp: str | None = None
    code: str = ""
    frequency_label: str = ""
    location: str = ""
    default_duration_min: int | None = None
    sort_order: int | None = None
    active: bool = True


class EntriesIn(BaseModel):
    dates: list[str]
    work_item_id: int | None = None
    category_id: int | None = None
    title_th: str | None = None
    shift: str | None = None
    start_time: str | None = None      # HH:MM, applied to each date
    end_time: str | None = None
    duration_min: int | None = None
    location: str = ""
    notes: str = ""


class EntryPatch(BaseModel):
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    clear_time: bool = False
    shift: str | None = None
    title_th: str | None = None
    location: str | None = None
    notes: str | None = None


class ToggleIn(BaseModel):
    work_item_id: int
    date: str


class RowIn(BaseModel):
    work_item_ids: list[int]


class PublishIn(BaseModel):
    note: str = ""


class ProgressIn(BaseModel):
    status: str
    note: str = ""


class ImportRowPatch(BaseModel):
    action: str | None = None
    title: str | None = None
    date: str | None = None
    location: str | None = None


class ExportIn(BaseModel):
    year: int
    month: int
    source: str = "published"


class UserIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    display_name: str
    role: str
    password: str = Field(min_length=6)


class UserPatch(BaseModel):
    display_name: str | None = None
    role: str | None = None
    password: str | None = None
    active: bool | None = None


# ------------------------------------------------------------------ helpers
def user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "display_name": u.display_name,
            "role": u.role, "active": u.active}


def cat_out(c: Category) -> dict:
    return {"id": c.id, "code": c.code, "name_th": c.name_th, "name_jp": c.name_jp, "color": c.color,
            "sort_order": c.sort_order, "active": c.active, "is_schedule": c.is_schedule,
            "export_label": c.export_label,
            "source_ref": c.source_ref}


def sub_out(s: Subcategory) -> dict:
    return {"id": s.id, "category_id": s.category_id, "name_th": s.name_th, "name_jp": s.name_jp,
            "sort_order": s.sort_order, "active": s.active, "source_ref": s.source_ref}


def item_out(w: WorkItem) -> dict:
    return {"id": w.id, "subcategory_id": w.subcategory_id, "code": w.code, "name_th": w.name_th,
            "name_jp": w.name_jp, "frequency_label": w.frequency_label, "location": w.location,
            "default_duration_min": w.default_duration_min, "sort_order": w.sort_order,
            "active": w.active, "source_ref": w.source_ref}


def master_tree(db: Session) -> list[dict]:
    out = []
    for c in db.scalars(select(Category).order_by(Category.sort_order, Category.id)):
        cd = cat_out(c)
        cd["subcategories"] = []
        for s in sorted(c.subcategories, key=lambda s: (s.sort_order, s.id)):
            sd = sub_out(s)
            sd["items"] = [item_out(w) for w in sorted(s.items, key=lambda w: (w.sort_order, w.id))]
            cd["subcategories"].append(sd)
        out.append(cd)
    return out


def get_setting(db: Session, key: str):
    s = db.get(Setting, key)
    return jload(s.value_json) if s else None


def _next_sort(db, model, **filt) -> int:
    q = select(model.sort_order)
    for k, v in filt.items():
        q = q.where(getattr(model, k) == v)
    vals = list(db.scalars(q))
    return (max(vals) + 10) if vals else 0


def _entry(db: Session, uid: str) -> PlanEntry:
    e = db.scalar(select(PlanEntry).where(PlanEntry.uid == uid, PlanEntry.deleted_at.is_(None)))
    if not e:
        raise HTTPException(404, "ไม่พบรายการ")
    return e


def shift_info(db: Session) -> dict:
    """Team lists only. Which team works D/N today needs the group calendar (PDF, not yet imported).
    Scheduled ≠ present: nothing here states attendance."""
    staff = list(db.scalars(select(Employee).where(Employee.active.is_(True)).order_by(Employee.team, Employee.sort_order)))
    teams: dict[str, list] = {}
    for e in staff:
        teams.setdefault(e.team, []).append({"name": e.name, "nickname": e.nickname, "position": e.position})
    if not staff:
        return {"status": "pending_roster", "teams": {}, "message": "รอไฟล์รายชื่อพนักงาน"}
    return {"status": "pending_calendar", "teams": teams,
            "message": f"มีรายชื่อ {len(staff)} คนแล้ว — รอนำเข้าตารางกะ 3 Group เพื่อบอกทีมที่เข้ากะ"}


def plan_view(db: Session, year: int, month: int) -> dict:
    plan = P.get_plan(db, year, month)
    lk = P.category_lookup(db)
    entries = P.decorate(db, [P.entry_dict(e) for e in P.active_entries(db, plan.id)], lk)
    rows = [r.work_item_id for r in db.scalars(select(PlanRow).where(PlanRow.plan_id == plan.id))]
    versions = [{"id": v.id, "revision": v.revision, "published_at": v.published_at,
                 "note": v.note, "diff": jload(v.diff_json),
                 "published_by": (db.get(User, v.published_by).display_name if v.published_by else None)}
                for v in db.scalars(select(PlanVersion).where(PlanVersion.plan_id == plan.id)
                                    .order_by(PlanVersion.revision.desc()))]
    days = month_days(year, month)
    hols = {h.date: h.name_th for h in db.scalars(select(Holiday).where(
        Holiday.date >= days[0].isoformat(), Holiday.date <= days[-1].isoformat()))}
    shifts = R.month_codes(db, days[0], days[-1])
    return {"shifts": shifts,
            "plan": {"id": plan.id, "year": year, "month": month, "revision": plan.current_revision,
                     "last_published_at": plan.last_published_at, "draft_dirty": plan.draft_dirty},
            "rows": rows, "entries": entries, "versions": versions, "holidays": hols,
            "days": [d.isoformat() for d in days]}


# ------------------------------------------------------------------ routes
def register_routes(app: FastAPI) -> None:
    api = "/api"

    @app.get(api + "/health")
    def health():
        return {"ok": True, "template_found": config.TEMPLATE_PATH.exists()}

    # ---- auth
    @app.post(api + "/auth/login")
    def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
        u = db.scalar(select(User).where(User.username == body.username.strip()))
        if not u or not u.active or not verify_password(body.password, u.password_hash):
            raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        tok = create_session(db, u)
        response.set_cookie(COOKIE, tok, httponly=True, samesite="lax",
                            max_age=config.SESSION_HOURS * 3600)
        return user_out(u)

    @app.post(api + "/auth/logout")
    def logout(response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
        for s in db.scalars(select(SessionToken).where(SessionToken.user_id == user.id)):
            db.delete(s)
        db.commit()
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.post(api + "/me/password")
    def change_own_password(body: dict, db: Session = Depends(get_db), me: User = Depends(current_user)):
        if not verify_password(str(body.get("current", "")), me.password_hash):
            raise HTTPException(422, "รหัสผ่านเดิมไม่ถูกต้อง")
        new = str(body.get("new", ""))
        if len(new) < 6:
            raise HTTPException(422, "รหัสผ่านใหม่อย่างน้อย 6 ตัวอักษร")
        me.password_hash = hash_password(new)
        audit(db, me.id, "change_password", "user", me.id, {})
        db.commit()
        if me.role == "admin":
            (config.DATA_DIR / "FIRST_ADMIN_PASSWORD.txt").unlink(missing_ok=True)
        return {"ok": True}

    @app.get(api + "/me")
    def me(user: User = Depends(current_user)):
        return user_out(user)

    # ---- users
    @app.get(api + "/users")
    def users(db: Session = Depends(get_db), _: User = Depends(require("admin"))):
        return [user_out(u) for u in db.scalars(select(User).order_by(User.id))]

    @app.post(api + "/users")
    def add_user(body: UserIn, db: Session = Depends(get_db), me: User = Depends(require("admin"))):
        if body.role not in ROLES:
            raise HTTPException(422, "บทบาทไม่ถูกต้อง")
        if db.scalar(select(User).where(User.username == body.username)):
            raise HTTPException(409, "ชื่อผู้ใช้นี้มีแล้ว")
        u = User(username=body.username, display_name=body.display_name, role=body.role,
                 password_hash=hash_password(body.password))
        db.add(u)
        db.flush()
        audit(db, me.id, "create_user", "user", u.id, {"role": u.role})
        db.commit()
        return user_out(u)

    @app.patch(api + "/users/{uid}")
    def edit_user(uid: int, body: UserPatch, db: Session = Depends(get_db), me: User = Depends(require("admin"))):
        u = db.get(User, uid)
        if not u:
            raise HTTPException(404, "ไม่พบผู้ใช้")
        if body.role is not None:
            if body.role not in ROLES:
                raise HTTPException(422, "บทบาทไม่ถูกต้อง")
            u.role = body.role
        if body.display_name is not None:
            u.display_name = body.display_name
        if body.active is not None:
            if u.id == me.id and not body.active:
                raise HTTPException(422, "ปิดบัญชีตัวเองไม่ได้")
            u.active = body.active
        if body.password:
            if len(body.password) < 6:
                raise HTTPException(422, "รหัสผ่านอย่างน้อย 6 ตัวอักษร")
            u.password_hash = hash_password(body.password)
        audit(db, me.id, "update_user", "user", u.id, {"role": u.role, "active": u.active})
        db.commit()
        return user_out(u)

    # ---- master data
    @app.get(api + "/master")
    def master(db: Session = Depends(get_db), _: User = Depends(current_user)):
        return master_tree(db)

    @app.post(api + "/categories")
    def add_cat(body: CategoryIn, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        c = Category(**body.model_dump(exclude={"sort_order"}), created_by=me.id, updated_by=me.id,
                     sort_order=body.sort_order if body.sort_order is not None else _next_sort(db, Category))
        db.add(c)
        db.flush()
        audit(db, me.id, "create", "category", c.id, body.model_dump())
        db.commit()
        return cat_out(c)

    @app.patch(api + "/categories/{cid}")
    def edit_cat(cid: int, body: dict, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        c = db.get(Category, cid)
        if not c:
            raise HTTPException(404, "ไม่พบหมวด")
        for k in ("name_th", "name_jp", "color", "code", "sort_order", "active", "export_label"):
            if k in body:
                if k == "name_th" and not str(body[k]).strip():
                    raise HTTPException(422, "ชื่อหมวดห้ามว่าง")
                setattr(c, k, body[k] if k != "name_jp" else (body[k] or None))
        c.updated_by = me.id
        audit(db, me.id, "update", "category", c.id, body)
        db.commit()
        return cat_out(c)

    @app.post(api + "/subcategories")
    def add_sub(body: SubIn, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        if not db.get(Category, body.category_id):
            raise HTTPException(404, "ไม่พบหมวดหลัก")
        s = Subcategory(**body.model_dump(exclude={"sort_order"}), created_by=me.id, updated_by=me.id,
                        sort_order=body.sort_order if body.sort_order is not None
                        else _next_sort(db, Subcategory, category_id=body.category_id))
        db.add(s)
        db.flush()
        audit(db, me.id, "create", "subcategory", s.id, body.model_dump())
        db.commit()
        return sub_out(s)

    @app.patch(api + "/subcategories/{sid}")
    def edit_sub(sid: int, body: dict, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        s = db.get(Subcategory, sid)
        if not s:
            raise HTTPException(404, "ไม่พบหมวดย่อย")
        for k in ("name_th", "name_jp", "sort_order", "active", "category_id"):
            if k in body:
                if k == "category_id" and not db.get(Category, body[k]):
                    raise HTTPException(404, "ไม่พบหมวดหลักปลายทาง")
                if k == "name_th" and not str(body[k]).strip():
                    raise HTTPException(422, "ชื่อหมวดย่อยห้ามว่าง")
                setattr(s, k, body[k] if k != "name_jp" else (body[k] or None))
        s.updated_by = me.id
        audit(db, me.id, "update", "subcategory", s.id, body)
        db.commit()
        return sub_out(s)

    @app.post(api + "/items")
    def add_item(body: ItemIn, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        if not db.get(Subcategory, body.subcategory_id):
            raise HTTPException(404, "ไม่พบหมวดย่อย")
        w = WorkItem(**body.model_dump(exclude={"sort_order"}), created_by=me.id, updated_by=me.id,
                     sort_order=body.sort_order if body.sort_order is not None
                     else _next_sort(db, WorkItem, subcategory_id=body.subcategory_id))
        db.add(w)
        db.flush()
        audit(db, me.id, "create", "work_item", w.id, body.model_dump())
        db.commit()
        return item_out(w)

    @app.patch(api + "/items/{wid}")
    def edit_item(wid: int, body: dict, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        w = db.get(WorkItem, wid)
        if not w:
            raise HTTPException(404, "ไม่พบรายการงาน")
        for k in ("name_th", "name_jp", "code", "frequency_label", "location", "default_duration_min",
                  "sort_order", "active", "subcategory_id"):
            if k in body:
                if k == "subcategory_id" and not db.get(Subcategory, body[k]):
                    raise HTTPException(404, "ไม่พบหมวดย่อยปลายทาง")
                if k == "name_th" and not str(body[k]).strip():
                    raise HTTPException(422, "ชื่องานห้ามว่าง")
                setattr(w, k, body[k] if k != "name_jp" else (body[k] or None))
        w.updated_by = me.id
        audit(db, me.id, "update", "work_item", w.id, body)
        db.commit()
        return item_out(w)

    @app.post(api + "/master/reorder")
    def reorder(body: dict, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        model = {"category": Category, "subcategory": Subcategory, "item": WorkItem}.get(body.get("kind"))
        if not model:
            raise HTTPException(422, "kind ไม่ถูกต้อง")
        for i, oid in enumerate(body.get("ids", [])):
            o = db.get(model, oid)
            if o:
                o.sort_order = i * 10
        audit(db, me.id, "reorder", body["kind"], "", {"ids": body.get("ids")})
        db.commit()
        return {"ok": True}

    # ---- plans (draft)
    @app.get(api + "/plans/{year}/{month}")
    def plan(year: int, month: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
        v = plan_view(db, year, month)
        db.commit()
        return v

    @app.post(api + "/plans/{year}/{month}/entries")
    def add_entries(year: int, month: int, body: EntriesIn, db: Session = Depends(get_db),
                    me: User = Depends(require("leader"))):
        plan = P.get_plan(db, year, month)
        times = None
        if body.start_time:
            times = {}
            for d in body.dates:
                s, e, _ = build_range(d, body.start_time, body.end_time, body.duration_min)
                times[d] = (s, e)
        es = P.create_entries(db, me.id, plan, dates=body.dates, work_item_id=body.work_item_id,
                              category_id=body.category_id, title_th=body.title_th,
                              start_at_by_date=times, shift=body.shift, location=body.location,
                              notes=body.notes)
        db.commit()
        return {"created": [P.entry_dict(e) for e in es]}

    @app.patch(api + "/entries/{uid}")
    def patch_entry(uid: str, body: EntryPatch, db: Session = Depends(get_db),
                    me: User = Depends(require("leader"))):
        e = _entry(db, uid)
        ch = {k: v for k, v in body.model_dump().items()
              if v is not None and k in ("date", "shift", "title_th", "location", "notes")}
        if body.shift == "":
            ch["shift"] = None
        d = ch.get("date", e.date)
        if body.clear_time:
            ch["start_at"] = ch["end_at"] = None
        elif body.start_time:
            ch["start_at"], ch["end_at"], _ = build_range(d, body.start_time, body.end_time,
                                                          None if body.end_time else 60)
        elif "date" in ch and e.start_at:   # move date, keep clock times
            st = e.start_at[11:16]
            en = e.end_at[11:16]
            ch["start_at"], ch["end_at"], _ = build_range(d, st, en)
        P.update_entry(db, me.id, e, ch)
        db.commit()
        return P.entry_dict(e)

    @app.delete(api + "/entries/{uid}")
    def del_entry(uid: str, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        P.delete_entry(db, me.id, _entry(db, uid))
        db.commit()
        return {"ok": True}

    @app.post(api + "/plans/{year}/{month}/toggle")
    def toggle(year: int, month: int, body: ToggleIn, db: Session = Depends(get_db),
               me: User = Depends(require("leader"))):
        r = P.toggle_cell(db, me.id, P.get_plan(db, year, month), body.work_item_id, body.date)
        db.commit()
        return r

    @app.post(api + "/plans/{year}/{month}/rows")
    def add_rows(year: int, month: int, body: RowIn, db: Session = Depends(get_db),
                 me: User = Depends(require("leader"))):
        plan = P.get_plan(db, year, month)
        for wid in body.work_item_ids:
            if not db.get(WorkItem, wid):
                raise HTTPException(404, f"ไม่พบรายการงาน {wid}")
            P.ensure_row(db, plan, wid)
            db.flush()
        P.mark_dirty(plan)
        db.commit()
        return {"ok": True}

    @app.delete(api + "/plans/{year}/{month}/rows/{wid}")
    def del_row(year: int, month: int, wid: int, db: Session = Depends(get_db),
                me: User = Depends(require("leader"))):
        plan = P.get_plan(db, year, month)
        if any(e.work_item_id == wid for e in P.active_entries(db, plan.id)):
            raise HTTPException(422, "แถวนี้ยังมีงานในเดือน — ลบงานก่อน")
        r = db.scalar(select(PlanRow).where(PlanRow.plan_id == plan.id, PlanRow.work_item_id == wid))
        if r:
            db.delete(r)
        db.commit()
        return {"ok": True}

    @app.post(api + "/plans/{year}/{month}/copy-prior")
    def copy_prior(year: int, month: int, with_dates: bool = False, db: Session = Depends(get_db),
                   me: User = Depends(require("leader"))):
        r = P.copy_prior_month(db, me.id, P.get_plan(db, year, month), with_dates)
        db.commit()
        return r

    @app.get(api + "/plans/{year}/{month}/pending")
    def pending(year: int, month: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
        d = P.pending_diff(db, P.get_plan(db, year, month))
        db.commit()
        return d

    @app.post(api + "/plans/{year}/{month}/publish")
    def publish(year: int, month: int, body: PublishIn, db: Session = Depends(get_db),
                me: User = Depends(current_user)):          # ทุกบทบาท (ผู้ใช้ยืนยัน, Q-SY1)
        v = P.publish(db, me.id, P.get_plan(db, year, month), body.note)
        db.commit()
        return {"revision": v.revision, "published_at": v.published_at, "diff": jload(v.diff_json)}

    # ---- published / mobile
    @app.get(api + "/today")
    def today(d: str | None = None, db: Session = Depends(get_db), _: User = Depends(current_user)):
        from datetime import datetime as _dt
        from .timeutil import TZ, op_day_of
        now = _dt.now(TZ)
        day = date.fromisoformat(d) if d else op_day_of(now)
        lk = P.category_lookup(db)
        todays = P.decorate(db, P.published_for_op_days(db, [day]), lk)
        upcoming = P.decorate(db, P.published_for_op_days(db, [day + timedelta(days=i) for i in range(1, 8)]), lk)
        ws, we = op_day_window(day)
        return {"op_day": day.isoformat(), "window": [ws.isoformat(), we.isoformat()],
                "now": now.replace(microsecond=0).isoformat(),
                "entries": todays, "upcoming": upcoming,
                "overlaps": P.overlaps_for(todays),
                "bands": get_setting(db, "planning_bands"),
                "shift": R.shift_card(db, day, now),
                "holiday": (db.get(Holiday, day.isoformat()).name_th if db.get(Holiday, day.isoformat()) else None)}

    @app.post(api + "/progress/{uid}")
    def progress(uid: str, body: ProgressIn, db: Session = Depends(get_db), me: User = Depends(current_user)):
        if not db.scalar(select(PlanEntry).where(PlanEntry.uid == uid)):
            raise HTTPException(404, "ไม่พบรายการ")
        tp = P.set_progress(db, me, uid, body.status, body.note)
        db.commit()
        return {"uid": uid, "status": tp.status, "updated_at": tp.updated_at}

    # ---- import
    @app.post(api + "/imports")
    async def upload(file: UploadFile = File(...), year: int = Form(...), db: Session = Depends(get_db),
                     me: User = Depends(require("foreman"))):
        data = await file.read()
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(413, "ไฟล์ใหญ่เกิน 25 MB")
        b = importer.create_batch(db, me.id, file.filename or "upload.xlsx", data, year)
        (config.UPLOAD_DIR / f"batch{b.id}_{b.sha256[:12]}.xlsx").write_bytes(data)
        db.commit()
        return import_view(db, b)

    @app.get(api + "/imports")
    def imports(db: Session = Depends(get_db), _: User = Depends(require("leader"))):
        return [{"id": b.id, "filename": b.filename, "status": b.status, "uploaded_at": b.uploaded_at,
                 "target_year": b.target_year, "summary": jload(b.summary_json)}
                for b in db.scalars(select(ImportBatch).order_by(ImportBatch.id.desc()))]

    @app.get(api + "/imports/{bid}")
    def import_get(bid: int, db: Session = Depends(get_db), _: User = Depends(require("leader"))):
        b = db.get(ImportBatch, bid)
        if not b:
            raise HTTPException(404, "ไม่พบ batch")
        return import_view(db, b)

    @app.patch(api + "/import-rows/{rid}")
    def import_row(rid: int, body: ImportRowPatch, db: Session = Depends(get_db),
                   _: User = Depends(require("foreman"))):
        r = db.get(ImportRow, rid)
        if not r:
            raise HTTPException(404, "ไม่พบแถว")
        importer.update_row(db, r, body.model_dump(exclude_none=True))
        db.commit()
        return row_out(r)

    @app.post(api + "/imports/{bid}/commit")
    def import_commit(bid: int, db: Session = Depends(get_db), me: User = Depends(require("foreman"))):
        r = importer.commit_batch(db, me.id, db.get(ImportBatch, bid))
        db.commit()
        return r

    @app.post(api + "/imports/{bid}/revert")
    def import_revert(bid: int, db: Session = Depends(get_db), me: User = Depends(require("foreman"))):
        r = importer.revert_batch(db, me.id, db.get(ImportBatch, bid))
        db.commit()
        return r

    # ---- export
    @app.post(api + "/exports")
    def export(body: ExportIn, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        if body.source not in ("published", "draft"):
            raise HTTPException(422, "source ต้องเป็น published หรือ draft")
        path = exporter.export_month(db, body.year, body.month, body.source)
        audit(db, me.id, "export", "plan", f"{body.year}-{body.month:02d}", {"file": path.name})
        db.commit()
        return {"file": path.name, "url": f"/api/exports/file/{path.name}"}

    @app.get(api + "/exports/file/{name}")
    def export_file(name: str, _: User = Depends(require("leader"))):
        p = (config.EXPORT_DIR / name).resolve()
        if p.parent != config.EXPORT_DIR.resolve() or not p.exists():
            raise HTTPException(404, "ไม่พบไฟล์")
        return FileResponse(p, filename=name,
                            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ---- shift roster (3 groups)
    def roster_batch_out(b) -> dict:
        return {"id": b.id, "status": b.status, "source": b.source, "method": b.method, "created_at": b.created_at,
                "checks": jload(b.checks_json)}

    @app.get(api + "/roster")
    def roster_month(year: int, month: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
        days = month_days(year, month)
        from .models import RosterBatch, ShiftDay
        rows = list(db.scalars(select(ShiftDay).where(ShiftDay.date >= days[0].isoformat(), ShiftDay.date <= days[-1].isoformat())))
        last = db.scalar(select(RosterBatch).order_by(RosterBatch.id.desc()).limit(1))
        by_day: dict[str, dict] = {d.isoformat(): {} for d in days}
        for r in rows:
            by_day[r.date][r.team] = {"code": r.code, "fill": r.fill, "edited": r.manually_edited}
        return {"days": by_day,
                "times": get_setting(db, "official_roster_times"),
                "last_batch": roster_batch_out(last) if last else None}

    @app.post(api + "/roster/preview")
    def roster_preview(db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        b = R.create_preview(db, me.id)
        db.commit()
        out = roster_batch_out(b)
        out["data"] = jload(b.data_json)
        return out

    @app.post(api + "/roster/{bid}/commit")
    def roster_commit(bid: int, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        from .models import RosterBatch
        b = db.get(RosterBatch, bid)
        if not b:
            raise HTTPException(404, "ไม่พบ batch")
        r = R.commit(db, me.id, b)
        db.commit()
        return r

    @app.patch(api + "/roster/{d}/{team}")
    def roster_edit(d: str, team: str, body: dict, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        s_ = R.edit_day(db, me.id, d, team, body.get("code", ""))
        db.commit()
        return {"date": s_.date, "team": s_.team, "code": s_.code, "edited": True}

    # ---- employees (staff master)
    def emp_out(e: Employee) -> dict:
        return {"id": e.id, "code": e.code, "name": e.name, "nickname": e.nickname, "team": e.team,
                "position": e.position, "sort_order": e.sort_order, "active": e.active, "source_ref": e.source_ref}

    @app.get(api + "/employees")
    def employees(db: Session = Depends(get_db), _: User = Depends(current_user)):
        return [emp_out(e) for e in db.scalars(select(Employee).order_by(Employee.team, Employee.sort_order, Employee.id))]

    @app.post(api + "/employees")
    def add_employee(body: dict, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        name = " ".join(str(body.get("name", "")).split())
        if not name:
            raise HTTPException(422, "ต้องระบุชื่อ-สกุล")
        if body.get("team") not in TEAMS:
            raise HTTPException(422, "ทีมต้องเป็น A, B หรือ C")
        e = Employee(code=str(body.get("code", "")).strip(), name=name, nickname=str(body.get("nickname", "")).strip(),
                     team=body["team"], position=str(body.get("position", "")).strip(),
                     sort_order=_next_sort(db, Employee), created_by=me.id, updated_by=me.id)
        db.add(e)
        db.flush()
        audit(db, me.id, "create", "employee", e.id, {"team": e.team})
        db.commit()
        return emp_out(e)

    @app.patch(api + "/employees/{eid}")
    def edit_employee(eid: int, body: dict, db: Session = Depends(get_db), me: User = Depends(require("leader"))):
        e = db.get(Employee, eid)
        if not e:
            raise HTTPException(404, "ไม่พบพนักงาน")
        before = {"team": e.team, "position": e.position, "active": e.active}
        if "team" in body:
            if body["team"] not in TEAMS:
                raise HTTPException(422, "ทีมต้องเป็น A, B หรือ C")
            e.team = body["team"]
        for k in ("position", "nickname", "code"):
            if k in body:
                setattr(e, k, str(body[k] or "").strip())
        if "active" in body:
            e.active = bool(body["active"])
        if "sort_order" in body:
            e.sort_order = int(body["sort_order"])
        e.updated_by = me.id
        audit(db, me.id, "update", "employee", e.id,
              {"before": before, "after": {"team": e.team, "position": e.position, "active": e.active}})
        db.commit()
        return emp_out(e)

    # ---- settings
    @app.get(api + "/settings")
    def settings(db: Session = Depends(get_db), _: User = Depends(current_user)):
        return {s.key: jload(s.value_json) for s in db.scalars(select(Setting))}

    @app.put(api + "/settings/{key}")
    def put_setting(key: str, body: dict, db: Session = Depends(get_db), me: User = Depends(require("admin"))):
        if key not in ("planning_bands", "export_mark_mode"):
            raise HTTPException(422, "แก้ไขค่านี้ไม่ได้จากหน้าจอ (official_roster_times รอการยืนยัน)")
        if key == "export_mark_mode" and not ({body.get("planned"), body.get("completed")} <= {"●", "✔", "✖"}):
            raise HTTPException(422, "เครื่องหมายต้องเป็น ● ✔ ✖ ตาม Data validation ของ Template")
        s = db.get(Setting, key) or Setting(key=key)
        s.value_json = jdump(body)
        db.add(s)
        audit(db, me.id, "setting", "setting", key, body)
        db.commit()
        return body

    @app.get(api + "/holidays")
    def holidays(year: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
        return [{"date": h.date, "name_th": h.name_th, "source_ref": h.source_ref}
                for h in db.scalars(select(Holiday).where(Holiday.date.like(f"{year}-%")).order_by(Holiday.date))]


def row_out(r: ImportRow) -> dict:
    return {"id": r.id, "sheet": r.sheet, "cell_ref": r.cell_ref, "line_no": r.line_no, "raw_text": r.raw_text,
            "date": r.date, "start_at": r.start_at, "end_at": r.end_at, "title": r.title,
            "location": r.location, "mbo_ref": r.mbo_ref, "time_slot": r.time_slot,
            "issues": jload(r.issues_json), "action": r.action, "match_entry_uid": r.match_entry_uid,
            "entry_uid": r.entry_uid}


def import_view(db: Session, b: ImportBatch) -> dict:
    rows = list(db.scalars(select(ImportRow).where(ImportRow.batch_id == b.id).order_by(ImportRow.id)))
    return {"id": b.id, "filename": b.filename, "sha256": b.sha256, "status": b.status,
            "target_year": b.target_year, "uploaded_at": b.uploaded_at,
            "summary": jload(b.summary_json), "rows": [row_out(r) for r in rows]}
