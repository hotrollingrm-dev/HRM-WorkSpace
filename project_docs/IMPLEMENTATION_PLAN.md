# Implementation Plan & Sitemap

## Sitemap
**Desktop** (`/`)
- `#/plan` — Monthly Planner: Month switcher · Matrix (หมวด→หมวดย่อย→งาน × วัน) · Quick Entry panel (เลือกหลายวัน) · Day drawer (งานรายวัน/นำเข้า/Unscheduled) · Draft/Publish/REV history · Export
- `#/settings` — Category → Subcategory → Work Item (CRUD, สี, เรียง, เปิด/ปิด, TH/JP + `[รอแปล]`), Time bands, Export options
- `#/import` — อัปโหลด → Preview → Commit/Revert + ประวัติ batch
- `#/history` — Revision ที่ Publish แล้ว + การเปลี่ยนแปลง
**Mobile PWA** (`/m`)
- Today's Work (op-day strip 08→08) · รายการงาน · เริ่ม/เสร็จ · Upcoming 7 วัน · การ์ดกะ `[รอไฟล์]`

## Milestones
| M | ขอบเขต | สถานะ |
|---|---|---|
| **M1** | Login/RBAC, Master CRUD, Monthly Draft + Matrix + Quick Entry หลายวัน, Copy เดือนก่อน, Publish/REV/diff, Mobile Today + Upcoming + Progress, Import Monthly schedule (P1/P2) + Preview/Commit/Revert, Export XLSX จาก Template, PWA shell | **รอบนี้** |
| M2 | Daily Timeline 24h แนวนอน (desktop drag/resize, mobile presets), overlap warning UI, PNG Daily Plan (1080×1350/1920) + REV | ถัดไป |
| M3 | Breakdown Mode (record, steps, affected tasks hold/reschedule, PNG), Recurrence rules + due/overdue, PDF export (LibreOffice headless, ตรวจ print fit) | |
| M4 | Shift: ถอด PDF 15 เดือนเป็นข้อมูล + Preview/ยืนยัน + checksum WD/Summary, Shift card, Employee master (เมื่อได้ไฟล์), แยก scheduled ≠ present | ต้องการ Q-SH1..6, roster |
| M5 | Push: Service worker push + VAPID Web Push/FCM, scheduler, notification center, deep-link, preferences, dedupe/throttle | ต้องการ Q-SY2/Q-SY3 + อนุมัติ IT |
| M6 | Reports planned vs actual, HOT Plan (P0) importer, LINE share sheet, Postgres + backup | |

## Acceptance tests (M1) — ดู `app/tests/`
1. เลือกหลายวัน → บันทึกครั้งเดียว → ปรากฏทุกวันที่ถูกต้อง
2. Draft ไม่เห็นในมือถือจนกว่าจะ Publish · Publish สร้าง REV ใหม่ + diff
3. แก้หลัง Publish → Draft dirty → Publish → REV+1, uid คงที่, original_date เก็บไว้
4. Import: ชื่อวันไม่ตรง → reject · ไม่มีเวลา → Unscheduled · หลายบรรทัด → หลายรายการ · re-import → skip_duplicate · แก้มือแล้วไม่ถูกทับ · Revert
5. Import ไม่สร้าง Completed
6. Export: เปิดได้, merges/CF/DV/print area/widths ตรง Template, เครื่องหมายอยู่คอลัมน์วันถูกต้อง, ไม่มีชื่อพนักงาน
7. Op-day: งาน 02:00 ของวันที่ 3 อยู่ op day วันที่ 2 · end ≤ start ถูกปฏิเสธ
8. Bands: 17–20 และ 05–08 สีต่างกัน ไม่มีข้อความ OT
9. ทุกหน้าหลักมีบรรทัดญี่ปุ่น · ชื่องานที่ไม่มี JP แสดง `[รอแปล]`
