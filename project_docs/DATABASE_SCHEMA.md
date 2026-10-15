# Database Schema (Milestone 1) — `app/hrm/models.py` คือแหล่งจริง

| ตาราง | คอลัมน์หลัก | หมายเหตุ |
|---|---|---|
| `users` | id, username UQ, display_name, role, password_hash (PBKDF2-SHA256 200k), active | |
| `sessions` | token PK, user_id, expires_at | cookie `hrm_session` HttpOnly SameSite=Lax |
| `categories` | id, code, name_th, name_jp?, color, sort_order, active, source_ref | name_jp ว่าง = `[รอแปล]` |
| `subcategories` | id, category_id FK, name_th, name_jp?, sort_order, active, source_ref | |
| `work_items` | id, subcategory_id FK, code, name_th, name_jp?, frequency_label, location, default_duration_min?, sort_order, active, source_ref | soft-delete ด้วย active |
| `monthly_plans` | id, year, month UQ(year,month), current_revision, last_published_at, draft_dirty | 1 แผน/เดือน |
| `plan_rows` | id, plan_id, work_item_id, sort_order UQ(plan_id, work_item_id) | แถวของ Matrix |
| `plan_entries` | id, uid UQ, plan_id, work_item_id?, category_id?, title_th, title_jp?, date, start_at?, end_at?, shift(D/N)?, time_slot?, location, notes, mbo_ref, source_type(manual/import/copy), source_ref, import_batch_id?, manually_edited, original_date, deleted_at?, created_by/at, updated_by/at | **Draft working copy** · CHECK end_at > start_at (ในโค้ด) |
| `plan_versions` | id, plan_id, revision, published_at, published_by, note, snapshot_json, diff_json UQ(plan_id, revision) | immutable |
| `task_progress` | entry_uid PK, status, note, updated_by, updated_at | Planned/In Progress/On Hold/Pending Review/Completed/Cancelled |
| `import_batches` | id, filename, sha256, target_year, uploaded_by, uploaded_at, status(preview/committed/reverted), summary_json | |
| `import_rows` | id, batch_id, sheet, cell_ref, line_no, raw_text, date?, start_at?, end_at?, title, location, mbo_ref, time_slot, issues_json, action, entry_uid? | |
| `holidays` | date PK, name_th, source_ref | seed จาก Template `10!AU5:AV27` |
| `settings` | key PK, value_json | planning_bands, official_roster_times, export_mark_mode |
| `audit_logs` | id, at, user_id, action, entity, entity_id, detail_json | |

Milestone ถัดไปจะเพิ่ม: `employees`, `teams`, `shift_rosters`, `shift_days`, `breakdown_events`, `breakdown_steps`, `affected_tasks`, `recurring_rules`, `notification_*`, `device_push_subscriptions`, `generated_exports`.
