# TEST RESULTS — Milestone 1
รันเมื่อ 15 ต.ค. 2026 · Python 3.13 · `python -m pytest -v tests`
**ผล (M1.4, 15 ต.ค. 22:40): 45 passed บน Python 3.11 / 3.12 / 3.13 / 3.14** — แก้ SQLAlchemy 2.0.40 ที่เปิดไม่ขึ้นบน Python 3.14 (เจอบนคอมผู้ใช้) เป็น 2.0.54 + FastAPI 0.143.1 · ทดสอบเปิดเซิร์ฟเวอร์จริงบน 3.14 ผ่าน · ชุด offline ทั้ง 4 เวอร์ชันติดตั้งครบโดยไม่ใช้เน็ต (dry-run)

ก่อนหน้า: **ผล: 44 passed, 0 failed** (35.9 s) — อัปเดต 15 ต.ค. 19:45 หลังเปลี่ยนเป็นธีม HRM Hydraulic + ยืนยันช่องเหลือง/shutdown

ธีม: ตรวจไม่มีการเลื่อนแนวนอนทั้งหน้าที่ 1920 / 1440 / 1280 / 1024 / 390 px (แผนรายเดือน, ตั้งค่า, นำเข้า, ประวัติ, งานวันนี้, กะ) · โหมดสว่างและมืด · ไม่มี JS error

| กลุ่ม | Test | ผล |
|---|---|---|
| Master | test_master_crud_and_soft_delete · test_seed_from_template_is_traceable | ✅ |
| Monthly plan | test_multi_date_quick_entry_saves_once_on_correct_dates · test_toggle_cell · test_copy_prior_month (ไม่สร้าง 31 พ.ย.) | ✅ |
| Draft / Publish | test_draft_publish_visibility_and_revisions (draft มองไม่เห็นบนมือถือ, REV+1, uid คงที่, original_date) | ✅ |
| เวลา | test_cross_midnight_and_operational_day · test_month_boundary_op_day · test_build_range_cross_midnight · test_op_day_boundaries · test_validate_range · test_overlap_warning | ✅ |
| สิทธิ์ | test_rbac · test_progress_rules (Viewer ยืนยันเสร็จไม่ได้) | ✅ |
| เวลากะ 2 ชุด | test_shift_time_settings_kept_separate (PDF 08:00–20:15/20:00–08:15 แยกจาก 08–20/20–08, แก้ทางหน้าจอไม่ได้) · test_today_shift_card_has_no_people | ✅ |
| Import (ไฟล์จริง) | test_import_preview_against_real_file · test_import_commit_creates_draft_only_and_no_completion · test_reimport_skips_duplicates_and_respects_manual_edits · test_rejected_row_fixed_by_user · test_revert_keeps_manually_edited · test_parse_line ×7 · test_split_events_continuation | ✅ |
| Export | test_export_requires_publish_or_draft · test_export_matches_template_structure_and_marks · test_export_overflow_goes_to_detail_sheet | ✅ |
| UI | test_no_ot_label_in_ui · test_every_ui_label_bilingual · test_static_pages_served | ✅ |

## การนำเข้าไฟล์จริง `Monthly schedule 2026.04 - 2027.03 Rev00.xlsx` (ปี 2026)
- อ่านได้ 8 sheet (May–Dec), ข้าม 4 (HOT Plan Apr/May, Master plan, Sheet1) พร้อมเหตุผล
- 215 รายการ → เพิ่มได้ 213, **ปฏิเสธ 2** (`Jul!B64` วันที่ 30 ซ้ำ + ชื่อวันไม่ตรง), ไม่มีเวลา 21 รายการ → Unscheduled, เตือนเลข MBO 14 รายการ
- เตือน `Jul` หัวเอกสารเขียน August
- นำเข้าซ้ำ: 213 รายการเป็น "ซ้ำ — ข้าม", 0 รายการใหม่
- ความเร็ว: 0.28 s (เปลี่ยนเป็น read-only หลังพบว่าโหลดเต็มใช้ 10.5 s เพราะ 8,368 merges)

## Export เทียบ Template (`tools/compare_export.py`)
สร้างจากแผน ต.ค. ที่โหลดเครื่องหมายจาก Template sheet `10` → **16/16 OK**:
dimensions, print area `A1:AS46`, landscape, paperSize, scale 93, margins, freeze `J7`, column widths, row heights, 24 conditional formats, 2 data validations, merges นอก/ใน body (เหมือนต้นฉบับทุก range), สูตรทั้งหมดนอก body, สไตล์ทุกเซลล์นอก body, ฟอนต์ใน body มาจากสไตล์ของ Template, ไม่มีชื่อพนักงาน
ภาพเทียบ (render ด้วย LibreOffice): `screenshots/20_export_compare_TEMPLATE_sheet10.png` vs `screenshots/21_export_compare_APP_output.png`
ความต่างที่ตั้งใจ: แผนใช้ `●` แทน `✔` (Q-EX1), `AR แผน Target` มีจำนวน (Q-EX2), F2 แสดง REV/สถานะ/เวลาส่งออก, ส่วนกะเว้นว่างและล้างสีพื้นตายตัวของ roster เดิม, J:L ว่างเพราะยังไม่มีแผน ก.ย.

## ตารางกะ 3 Group (tests/test_roster.py)
- test_transcription_matches_pdf_checksums: WD 45/45, ตารางสรุป 2026 ตรง, ข้อยกเว้นเฉพาะวัน Substitution
- test_fills_detected_from_pixels: ช่องเหลือง/เขียว/S ตรงจุดที่ตรวจด้วยตา
- test_roster_needs_confirmation_then_drives_today_and_export: ต้องกดยืนยันก่อนใช้ · ทีม D/N และเวลากะของวันตัวอย่างตรงกับตารางกะ · test_official_times_confirmed

## Tablet (Playwright, has_touch) — 15 ต.ค. 18:10
iPad แนวนอน 1180×820, iPad แนวตั้ง 820×1180, Android 1280×800: แผนรายเดือน (เปิดมาที่คอลัมน์วันนี้), ลงงานด่วนแบบแผงเลื่อน, ตั้งค่า → พนักงาน (สลับทีม), หน้า m.html แบบ 2 คอลัมน์ — ไม่มี JS error · ภาพ `screenshots/30_*`–`34_*`
ใหม่: test_employees_seeded_from_template_and_team_editable · test_export_mark_default_is_check_for_plan · test_export_reflects_team_change

## UI ตรวจด้วย Playwright (Chromium) 1920×1080 และ 390×844
หน้า Login, แผนรายเดือน, ลงงานด่วน (เลือก 3 วัน), รายละเอียดวัน, Publish dialog, ตั้งค่า, นำเข้า (preview), มือถือ งานวันนี้/sheet — ไม่มี JS error (มีเฉพาะ 401 ก่อน login ตามปกติ) · ภาพอยู่ใน `screenshots/`

## ยังไม่ได้ทดสอบ / ไม่อยู่ใน M1
- การแยกรหัสกะ D/N/H/S จาก PDF (Milestone 4 — PDF เป็นภาพสแกน)
- PDF export / PNG LINE / Push notification / Timeline drag-drop (M2–M5)
- เปิดไฟล์ export ด้วย Microsoft Excel จริง (ทดสอบด้วย openpyxl + LibreOffice) — ควรเปิดใน Excel ของโรงงาน 1 ครั้ง
- ทดสอบบน iPhone/Android จริง และติดตั้ง PWA (ต้องใช้ HTTPS)
