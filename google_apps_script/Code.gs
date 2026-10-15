/**
 * HRM WorkSpace — หน้า "งานวันนี้" สำหรับมือถือ (Google Apps Script)
 *
 * อ่านไฟล์ HRM_mobile.csv ที่ "ใหม่ที่สุด" ใน Google Drive ของบัญชีนี้ แล้วแสดงเป็นหน้าเว็บมือถือ
 * ไฟล์มาจากปุ่ม "ไฟล์มือถือ" ในโปรแกรม HRM WorkSpace — มีเฉพาะงานที่ Publish แล้ว 8 วัน
 * และตัวอักษรทีม A/B/C (ไม่มีรายชื่อพนักงาน)
 *
 * ไม่ต้องแก้อะไรในไฟล์นี้ — วางทั้งหมดแล้วกด Deploy ตามคู่มือ MOBILE_GOOGLE_TH.md
 */
const FILE_PREFIX = 'HRM_mobile';

function doGet() {
  const t = HtmlService.createTemplateFromFile('Index');
  t.dataJson = JSON.stringify(getData()).replace(/</g, '\\u003c');
  return t.evaluate()
    .setTitle('HRM งานวันนี้')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1, viewport-fit=cover');
}

/** เรียกจากปุ่ม "โหลดใหม่" บนหน้าเว็บด้วย */
function getData() {
  const f = newestFile_();
  if (!f) return { error: 'ยังไม่พบไฟล์ ' + FILE_PREFIX + '.csv ใน Google Drive' };
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
  try { cache.put(key, JSON.stringify(data), 300); } catch (e) { /* ข้อมูลใหญ่เกิน cache ก็ไม่เป็นไร */ }
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
    // กรณี Drive แปลงไฟล์เป็น Google ชีตให้อัตโนมัติ
    return SpreadsheetApp.openById(f.getId()).getSheets()[0].getDataRange().getDisplayValues();
  }
  const text = f.getBlob().getDataAsString('UTF-8').replace(/^﻿/, '');
  return Utilities.parseCsv(text);
}
