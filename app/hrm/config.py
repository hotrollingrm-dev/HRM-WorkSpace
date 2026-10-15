"""Runtime configuration. Everything overridable by environment variables."""
from __future__ import annotations

import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent          # app/
PROJECT_DIR = APP_DIR.parent                               # HRM-WorkSpace/
DATA_DIR = Path(os.environ.get("HRM_DATA_DIR", APP_DIR / "data"))
EXPORT_DIR = DATA_DIR / "exports"
UPLOAD_DIR = DATA_DIR / "uploads"
WEB_DIR = APP_DIR / "web"

DB_URL = os.environ.get("HRM_DB_URL", f"sqlite:///{DATA_DIR / 'hrm.db'}")

# Company data (never committed to Git): template workbook, roster transcription, starting task list.
COMPANY_DIR = Path(os.environ.get("HRM_COMPANY_DIR", APP_DIR / "company_data"))
_TEMPLATE_CANDIDATES = [
    COMPANY_DIR / "เอกสาร HRM_Work_Management_20261.xlsx",
    PROJECT_DIR / "source_files" / "เอกสาร HRM_Work_Management_20261.xlsx",
]
# Original Excel template (read-only reference, never written)
TEMPLATE_PATH = Path(os.environ.get("HRM_TEMPLATE_PATH") or next(
    (p for p in _TEMPLATE_CANDIDATES if p.exists()), _TEMPLATE_CANDIDATES[0]))
TEMPLATE_SHEET = "10"   # sheet used as layout prototype (see FILE_AUDIT §1.2)

TZ_OFFSET = "+07:00"    # Asia/Bangkok, no DST
SESSION_HOURS = 24 * 14

# First-run admin. If unset a random password is generated and printed once.
ADMIN_USERNAME = os.environ.get("HRM_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("HRM_ADMIN_PASSWORD")


def ensure_dirs() -> None:
    for d in (DATA_DIR, EXPORT_DIR, UPLOAD_DIR):
        d.mkdir(parents=True, exist_ok=True)
