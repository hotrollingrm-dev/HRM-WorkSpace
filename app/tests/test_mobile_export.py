import csv
import io
from datetime import datetime, timedelta

from conftest import needs_company_data
from hrm.services.mobile_export import COLUMNS
from hrm.timeutil import TZ, op_day_of


def _item(client):
    cat = client.post("/api/categories", json={"name_th": "หมวดทดสอบ"}).json()
    sub = client.post("/api/subcategories", json={"category_id": cat["id"], "name_th": "ย่อยทดสอบ"}).json()
    return client.post("/api/items", json={"subcategory_id": sub["id"], "name_th": "งานทดสอบมือถือ"}).json()


def _rows(client):
    r = client.get("/api/mobile-file")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    text = r.content.decode("utf-8")
    assert text.startswith("﻿")                         # BOM for Excel
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def test_mobile_file_has_only_published_work_for_next_8_days(client):
    today = op_day_of(datetime.now(TZ))
    it = _item(client)
    d0, d9 = today.isoformat(), (today + timedelta(days=9)).isoformat()
    for d in (d0, d9):
        client.post(f"/api/plans/{d[:4]}/{int(d[5:7])}/entries", json={"dates": [d], "work_item_id": it["id"]}).raise_for_status()
    rows = _rows(client)
    assert list(rows[0].keys()) == COLUMNS and rows[0]["type"] == "meta"
    assert not [r for r in rows if r["type"] == "task"]                  # draft is never exported
    for ym in {(d0[:4], d0[5:7]), (d9[:4], d9[5:7])}:
        client.post(f"/api/plans/{ym[0]}/{int(ym[1])}/publish", json={"note": "t"})
    tasks = [r for r in _rows(client) if r["type"] == "task"]
    assert [(t["date"], t["title"], t["status"]) for t in tasks] == [(d0, "งานทดสอบมือถือ", "แผน")]   # day 9 is outside the window


def test_mobile_file_needs_login(client):
    from fastapi.testclient import TestClient
    assert TestClient(client.app).get("/api/mobile-file").status_code == 401


@needs_company_data
def test_mobile_file_never_contains_employee_names(client):
    pv = client.post("/api/roster/preview").json()
    client.post(f"/api/roster/{pv['id']}/commit")
    names = [e["name"] for e in client.get("/api/employees").json()]
    assert names
    text = client.get("/api/mobile-file").content.decode("utf-8")
    assert not [n for n in names if n and n in text]
    shifts = [r for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))) if r["type"] == "shift"]
    assert shifts and all(set(r["start"] + r["end"] + r["shift"]) <= set("ABC") for r in shifts)
