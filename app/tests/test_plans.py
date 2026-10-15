import pytest
from conftest import needs_company_data, items, user_client


@needs_company_data
def test_master_crud_and_soft_delete(client):
    c = client.post("/api/categories", json={"name_th": "Safety", "color": "#C2417A"}).json()
    s = client.post("/api/subcategories", json={"category_id": c["id"], "name_th": "Patrol"}).json()
    w = client.post("/api/items", json={"subcategory_id": s["id"], "name_th": "WI patrol PF", "frequency_label": "1 ครั้ง/เดือน"}).json()
    assert client.patch(f"/api/items/{w['id']}", json={"name_th": "WI patrol PF (แก้)", "name_jp": ""}).json()["name_jp"] is None
    assert client.patch(f"/api/items/{w['id']}", json={"active": False}).json()["active"] is False
    tree = client.get("/api/master").json()
    found = [i for cc in tree for ss in cc["subcategories"] for i in ss["items"] if i["id"] == w["id"]]
    assert found and found[0]["name_th"].endswith("(แก้)")          # still present (soft)
    r = client.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-05"], "work_item_id": w["id"]})
    assert r.status_code == 422                                      # inactive item can't be planned
    assert client.patch(f"/api/items/{w['id']}", json={"name_th": "  "}).status_code == 422


@needs_company_data
def test_seed_from_template_is_traceable(client):
    its = items(client)
    assert len(its) == 22
    assert all(i["source_ref"].startswith("Template 10!D") for i in its)
    assert all(i["name_jp"] is None for i in its)                    # no invented Japanese


@needs_company_data
def test_multi_date_quick_entry_saves_once_on_correct_dates(client):
    w = items(client)[0]
    dates = ["2026-10-01", "2026-10-08", "2026-10-15", "2026-10-29"]
    r = client.post("/api/plans/2026/10/entries", json={"dates": dates, "work_item_id": w["id"], "shift": "D"})
    assert r.status_code == 200
    v = client.get("/api/plans/2026/10").json()
    got = sorted(e["date"] for e in v["entries"] if e["work_item_id"] == w["id"])
    assert got == dates
    assert all(e["shift"] == "D" and e["start_at"] is None for e in v["entries"])
    assert w["id"] in v["rows"]
    # rejected: duplicate dates / date outside month
    assert client.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-02", "2026-10-02"], "work_item_id": w["id"]}).status_code == 422
    assert client.post("/api/plans/2026/10/entries", json={"dates": ["2026-11-02"], "work_item_id": w["id"]}).status_code == 422


@needs_company_data
def test_toggle_cell(client):
    w = items(client)[3]
    r = client.post("/api/plans/2026/10/toggle", json={"work_item_id": w["id"], "date": "2026-10-20"}).json()
    assert r["action"] == "added"
    r = client.post("/api/plans/2026/10/toggle", json={"work_item_id": w["id"], "date": "2026-10-20"}).json()
    assert r["action"] == "removed"


@needs_company_data
def test_draft_publish_visibility_and_revisions(client):
    w = items(client)[0]
    client.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-15"], "work_item_id": w["id"]})
    assert client.get("/api/today?d=2026-10-15").json()["entries"] == []          # draft invisible
    p = client.post("/api/plans/2026/10/publish", json={"note": "แรก"}).json()
    assert p["revision"] == 1 and len(p["diff"]["added"]) == 1
    today = client.get("/api/today?d=2026-10-15").json()["entries"]
    assert [e["title_th"] for e in today] == [w["name_th"]]
    assert client.post("/api/plans/2026/10/publish", json={}).status_code == 422  # nothing changed
    uid = today[0]["uid"]
    client.patch(f"/api/entries/{uid}", json={"date": "2026-10-16"})
    # mobile still sees REV.01 until publish
    assert len(client.get("/api/today?d=2026-10-15").json()["entries"]) == 1
    v = client.get("/api/plans/2026/10").json()
    assert v["plan"]["draft_dirty"] is True
    p2 = client.post("/api/plans/2026/10/publish", json={}).json()
    assert p2["revision"] == 2
    assert p2["diff"]["changed"][0]["uid"] == uid and "date" in p2["diff"]["changed"][0]["fields"]
    moved = client.get("/api/today?d=2026-10-16").json()["entries"][0]
    assert moved["uid"] == uid and moved["original_date"] == "2026-10-15" and moved["revision"] == 2


@needs_company_data
def test_cross_midnight_and_operational_day(client):
    w = items(client)[0]
    r = client.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-15"], "work_item_id": w["id"],
                                                         "start_time": "21:00", "end_time": "02:00", "shift": "N"}).json()
    e = r["created"][0]
    assert e["start_at"] == "2026-10-15T21:00:00+07:00" and e["end_at"] == "2026-10-16T02:00:00+07:00"
    # an entry at 01:00 of the 16th belongs to the operational day of the 15th
    client.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-16"], "work_item_id": w["id"],
                                                    "start_time": "01:00", "end_time": "03:00"})
    client.post("/api/plans/2026/10/publish", json={})
    d15 = client.get("/api/today?d=2026-10-15").json()
    assert [x["start_at"][11:16] for x in d15["entries"]] == ["21:00", "01:00"]
    assert d15["window"] == ["2026-10-15T08:00:00+07:00", "2026-10-16T08:00:00+07:00"]
    assert d15["overlaps"] == [[d15["entries"][0]["uid"], d15["entries"][1]["uid"]]]  # warning only
    assert client.get("/api/today?d=2026-10-16").json()["entries"] == []


@needs_company_data
def test_month_boundary_op_day(client):
    """02:00 on Nov 1 belongs to op day Oct 31 (different monthly plan)."""
    w = items(client)[0]
    client.post("/api/plans/2026/11/entries", json={"dates": ["2026-11-01"], "work_item_id": w["id"], "start_time": "02:00", "end_time": "04:00"})
    client.post("/api/plans/2026/11/publish", json={})
    assert len(client.get("/api/today?d=2026-10-31").json()["entries"]) == 1


@needs_company_data
def test_copy_prior_month(client):
    w = items(client)[0]
    client.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-05", "2026-10-31"], "work_item_id": w["id"]})
    r = client.post("/api/plans/2026/11/copy-prior?with_dates=true").json()
    assert r["rows"] == 1 and r["entries"] == 1 and r["skipped_dates"] == ["2026-10-31"]   # no Nov 31 — not guessed


@needs_company_data
def test_rbac(client):
    viewer = user_client(client, "viewer")
    leader = user_client(client, "leader")
    w = items(client)[0]
    assert viewer.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-05"], "work_item_id": w["id"]}).status_code == 403
    assert leader.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-05"], "work_item_id": w["id"]}).status_code == 200
    assert viewer.post("/api/plans/2026/10/publish", json={}).status_code == 200      # everyone may publish (user decision)
    assert viewer.post("/api/categories", json={"name_th": "x"}).status_code == 403
    assert viewer.get("/api/users").status_code == 403


@needs_company_data
def test_progress_rules(client):
    viewer = user_client(client, "viewer")
    w = items(client)[0]
    uid = client.post("/api/plans/2026/10/entries", json={"dates": ["2026-10-05"], "work_item_id": w["id"]}).json()["created"][0]["uid"]
    client.post("/api/plans/2026/10/publish", json={})
    assert viewer.post(f"/api/progress/{uid}", json={"status": "completed"}).status_code == 422
    assert viewer.post(f"/api/progress/{uid}", json={"status": "pending_review"}).json()["status"] == "pending_review"
    assert client.post(f"/api/progress/{uid}", json={"status": "completed"}).json()["status"] == "completed"
    assert client.get("/api/today?d=2026-10-05").json()["entries"][0]["progress"]["status"] == "completed"


@needs_company_data
def test_shift_time_settings_kept_separate(client):
    s = client.get("/api/settings").json()
    assert s["official_roster_times"]["D"] == {"start": "08:00", "end": "20:15"}
    assert s["official_roster_times"]["N"] == {"start": "20:00", "end": "08:15"}
    assert s["official_roster_times"]["confirmed"] is True             # user confirmed 08:00–20:15 / 20:00–08:15
    assert s["planning_bands"]["day"]["end"] == "20:00" and s["planning_bands"]["night"]["end"] == "08:00"
    assert [x["start"] for x in s["planning_bands"]["day"]["segments"]] == ["08:00", "17:00"]
    assert [x["start"] for x in s["planning_bands"]["night"]["segments"]] == ["20:00", "05:00"]
    assert client.put("/api/settings/official_roster_times", json={}).status_code == 422


@needs_company_data
def test_today_shift_card_has_no_people(client):
    t = client.get("/api/today?d=2026-10-15").json()
    assert t["shift"]["status"] == "no_calendar"                  # calendar not imported yet → no claim
    assert sum(len(v) for v in t["shift"]["teams"].values()) == 12
    assert "shifts" not in t["shift"]


@needs_company_data
def test_employees_seeded_from_template_and_team_editable(client):
    emps = client.get("/api/employees").json()
    assert len(emps) == 12
    assert {e["team"] for e in emps} == {"A", "B", "C"} and [sum(e["team"] == t for e in emps) for t in "ABC"] == [4, 4, 4]
    assert all(e["source_ref"].startswith("Template 10!B") for e in emps)
    e = emps[0]
    r = client.patch(f"/api/employees/{e['id']}", json={"team": "C"}).json()
    assert r["team"] == "C" and r["name"] == e["name"]                 # name unchanged
    assert client.patch(f"/api/employees/{e['id']}", json={"team": "D"}).status_code == 422
    viewer = user_client(client, "viewer", "v2")
    assert viewer.patch(f"/api/employees/{e['id']}", json={"team": "A"}).status_code == 403


@needs_company_data
def test_export_mark_default_is_check_for_plan(client):
    assert client.get("/api/settings").json()["export_mark_mode"]["planned"] == "✔"


@needs_company_data
def test_change_own_password_and_first_password_file(client):
    from hrm import config
    viewer = user_client(client, "viewer", "pw1")
    assert viewer.post("/api/me/password", json={"current": "wrong", "new": "abcdef"}).status_code == 422
    assert viewer.post("/api/me/password", json={"current": "pass1234", "new": "abc"}).status_code == 422
    assert viewer.post("/api/me/password", json={"current": "pass1234", "new": "newpass99"}).json()["ok"]
    from fastapi.testclient import TestClient
    c = TestClient(client.app)
    assert c.post("/api/auth/login", json={"username": "pw1", "password": "newpass99"}).status_code == 200
    # admin changing password removes the first-run password file
    f = config.DATA_DIR / "FIRST_ADMIN_PASSWORD.txt"
    f.write_text("x", encoding="utf-8")
    assert client.post("/api/me/password", json={"current": "admin123", "new": "admin456"}).json()["ok"]
    assert not f.exists()
