# Requirement Traceability (Handover v1.1 → Milestone 1)
✅ เสร็จ/ทดสอบแล้ว · 🟡 บางส่วน · ⏳ Milestone ถัดไป · ⛔ รอข้อมูล

| Handover | ข้อกำหนด | สถานะ | ที่อยู่ในโค้ด / Test |
|---|---|---|---|
| §3.3, §15 | Persistent DB, accounts, roles, audit log | ✅ (บทบาทชั่วคราว Q-SY1) | models.py, auth.py · test_rbac |
| §4.2, §5 | Month matrix, multi-date Quick Entry, month switch, Copy prior | ✅ | desktop.js planPage · test_multi_date…, test_copy_prior_month |
| §5 | Work Master ≠ Work Instance; recurrence ไม่ล็อกวัน | ✅ (recurrence ⏳ M3) | work_items vs plan_entries |
| §5 | Draft/Publish, REV, change history, original date | ✅ | plans.publish · test_draft_publish… |
| §6 | Op day 08→08, bands 08–17/17–20/20–05/05–08, no OT | ✅ (แถบเวลา; Timeline เต็ม ⏳ M2) | timeutil.py, heatStrip · test_no_ot_label_in_ui |
| §6 | start/end datetime เต็ม, cross-midnight, Unscheduled, overlap warning | ✅ | test_cross_midnight… |
| §7 | 3-level hierarchy CRUD, TH/JP, color, sort, deactivate | ✅ | settingsPage · test_master_crud… |
| §8 | Thai บน / JP เล็กล่าง, `[รอแปล]` | 🟡 (ร่าง JP รออนุมัติ Q-SY4) | ui.js bi() |
| §9 | Import Excel preview/validate/dup/no-overwrite/revert/provenance | ✅ (PDF import ⏳ M4) | importer.py · test_import_* |
| §10 | Export XLSX ตาม Template + Daily Detail + REV | ✅ (PDF ⏳ M3) | exporter.py · test_export_* |
| §11 | Push notifications | ⏳ M5 | — |
| §12 | Shift roster / members | ⛔ รอไฟล์ (การ์ดแสดงสถานะรอ) | today.shift |
| §13 | Breakdown mode | ⏳ M3 | — |
| §14 | PNG for LINE | ⏳ M2 | — |
| §3.2 | Mobile PWA Today's Work, tap-first, status | ✅ | mobile.js, sw.js, manifest |
| §17 | UX: hierarchy, large touch targets, states | ✅ | screenshots/ |
