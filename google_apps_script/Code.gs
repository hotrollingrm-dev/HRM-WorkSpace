/**
 * HRM WorkSpace — หน้า "งานวันนี้" + เพิ่มนัดหมาย สำหรับมือถือ/แท็บเล็ต (Google Apps Script)
 *
 * 1) แผนงาน: อ่านไฟล์ HRM_mobile.csv ที่ใหม่ที่สุดใน Google Drive ของบัญชีนี้
 *    (ไฟล์มาจากปุ่ม "ไฟล์มือถือ" ในโปรแกรม — มีแค่งานที่ Publish แล้ว + ตัวอักษรทีม ไม่มีรายชื่อพนักงาน)
 * 2) นัดหมาย: เพิ่ม/ลบจากหน้าเว็บนี้ได้เลย → ลงปฏิทิน Google ชื่อ "HRM งานทีม" พร้อมเตือนก่อนเวลา
 *    คนในทีมเพิ่มปฏิทินนี้ในมือถือครั้งเดียว แล้วมือถือจะเด้งเตือนเองทุกนัด
 *
 * ── ตั้งค่า (แก้ได้ 3 บรรทัดนี้) ──────────────────────────────
 */
const ADD_PIN = '';               // รหัสสำหรับเพิ่ม/ลบนัด เช่น '2468' — ปล่อยว่าง = ปิดการเพิ่มนัด
const REMIND_MIN = 10;            // เตือนก่อนนัดกี่นาที
const CALENDAR_NAME = 'HRM งานทีม';
/* ─────────────────────────────────────────────────────────── */

const FILE_PREFIX = 'HRM_mobile';
const TZ = 'Asia/Bangkok';

function doGet() {
  const t = HtmlService.createTemplateFromFile('Index');
  t.dataJson = JSON.stringify(getData()).replace(/</g, '\\u003c');
  return t.evaluate()
    .setTitle('HRM งานวันนี้')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1, viewport-fit=cover');
}

/** ข้อมูลทั้งหมดของหน้า (เรียกจากปุ่ม "โหลดใหม่" ด้วย) */
function getData() {
  const out = { rows: [], appts: [], canAdd: !!ADD_PIN, remindMin: REMIND_MIN, calendarName: CALENDAR_NAME };
  try { Object.assign(out, readPlan_()); } catch (e) { out.planError = 'อ่านไฟล์แผนงานไม่ได้: ' + e.message; }
  try {
    const cal = calendar_();
    out.calendarId = cal.getId();
    out.appts = listAppts_(cal);
  } catch (e) { out.calError = 'อ่านปฏิทินไม่ได้: ' + e.message; }
  return out;
}

/** เพิ่มนัด: f = {pin, title, date:'yyyy-MM-dd', start:'HH:mm', end:'HH:mm'?, location, notes} */
function addAppt(f) {
  checkPin_(f && f.pin);
  const title = String(f.title || '').trim();
  if (!title) throw new Error('กรุณาใส่ชื่อนัด');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(f.date || '') || !/^\d{2}:\d{2}$/.test(f.start || '')) throw new Error('วันหรือเวลาไม่ถูกต้อง');
  const s = new Date(f.date + 'T' + f.start + ':00+07:00');
  let e = /^\d{2}:\d{2}$/.test(f.end || '') ? new Date(f.date + 'T' + f.end + ':00+07:00') : new Date(s.getTime() + 60 * 60000);
  if (e <= s) e = new Date(e.getTime() + 24 * 3600000);          // เลยเที่ยงคืน (กะดึก)
  const ev = calendar_().createEvent(title, s, e, {
    location: String(f.location || '').trim(),
    description: (String(f.notes || '').trim() + '\n\n— เพิ่มจากแอป HRM').trim()
  });
  ev.removeAllReminders();
  ev.addPopupReminder(REMIND_MIN);
  return getData();
}

function deleteAppt(id, pin) {
  checkPin_(pin);
  const ev = calendar_().getEventById(String(id));
  if (ev) ev.deleteEvent();
  return getData();
}

function checkPin(pin) { checkPin_(pin); return true; }

/* ── ภายใน ───────────────────────────────────────────────── */
function checkPin_(pin) {
  if (!ADD_PIN) throw new Error('ยังเปิดการเพิ่มนัดไม่ได้ — ให้หัวหน้าตั้ง ADD_PIN ใน Code.gs');
  if (String(pin || '') !== String(ADD_PIN)) throw new Error('รหัสไม่ถูกต้อง');
}

function calendar_() {
  const found = CalendarApp.getCalendarsByName(CALENDAR_NAME);
  if (found.length) return found[0];
  return CalendarApp.createCalendar(CALENDAR_NAME, { timeZone: TZ, color: CalendarApp.Color.BLUE });
}

function listAppts_(cal) {
  const from = new Date(Date.now() - 24 * 3600000);
  const to = new Date(Date.now() + 10 * 24 * 3600000);
  return cal.getEvents(from, to).map(ev => ({
    id: ev.getId(),
    title: ev.getTitle(),
    allDay: ev.isAllDayEvent(),
    date: Utilities.formatDate(ev.getStartTime(), TZ, 'yyyy-MM-dd'),
    start: ev.isAllDayEvent() ? '' : Utilities.formatDate(ev.getStartTime(), TZ, 'HH:mm'),
    end: ev.isAllDayEvent() ? '' : Utilities.formatDate(ev.getEndTime(), TZ, 'HH:mm'),
    location: ev.getLocation() || '',
    notes: (ev.getDescription() || '').replace(/\n*— เพิ่มจากแอป HRM\s*$/, '')
  }));
}

function readPlan_() {
  const f = newestFile_();
  if (!f) return { planError: 'ยังไม่พบไฟล์ ' + FILE_PREFIX + '.csv ใน Google Drive' };
  const key = f.getId() + ':' + f.getLastUpdated().getTime();
  const cache = CacheService.getScriptCache();
  const hit = cache.get(key);
  if (hit) return JSON.parse(hit);
  const table = readTable_(f);
  const head = table.shift().map(String);
  const rows = table
    .filter(r => r.join('').trim() !== '')
    .map(r => { const o = {}; head.forEach((h, i) => { o[h] = r[i] == null ? '' : String(r[i]); }); return o; });
  const data = { rows: rows, file: f.getName(), uploaded: f.getLastUpdated().toISOString() };
  try { cache.put(key, JSON.stringify(data), 300); } catch (e) { /* ใหญ่เกิน cache ก็ไม่เป็นไร */ }
  return data;
}

function newestFile_() {
  const it = DriveApp.searchFiles('title contains "' + FILE_PREFIX + '" and trashed = false');
  let best = null;
  while (it.hasNext()) {
    const f = it.next();
    const ok = /\.csv$/i.test(f.getName()) || f.getMimeType() === MimeType.CSV ||
               f.getMimeType() === MimeType.GOOGLE_SHEETS;
    if (ok && (!best || f.getLastUpdated() > best.getLastUpdated())) best = f;
  }
  return best;
}

function readTable_(f) {
  if (f.getMimeType() === MimeType.GOOGLE_SHEETS) {
    return SpreadsheetApp.openById(f.getId()).getSheets()[0].getDataRange().getDisplayValues();
  }
  const text = f.getBlob().getDataAsString('UTF-8').replace(/^﻿/, '');
  return Utilities.parseCsv(text);
}
