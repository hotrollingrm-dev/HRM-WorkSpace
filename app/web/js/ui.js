// Shared UI helpers: element builder, icons, bilingual labels, toast, dialog, api.
import { sticker, hasSticker } from "./stickers.js";
export { sticker, hasSticker };
/** Sticker when one exists for this name, else the line icon. */
export const art = (name, size = 30, cls = "") => hasSticker(name) ? sticker(name, size, cls) : icon(name);

export const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElementNS(tag === "svg" || attrs.__svg ? "http://www.w3.org/2000/svg" : "http://www.w3.org/1999/xhtml", tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "__svg" || v === undefined || v === null || v === false) continue;
    if (k === "class") el.setAttribute("class", v);
    else if (k === "style" && typeof v === "object") {
      for (const [sk, sv] of Object.entries(v)) {
        if (sv === null || sv === undefined) continue;
        if (sk.startsWith("--")) el.style.setProperty(sk, sv); else el.style[sk] = sv;
      }
    }
    else if (k.startsWith("on")) el.addEventListener(k.slice(2).toLowerCase(), v);
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid === null || kid === undefined || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
};

// ── Icon set: 24px grid, 1.6 stroke, round caps — one family throughout ──
const P = {
  grid: "M4 5.5h16M4 10.5h16M4 15.5h16M4 20h16M8.5 3v18M14 3v18",
  calendar: "M4.5 7.5h15v12h-15zM4.5 11h15M8.5 4.5v4M15.5 4.5v4",
  upload: "M12 15V4.5M7.5 9 12 4.5 16.5 9M5 15.5V19h14v-3.5",
  download: "M12 4.5V15M7.5 10.5 12 15l4.5-4.5M5 15.5V19h14v-3.5",
  gear: "M12 9.2a2.8 2.8 0 1 1 0 5.6 2.8 2.8 0 0 1 0-5.6ZM12 3.5v2.2M12 18.3v2.2M20.5 12h-2.2M5.7 12H3.5M18 6l-1.6 1.6M7.6 16.4 6 18M18 18l-1.6-1.6M7.6 7.6 6 6",
  history: "M4.5 12a7.5 7.5 0 1 0 2.2-5.3M4.5 4.5v3.2h3.2M12 8v4.3l2.8 1.7",
  send: "M4.5 11.5 19.5 5l-4.8 14-3.3-6.2zM11.4 12.8l8.1-7.8",
  plus: "M12 5v14M5 12h14",
  x: "M6.5 6.5l11 11M17.5 6.5l-11 11",
  check: "M5 12.5l4.5 4.5L19 7.5",
  chevL: "M14.5 5.5 8 12l6.5 6.5", chevR: "M9.5 5.5 16 12l-6.5 6.5", chevD: "M6 9.5l6 6 6-6",
  sun: "M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8ZM12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4",
  moon: "M18.5 14.5A7 7 0 0 1 9.5 5.5a7 7 0 1 0 9 9Z",
  clock: "M12 4.5a7.5 7.5 0 1 1 0 15 7.5 7.5 0 0 1 0-15ZM12 8v4.2l2.8 1.8",
  user: "M12 4.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7ZM5 19.5c.8-3.2 3.6-5 7-5s6.2 1.8 7 5",
  users: "M9 5a3 3 0 1 1 0 6 3 3 0 0 1 0-6ZM3.5 19c.6-3 2.8-4.7 5.5-4.7s4.9 1.7 5.5 4.7M15.5 5.3a3 3 0 0 1 0 5.6M17 14.6c1.9.5 3.1 2 3.5 4.4",
  logout: "M14 4.5H6v15h8M10.5 12H20M16.5 8.5 20 12l-3.5 3.5",
  search: "M10.5 4.5a6 6 0 1 1 0 12 6 6 0 0 1 0-12ZM15 15l4.5 4.5",
  star: "M12 4.5l2.3 4.8 5.2.7-3.8 3.6.9 5.2-4.6-2.5-4.6 2.5.9-5.2L4.5 10l5.2-.7z",
  trash: "M5 7h14M9.5 7V4.5h5V7M7 7l.8 12.5h8.4L17 7",
  edit: "M5 19h4l10-10-4-4L5 15zM13.5 6.5l4 4",
  alert: "M12 4.5 20.5 19h-17zM12 10v4M12 16.8v.2",
  info: "M12 4.5a7.5 7.5 0 1 1 0 15 7.5 7.5 0 0 1 0-15ZM12 11v5M12 8v.2",
  play: "M8 5.5v13l10-6.5z",
  pause: "M8.5 5.5v13M15.5 5.5v13",
  layers: "M12 4.5 20 9l-8 4.5L4 9zM4 13l8 4.5 8-4.5",
  copy: "M9 9h10.5v10.5H9zM15 9V4.5H4.5V15H9",
  file: "M6 3.5h8l4 4v13H6zM14 3.5v4h4",
  wifiOff: "M3.5 4.5l17 15M8.5 13.5a5 5 0 0 1 4.6-1.4M5.3 10.4a9.5 9.5 0 0 1 4-2.3M12 17.5v.2M15.6 10.6a9.5 9.5 0 0 1 3.1 1.9",
  slab: "M3.5 14.5h17M5 14.5V11h14v3.5M7.5 17.5a1.5 1.5 0 1 0 0 .1M16.5 17.5a1.5 1.5 0 1 0 0 .1M12 17.5a1.5 1.5 0 1 0 0 .1M9 8.5c.6-1.2.6-2.3 0-3.5M12 8.5c.6-1.2.6-2.3 0-3.5M15 8.5c.6-1.2.6-2.3 0-3.5",
};
export const icon = (name, cls = "") => {
  const s = h("svg", { viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "2",
    "stroke-linecap": "round", "stroke-linejoin": "round", class: `ic ${cls}`, "aria-hidden": "true" });
  s.append(h("path", { __svg: true, d: P[name] || P.info }));
  return s;
};

// ── 3D tile icons (HRM Hydraulic theme §8): gradient tile + rim + glyph with depth copy ──
export const TILE = { brand: "#2A64E8", day: "#E7A21B", night: "#5566C8", running: "#1C9B55", idle: "#7F8898",
  abnormal: "#E36C12", leak: "#D93A40", maint: "#7652E8", adjust: "#4F6B8F", refill: "#0E9A7B", low: "#D39A06" };
let tileSeq = 0;
const mixHex = (hex, other, t) => { const a = parseInt(hex.slice(1), 16), b = parseInt(other.slice(1), 16);
  const ch = (x, y) => Math.round(x + (y - x) * t);
  const r = ch(a >> 16, b >> 16), g = ch((a >> 8) & 255, (b >> 8) & 255), bl = ch(a & 255, b & 255);
  return `#${((1 << 24) | (r << 16) | (g << 8) | bl).toString(16).slice(1)}`; };
export const tile3d = (glyph, color = TILE.brand, size = 44) => {
  if (hasSticker(glyph)) return sticker(glyph, size, "tile");
  const id = `t${++tileSeq}`;
  const dark = document.documentElement.dataset.theme === "dark" ||
    (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
  const top = dark ? mixHex(color, "#1c222c", .66) : mixHex(color, "#ffffff", .93);
  const bot = dark ? mixHex(color, "#1c222c", .80) : mixHex(color, "#ffffff", .80);
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 48 48"); s.setAttribute("width", size); s.setAttribute("height", size);
  s.setAttribute("class", "tile3d"); s.setAttribute("aria-hidden", "true");
  s.innerHTML = `<defs><linearGradient id="${id}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${top}"/><stop offset="1" stop-color="${bot}"/></linearGradient>
    <linearGradient id="${id}g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mixHex(color, "#ffffff", .28)}"/><stop offset="1" stop-color="${mixHex(color, "#000000", .10)}"/></linearGradient></defs>
    <rect x="2" y="4.5" width="44" height="42" rx="14" fill="${color}" opacity=".16"/>
    <rect x="2" y="2" width="44" height="42" rx="14" fill="url(#${id}b)" stroke="#fff" stroke-opacity=".75" stroke-width=".75"/>
    <g transform="translate(12 11.6) scale(1)" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="${P[glyph] || P.info}" stroke="#000" stroke-opacity=".22" stroke-width="2.6" transform="translate(0 1.6)"/>
      <path d="${P[glyph] || P.info}" stroke="url(#${id}g)" stroke-width="2.6"/>
      <path d="${P[glyph] || P.info}" stroke="#fff" stroke-opacity=".45" stroke-width=".8" transform="translate(-.4 -.5)"/></g>`;
  return s;
};

// ── Bilingual dictionary. Thai = source. Japanese = DRAFT proposal, not yet approved (OPEN_QUESTIONS Q-SY4).
export const JP_APPROVED = false;
export const T = {
  plan: ["แผนรายเดือน", "月間計画"], settings: ["ตั้งค่า", "設定"], import: ["นำเข้า", "取込"], history: ["ประวัติ", "履歴"],
  today: ["งานวันนี้", "今日の作業"], upcoming: ["7 วันถัดไป", "今後7日間"], shift: ["กะ", "シフト"], account: ["บัญชี", "アカウント"],
  publish: ["Publish แผน", "計画を公開"], export: ["ส่งออก Excel", "Excel出力"], quick: ["ลงงานด่วน", "クイック登録"],
  save: ["บันทึก", "保存"], cancel: ["ยกเลิก", "キャンセル"], login: ["เข้าสู่ระบบ", "ログイン"], logout: ["ออกจากระบบ", "ログアウト"],
  category: ["หมวดหลัก", "カテゴリ"], subcategory: ["หมวดย่อย", "サブカテゴリ"], item: ["รายการงาน", "作業項目"],
  schedule: ["ประชุม / กิจกรรม", "会議・行事"], unscheduled: ["ยังไม่กำหนดเวลา", "時間未定"], draft: ["ฉบับร่าง", "下書き"],
  copyPrior: ["คัดลอกเดือนก่อน", "前月をコピー"], addRow: ["เพิ่มแถวงาน", "行を追加"], users: ["ผู้ใช้", "ユーザー"],
  start: ["เริ่มงาน", "開始"], done: ["เสร็จแล้ว", "完了"], submit: ["ส่งตรวจ", "確認依頼"], hold: ["พักงาน", "保留"],
  upload: ["เลือกไฟล์", "ファイル選択"], commit: ["ยืนยันนำเข้า", "取込確定"], revert: ["ย้อนการนำเข้า", "取込取消"],
  dayDetail: ["รายละเอียดวัน", "日別詳細"], bands: ["แถบเวลา", "時間帯"], master: ["ข้อมูลหลัก", "マスタ"],
};
export const bi = (key, jpOverride) => {
  const [th, jp] = Array.isArray(key) ? key : (T[key] || [key, null]);
  const j = jpOverride !== undefined ? jpOverride : jp;
  return h("span", { class: "bi" }, h("span", { class: "th" }, th),
    j ? h("span", { class: "jp", lang: "ja" }, j) : h("span", { class: "jp pending" }, "[รอแปล]"));
};
// Content names (work items, categories). Admin views show the [รอแปล] marker (Handover §8);
// planning views show the Japanese line only when a reviewed name exists.
export const biName = (th, jp, { admin = false } = {}) =>
  jp || admin ? bi([th, jp || null]) : h("span", { class: "bi" }, h("span", { class: "th" }, th));

// ── toast ──
let toastBox;
export const toast = (msg, kind = "ok", ms = 3200) => {
  toastBox ??= document.body.appendChild(h("div", { class: "toasts", role: "status", "aria-live": "polite" }));
  const t = h("div", { class: `toast ${kind}` },
    tile3d(kind === "ok" ? "check" : kind === "bad" ? "alert" : "info", kind === "ok" ? TILE.running : kind === "bad" ? TILE.leak : TILE.abnormal, 44), h("span", {}, msg));
  toastBox.append(t);
  setTimeout(() => { t.style.transition = "opacity .3s"; t.style.opacity = 0; setTimeout(() => t.remove(), 300); }, ms);
};

// ── dialog ──
export const dialog = ({ title, body, actions = [], onClose, wide }) => {
  const scrim = h("div", { class: "scrim" });
  const box = h("div", { class: "dialog", role: "dialog", "aria-modal": "true", style: wide ? { width: "min(820px,94vw)" } : null });
  const close = () => { scrim.remove(); box.remove(); document.removeEventListener("keydown", esc); onClose?.(); };
  const esc = e => e.key === "Escape" && close();
  document.addEventListener("keydown", esc);
  scrim.onclick = close;
  box.append(h("h2", {}, title), body, h("div", { class: "actions" }, actions.map(a => {
    const b = h("button", { class: `btn ${a.kind || ""}` }, a.icon ? icon(a.icon) : null, a.label);
    b.onclick = async () => { if (a.run) { b.disabled = true; try { const keep = await a.run(); if (keep !== true) close(); } finally { b.disabled = false; } } else close(); };
    return b;
  })));
  document.body.append(scrim, box);
  box.querySelector("input,select,textarea,button")?.focus();
  return close;
};

// ── API ──
export class ApiError extends Error { constructor(status, msg) { super(msg); this.status = status; } }
export const api = async (path, { method = "GET", body, form } = {}) => {
  let res;
  try {
    res = await fetch("/api" + path, {
      method, credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: form || (body ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ApiError(0, "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ — ตรวจเครือข่ายแล้วลองอีกครั้ง");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    let d = data.detail;
    if (Array.isArray(d)) d = d.map(x => x.msg).join(", ");
    throw new ApiError(res.status, d || `เกิดข้อผิดพลาด (${res.status})`);
  }
  return data;
};

// ── dates (Asia/Bangkok) ──
export const TH_MONTH = ["มกราคม","กุมภาพันธ์","มีนาคม","เมษายน","พฤษภาคม","มิถุนายน","กรกฎาคม","สิงหาคม","กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"];
export const TH_MONTH_S = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."];
export const TH_WD = ["อา","จ","อ","พ","พฤ","ศ","ส"];
export const TH_WD_L = ["อาทิตย์","จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์"];
export const JP_WD = ["日","月","火","水","木","金","土"];
export const pd = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
export const iso = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
export const hhmm = s => s ? s.slice(11, 16) : "";
export const bkkNow = () => { const n = new Date(); return new Date(n.getTime() + (n.getTimezoneOffset() + 420) * 60000); };
export const todayIso = () => iso(bkkNow());
// Status → theme semantics (§3): run = done, primary = active, abn = waiting/attention, stop = neutral
export const STATUS = {
  planned: ["แผน", "idle"], in_progress: ["กำลังทำ", "info"], on_hold: ["พักงาน", "idle"],
  pending_review: ["รอตรวจ", "warn"], completed: ["เสร็จ", "ok"], cancelled: ["ยกเลิก", "idle"],
};
export const statusPill = s => { const [t, k] = STATUS[s] || STATUS.planned; return h("span", { class: `pill ${k}` }, t); };

// ── heat strip (operational day 08:00 → 08:00) ──
const toMin = t => { const [a, b] = t.split(":").map(Number); return a * 60 + b; };
export const heatStrip = (bands, { nowIso, opDay, big } = {}) => {
  const segs = [...(bands?.day?.segments || []), ...(bands?.night?.segments || [])];
  const strip = h("div", { class: "heat", style: big ? { height: "22px", borderRadius: "11px" } : null, role: "img",
    "aria-label": "ช่วงเวลา 08:00 ถึง 08:00 วันถัดไป: กะกลางวันและกะกลางคืน" });
  for (const s of segs) {
    let a = toMin(s.start) - 480, b = toMin(s.end) - 480;
    if (a < 0) a += 1440; if (b <= 0) b += 1440;
    strip.append(h("i", { class: s.tone, style: { width: `${((b - a) / 1440) * 100}%` }, title: `${s.start}–${s.end}` }));
  }
  if (nowIso && opDay) {
    const start = new Date(`${opDay}T08:00:00+07:00`).getTime();
    const frac = (new Date(nowIso).getTime() - start) / 864e5;
    if (frac >= 0 && frac <= 1) strip.append(h("span", { class: "heat-now", style: { left: `${frac * 100}%` } }));
  }
  const marks = [[0, "08:00"], [4, "12:00"], [9, "17:00"], [12, "20:00"], [16, "00:00"], [21, "05:00"], [24, "08:00"]];
  const scale = h("div", { class: "heat-scale" }, marks.map(([o, t], i) =>
    h("span", { class: [4, 21].includes(o) ? "minor" : null, style: { left: `${(o / 24) * 100}%`, transform: i === 0 ? "none" : i === marks.length - 1 ? "translateX(-100%)" : "translateX(-50%)" } }, t)));
  return h("div", { class: "heat-wrap" }, strip, scale);
};

// ── press ripple on every button (theme §7) ──
document.addEventListener("pointerdown", e => {
  const b = e.target.closest?.(".btn"); if (!b || b.disabled) return;
  const r = b.getBoundingClientRect(), d = Math.max(r.width, r.height);
  const sp = document.createElement("span"); sp.className = "ripple";
  Object.assign(sp.style, { width: `${d}px`, height: `${d}px`, left: `${e.clientX - r.left - d / 2}px`, top: `${e.clientY - r.top - d / 2}px` });
  b.append(sp); setTimeout(() => sp.remove(), 600);
});
