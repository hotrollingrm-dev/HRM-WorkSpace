# HRM WorkSpace — Agent Instructions

- Primary language: Thai. Product UI: Thai main line, Japanese secondary small line. Missing/unapproved translations = `[รอแปล]`.
- Visual style: HRM Hydraulic house theme — use the `hrm-hydraulic-theme` skill (`.claude/skills/`). Japanese replaces its default EN secondary line.
- Repo workflow, tests and release steps: use the `hrm-workspace-dev` skill (`.claude/skills/`).
- **Company data never goes into Git**: `app/company_data/*`, `source_files/`, screenshots, FILE_AUDIT. Employee names/IDs, the roster and meeting titles must not appear in code, tests or docs.
- No fabricated attendance, employee names, recurrence intervals, ISO or safety settings. Separate facts, assumptions, unresolved details (`project_docs/OPEN_QUESTIONS.md`).
- Work iteratively with working code in `app/` and tests. Every milestone ends with actual pass/fail results and a list of incomplete features.
- Shift times (user-confirmed): official D 08:00–20:15 / N 20:00–08:15. Planning UI bands 08–17 / 17–20 / 20–05 / 05–08 are colour only, no OT label. Operational day = 08:00 → 08:00 next day.
- Roster = *scheduled*, never attendance. Codes: D, N, H (holiday), S (factory shutdown). Yellow D/N = working on a public holiday; green = substitution day. Group 1/2/3 = Team A/B/C.
- Export marks: ✔ = planned (user-confirmed). Everyone may Publish (single main user).
- Safe operations: no public demos with personnel info; no external uploads, notifications, LINE or deployment without explicit permission.
- Preserve the source Excel layout on export (`tools/compare_export.py` must report no DIFF). Reject questionable import dates instead of guessing.
- Tap-first UI; keep traceability (`source_ref`), audit log and revision numbers.
