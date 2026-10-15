from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import (Boolean, ForeignKey, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def new_uid() -> str:
    return uuid.uuid4().hex


def jdump(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def jload(s):
    return json.loads(s) if s else None


ROLES = ("admin", "foreman", "leader", "viewer")
STATUSES = ("planned", "in_progress", "on_hold", "pending_review", "completed", "cancelled")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16), default="viewer")
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(32), default=now_iso)


class SessionToken(Base):
    __tablename__ = "sessions"
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[str] = mapped_column(String(32))


class _Audited:
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=now_iso)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[str] = mapped_column(String(32), default=now_iso, onupdate=now_iso)


class Category(_Audited, Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), default="")
    name_th: Mapped[str] = mapped_column(String(200))
    name_jp: Mapped[str | None] = mapped_column(String(200), nullable=True)
    color: Mapped[str] = mapped_column(String(9), default="#64748B")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_schedule: Mapped[bool] = mapped_column(Boolean, default=False)  # meetings/imported schedule
    export_label: Mapped[str | None] = mapped_column(String(200), nullable=True)  # exact text for Template col B
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subcategories: Mapped[list["Subcategory"]] = relationship(
        back_populates="category", order_by="Subcategory.sort_order")


class Subcategory(_Audited, Base):
    __tablename__ = "subcategories"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    name_th: Mapped[str] = mapped_column(String(200))
    name_jp: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[Category] = relationship(back_populates="subcategories")
    items: Mapped[list["WorkItem"]] = relationship(
        back_populates="subcategory", order_by="WorkItem.sort_order")


class WorkItem(_Audited, Base):
    __tablename__ = "work_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    subcategory_id: Mapped[int] = mapped_column(ForeignKey("subcategories.id"))
    code: Mapped[str] = mapped_column(String(32), default="")
    name_th: Mapped[str] = mapped_column(String(200))
    name_jp: Mapped[str | None] = mapped_column(String(200), nullable=True)
    frequency_label: Mapped[str] = mapped_column(String(64), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    default_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    subcategory: Mapped[Subcategory] = relationship(back_populates="items")


TEAMS = ("A", "B", "C")


class Employee(_Audited, Base):
    """Staff master. Seeded from Template 10!B33:I44 (user-approved 2026-10-15).
    Names are kept as in the source; team / position / active are editable."""
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), default="")
    name: Mapped[str] = mapped_column(String(200))
    nickname: Mapped[str] = mapped_column(String(64), default="")
    team: Mapped[str] = mapped_column(String(2), default="A")
    position: Mapped[str] = mapped_column(String(64), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)


class RosterBatch(Base):
    __tablename__ = "roster_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(300))
    method: Mapped[str] = mapped_column(String(300))
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String(32), default=now_iso)
    status: Mapped[str] = mapped_column(String(16), default="preview")   # preview / committed / reverted
    checks_json: Mapped[str] = mapped_column(Text, default="{}")
    data_json: Mapped[str] = mapped_column(Text, default="{}")            # {date: {team: [code, fill]}}


class ShiftDay(Base):
    """Group calendar: which code each team has on a date (scheduled, not attendance)."""
    __tablename__ = "shift_days"
    __table_args__ = (UniqueConstraint("date", "team"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    team: Mapped[str] = mapped_column(String(2))
    code: Mapped[str] = mapped_column(String(2))                 # D / N / H / S
    fill: Mapped[str | None] = mapped_column(String(16), nullable=True)   # special / substitution
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[str] = mapped_column(String(32), default=now_iso)


class MonthlyPlan(Base):
    __tablename__ = "monthly_plans"
    __table_args__ = (UniqueConstraint("year", "month"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    current_revision: Mapped[int] = mapped_column(Integer, default=0)
    last_published_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    draft_dirty: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(32), default=now_iso)


class PlanRow(Base):
    __tablename__ = "plan_rows"
    __table_args__ = (UniqueConstraint("plan_id", "work_item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("monthly_plans.id", ondelete="CASCADE"))
    work_item_id: Mapped[int] = mapped_column(ForeignKey("work_items.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class PlanEntry(_Audited, Base):
    __tablename__ = "plan_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, default=new_uid)
    plan_id: Mapped[int] = mapped_column(ForeignKey("monthly_plans.id", ondelete="CASCADE"))
    work_item_id: Mapped[int | None] = mapped_column(ForeignKey("work_items.id"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    title_th: Mapped[str] = mapped_column(String(500))
    title_jp: Mapped[str | None] = mapped_column(String(500), nullable=True)
    date: Mapped[str] = mapped_column(String(10), index=True)          # YYYY-MM-DD
    start_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    shift: Mapped[str | None] = mapped_column(String(2), nullable=True)  # D / N planning band
    time_slot: Mapped[str | None] = mapped_column(String(16), nullable=True)  # morning/afternoon/other (import)
    location: Mapped[str] = mapped_column(String(200), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    mbo_ref: Mapped[str] = mapped_column(String(64), default="")
    source_type: Mapped[str] = mapped_column(String(16), default="manual")
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    import_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_key: Mapped[str | None] = mapped_column(String(600), nullable=True, index=True)
    manually_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    original_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    deleted_at: Mapped[str | None] = mapped_column(String(32), nullable=True)


class PlanVersion(Base):
    __tablename__ = "plan_versions"
    __table_args__ = (UniqueConstraint("plan_id", "revision"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("monthly_plans.id", ondelete="CASCADE"))
    revision: Mapped[int] = mapped_column(Integer)
    published_at: Mapped[str] = mapped_column(String(32), default=now_iso)
    published_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="")
    snapshot_json: Mapped[str] = mapped_column(Text)
    diff_json: Mapped[str] = mapped_column(Text, default="{}")


class TaskProgress(Base):
    __tablename__ = "task_progress"
    entry_uid: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="planned")
    note: Mapped[str] = mapped_column(Text, default="")
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[str] = mapped_column(String(32), default=now_iso)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    target_year: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[str] = mapped_column(String(32), default=now_iso)
    status: Mapped[str] = mapped_column(String(16), default="preview")
    summary_json: Mapped[str] = mapped_column(Text, default="{}")


class ImportRow(Base):
    __tablename__ = "import_rows"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("import_batches.id", ondelete="CASCADE"), index=True)
    sheet: Mapped[str] = mapped_column(String(64))
    cell_ref: Mapped[str] = mapped_column(String(32))
    line_no: Mapped[int] = mapped_column(Integer, default=1)
    raw_text: Mapped[str] = mapped_column(Text)
    date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    start_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    mbo_ref: Mapped[str] = mapped_column(String(64), default="")
    time_slot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    issues_json: Mapped[str] = mapped_column(Text, default="[]")
    action: Mapped[str] = mapped_column(String(20), default="add")
    match_entry_uid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entry_uid: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Holiday(Base):
    __tablename__ = "holidays"
    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    name_th: Mapped[str] = mapped_column(String(200))
    source_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[str] = mapped_column(String(32), default=now_iso)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    detail_json: Mapped[str] = mapped_column(Text, default="{}")


def audit(db, user_id, action, entity, entity_id="", detail=None):
    db.add(AuditLog(user_id=user_id, action=action, entity=entity,
                    entity_id=str(entity_id), detail_json=jdump(detail or {})))
