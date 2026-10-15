---
name: hrm-workspace-dev
description: Working on the HRM WorkSpace repo (FastAPI + SQLite + vanilla JS planner/PWA for the Hot Rolling Mill). Use for any code change, test run, dependency bump, Windows installer change or release package in this repository.
---

# HRM WorkSpace — development workflow

## Layout
```
app/hrm/            FastAPI backend (models, seed, services/plans|importer|exporter|roster)
app/web/            vanilla ES modules, no build step (index.html = planner, m.html = Today's Work PWA)
app/tests/          pytest
app/tools/          compare_export, detect_roster_fills, load_template_plan, backup, reset_password
app/company_data/   COMPANY DATA — git-ignored, only README.md is tracked
app/*.bat           Windows installer / launcher scripts
project_docs/       architecture, schema, plan, open questions, test results
```

## Company data rule (most important)
- Template xlsx, Monthly schedule xlsx, roster PDF, `master_seed.json`, `roster_codes.json`, `roster_fills.json` live only in `app/company_data/` on the user's PC.
- Code reads them via `hrm.config.COMPANY_DIR`; the app must still start without them (empty master, clear Thai error messages).
- Never hard-code employee names/IDs, meeting titles, roster codes or task names in code, tests or docs. Tests compare against data loaded at runtime.
- Before every commit: `git ls-files -z | xargs -0 grep -lE "<employee surnames / IDs / meeting keywords>"` must return nothing.

## Tests
```bash
cd app
pip install -r requirements-dev.txt
python -m pytest -q tests
```
- With `company_data/` present: all tests run (45 at M1.3). Without it: data tests are skipped via `@needs_company_data` (14 pass, 31 skip) — that is expected in cloud sessions.
- Export changes: run `python -m tools.compare_export <file.xlsx>` — must print no `DIFF` lines.

## Dependencies & Python versions
- `requirements.txt` is pinned. Any bump must be tested on **Python 3.11, 3.12, 3.13 and 3.14** (the user's PC runs 3.14):
  ```bash
  pip install uv && for v in 3.11 3.12 3.13 3.14; do uv python install $v; P=$(uv python find $v); \
    rm -rf /tmp/v && $P -m venv /tmp/v && /tmp/v/bin/pip install -q -r requirements-dev.txt && \
    echo "$v: $(/tmp/v/bin/python -m pytest -q tests | tail -1)"; done
  ```
- History: SQLAlchemy 2.0.40 crashes on Python 3.14 (`descriptor '__getitem__' requires a 'typing.Union' object`) → use ≥ 2.0.54. FastAPI 0.115 emits 3.14 asyncio deprecations → use current FastAPI.

## Windows scripts (`app/*.bat`)
- ASCII only, **CRLF** line endings (`sed -i 's/\r$//; s/$/\r/' file.bat`).
- Inside `if (...)` / `for (...)` blocks escape parentheses in `echo` text: `^(` `^)`.
- `install_windows.bat` must keep: Python detection (py launcher 3.14→3.11, then `python`), private `.venv`, offline install from `wheels\pyXY` when present, self-check `import hrm.main`, desktop shortcut.
- Cannot be executed in the cloud container — review by reading and say so in the hand-off.

## Offline package (for PCs without internet)
```bash
for v in 311 312 313 314; do pip download -q -r requirements.txt colorama==0.4.6 --only-binary=:all: \
  --platform win_amd64 --python-version $v --implementation cp -d wheels/py$v; done
# verify each set resolves offline:
pip install --dry-run --no-index --find-links wheels/py314 --platform win_amd64 --python-version 314 \
  --implementation cp --only-binary=:all: --target /tmp/x -r requirements.txt colorama
```
Zip = `git archive HEAD` + `app/wheels/`. Company data is shipped separately (`HRM_company_data.zip`), never inside the code package.

## UI conventions
- Theme: `hrm-hydraulic-theme` skill; tokens in `app/web/css/base.css` (light + dark). No hard-coded colours outside tokens (category colours are user data).
- Labels via `bi()` / dictionary `T` in `app/web/js/ui.js` (Thai + Japanese). Japanese UI strings are drafts until reviewed (`JP_APPROVED = false`).
- Check no horizontal page scroll at 1920 / 1440 / 1280 / 1024 / 390 px with Playwright; panes scroll inside themselves.
- Never show the word "OT" on timeline/planning UI (test `test_no_ot_label_in_ui`).

## Hand-off checklist
- Tests run on all four Python versions if dependencies changed; record results in `project_docs/TEST_RESULTS.md`.
- Update `project_docs/OPEN_QUESTIONS.md` when the user answers or a new data conflict appears.
- Commit message ends with the session attribution lines.
