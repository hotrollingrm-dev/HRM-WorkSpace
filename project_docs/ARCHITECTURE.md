# HRM WorkSpace — Architecture (v0.1, Milestone 1)

## 1. ภาพรวม
```
 Desktop browser (Foreman)          Mobile PWA (Leader/Operator)
   /#/plan  /#/settings  /#/import    /m  (Today's Work)
            │   fetch JSON (same origin, cookie session)  │
            └───────────────┬─────────────────────────────┘
                     FastAPI (hrm/main.py)
     auth · master · plans · publish · progress · import · export
                            │
              SQLAlchemy 2 ──► SQLite (WAL)  app/data/hrm.db
              openpyxl     ──► source_files/ template (read-only)
                           ──► app/data/exports/*.xlsx
```
- **ไม่มี build step** (Vanilla ES modules) → เปิดบน PC โรงงานได้ด้วย Python อย่างเดียว ไม่ต้องใช้ Node
- **ไม่เรียกบริการภายนอก** — ฟอนต์อยู่ใน `web/fonts/`, ไม่มี CDN, ไม่มี telemetry
- Postgres-ready: เปลี่ยน `HRM_DB_URL` ได้ (ใช้ type มาตรฐาน, ไม่มี SQL เฉพาะ SQLite)

## 2. หลักการข้อมูล
| หลัก | วิธีทำ |
|---|---|
| Plan once → Publish | แต่ละเดือนมี **Draft working copy** (`plan_entries`) · Publish = snapshot JSON ลง `plan_versions` (REV ต่อเนื่อง) · มือถืออ่านเฉพาะ snapshot ล่าสุด |
| Work Master ≠ Work Instance | `work_items` (แม่แบบ) กับ `plan_entries` (งานจริง/วันที่) แยกกัน · ลบแม่แบบ = soft (active=false) |
| Recurrence ไม่ล็อกวันที่ | M1 เก็บเพียง `frequency_label` (ข้อความจาก Template) ยังไม่คำนวณ |
| Planned ≠ Actual | ผลงานจริงอยู่ `task_progress` ผูกกับ `entry_uid` (คงที่ข้าม revision) ไม่ทำให้ต้อง Publish ใหม่ |
| Import ไม่ยืนยันผลงาน | ไม่มีเส้นทางโค้ดใดจาก Import ที่สร้าง `task_progress` |
| เวลาไม่กำกวม | `start_at`/`end_at` เป็น ISO datetime +07:00 เต็ม · ไม่มีเวลา = **Unscheduled** |
| Traceability | ทุก entry จาก import มี `source_ref` (`Oct!I6#2`), `import_batch_id`; `audit_logs` ทุกการเขียน |

## 3. Operational Day & Bands
- Operational day D = `[D 08:00, D+1 08:00)` Asia/Bangkok
- `planning_bands` (ตั้งค่า, ผู้ใช้กำหนด): 08–17 / 17–20 (กะ D) · 20–05 / 05–08 (กะ N) — แสดงเป็นสีเท่านั้น ไม่มีคำว่า OT
- `official_roster_times` (จาก PDF): D 08:00–20:15, N 20:00–08:15 — **เก็บแยก** ยังไม่ใช้คำนวณ (Q-SH1)
- งานมีเวลา: อยู่ใน op day ตาม `start_at` · งานไม่มีเวลา: อยู่ตาม `date`

## 4. Roles (ชั่วคราว — Q-SY1)
| Role | สิทธิ์ |
|---|---|
| admin | ทุกอย่าง + ผู้ใช้ |
| foreman | Master, Draft, Publish, Import, Export, ยืนยันเสร็จ |
| leader | Master (ไม่ลบ), Draft, ส่ง "เสร็จ (รอตรวจ)" |
| viewer | ดู published + ส่ง "เสร็จ (รอตรวจ)" |

## 5. Export pipeline
1. เปิด Template (read-only) → เก็บ sheet `10` เป็นต้นแบบ, ลบ `9`,`11`,`12`,`Sheet1`
2. ตั้ง `D2` = วันที่ 1 ของเดือน → สูตรหัวเอกสาร/วันที่/ชื่อวันทำงานเอง
3. Unmerge เฉพาะ A:I แถว 7–28 → เขียนแถวงานใหม่ใช้สไตล์ต้นแบบจากแถว 7/12 (สลับสีกลุ่มเหมือนต้นฉบับ) → merge ใหม่ตามกลุ่ม (No./หมวด/ความถี่/จุด)
4. เครื่องหมายวัน: แผน `●` · เสร็จ (ยืนยัน) `✔` (ตั้งค่าได้, Q-EX1) · J:L = 3 วันท้ายเดือนก่อน
5. ส่วนกะ (33–44): ล้างข้อมูลบุคคล คงสูตร
6. AU5:AU27 = วันหยุดของปีที่ export
7. เกิน 22 แถว / งานนำเข้า / งานไม่มีแม่แบบ → sheet `Daily Detail`
8. F2 = `REV.xx · สถานะ · เวลาส่งออก`
9. ทดสอบ: structural diff กับ Template + render ด้วย LibreOffice เป็น PNG เทียบ

## 6. Import pipeline (Monthly schedule)
Upload → SHA-256 → detect layout ต่อ sheet (P1 May/Jun, P2 Jul–Dec, P0 HOT Plan = ข้าม) → แยกบรรทัด → parse เวลา → ตรวจชื่อวันกับปีที่เลือก → ตรวจซ้ำกับ Draft → **Preview** (add / skip_duplicate / update_candidate / conflict / reject) → ผู้ใช้ปรับ → Commit ลง Draft → Revert ได้ (ยกเว้นแถวที่ถูกแก้มือหลัง import)
