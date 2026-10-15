import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

APP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP))

from hrm import config  # noqa: E402

_NAME = "Monthly schedule 2026.04 - 2027.03 Rev00.xlsx"
SCHEDULE = next((p for p in (APP / "company_data" / _NAME, APP.parent / "source_files" / _NAME) if p.exists()),
                APP / "company_data" / _NAME)

# Company files are not in Git. Tests that need them are skipped on machines without them.
HAS_TEMPLATE = config.TEMPLATE_PATH.exists()
HAS_SCHEDULE = SCHEDULE.exists()
HAS_MASTER = (config.COMPANY_DIR / "master_seed.json").exists()
HAS_ROSTER = (config.COMPANY_DIR / "roster_codes.json").exists()
needs_company_data = pytest.mark.skipif(not (HAS_TEMPLATE and HAS_SCHEDULE and HAS_MASTER and HAS_ROSTER),
                                        reason="company_data/ not present on this machine")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "EXPORT_DIR", tmp_path / "exports")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "admin123")
    from hrm.main import create_app
    app = create_app(f"sqlite:///{tmp_path / 't.db'}")
    c = TestClient(app)
    r = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    return c


def user_client(client, role, name=None):
    name = name or f"u_{role}"
    r = client.post("/api/users", json={"username": name, "display_name": name, "role": role, "password": "pass1234"})
    assert r.status_code == 200, r.text
    c = TestClient(client.app)
    assert c.post("/api/auth/login", json={"username": name, "password": "pass1234"}).status_code == 200
    return c


def items(client):
    return [i for c in client.get("/api/master").json() for s in c["subcategories"] for i in s["items"]]


def import_schedule(client, year=2026):
    with open(SCHEDULE, "rb") as f:
        r = client.post("/api/imports", files={"file": (SCHEDULE.name, f)}, data={"year": str(year)})
    assert r.status_code == 200, r.text
    return r.json()
