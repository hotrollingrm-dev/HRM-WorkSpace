import { h, icon, bi, biName, T, toast, tile3d, TILE, dialog, api, ApiError, TH_MONTH, TH_MONTH_S, TH_WD, TH_WD_L,
  pd, iso, hhmm, todayIso, statusPill, heatStrip, STATUS , art } from "./ui.js";
import { loginView, millArt } from "./login.js";

const RANK = { viewer: 0, leader: 1, foreman: 2, admin: 3 };
const S = {
  me: null, master: [], settings: {},
  ym: null,                 // {y, m}
  view: null,               // plan view payload
  qe: { cat: null, sub: null, item: null, dates: new Set(), shift: "", start: "", end: "", notes: "", adhoc: false, title: "", q: "" },
};
const can = r => S.me && RANK[S.me.role] >= RANK[r];
const app = document.getElementById("app");

// ───────────────────────── boot / router ─────────────────────────
async function boot() {
  try { S.me = await api("/me"); }
  catch (e) { if (e.status === 401) return showLogin(); return fatal(e); }
  [S.master, S.settings] = await Promise.all([api("/master"), api("/settings")]);
  window.addEventListener("hashchange", route);
  route();
}
function showLogin() {
  app.replaceChildren(loginView(async () => { await boot(); }));
}
function fatal(e) {
  app.replaceChildren(h("div", { class: "empty", style: { minHeight: "100vh" } }, art("wifiOff", 76, "hero"),
    h("h3", {}, "เปิดระบบไม่ได้"), h("p", {}, e.message),
    h("button", { class: "btn", onclick: () => location.reload() }, "ลองใหม่")));
}
function parseHash() {
  const [, page = "plan", arg] = location.hash.split("/");
  return { page, arg };
}
function route() {
  const { page, arg } = parseHash();
  if (arg && /^\d{4}-\d{2}$/.test(arg)) S.ym = { y: +arg.slice(0, 4), m: +arg.slice(5) };
  if (!S.ym) { const t = pd(todayIso()); S.ym = { y: t.getFullYear(), m: t.getMonth() + 1 }; }
  shell(page);
  ({ plan: planPage, settings: settingsPage, import: importPage, history: historyPage }[page] || planPage)();
}
const NAV = [["plan", "calendar"], ["import", "upload"], ["history", "history"], ["settings", "gear"]];
let mainEl;
function shell(page) {
  const initials = (S.me.display_name || S.me.username).trim().slice(0, 1);
  mainEl = h("main", { class: "main", id: "main" });
  const item = (href, ic, key, current, extra = {}) => h("a", { href, "aria-current": current ? "page" : null, class: "nav-it", ...extra },
    art(ic, 30, "nav"), bi(key), h("span", { class: "tip", role: "tooltip" }, T[key]?.[0] || key[0]));
  app.replaceChildren(h("div", { class: "shell" },
    h("nav", { class: "rail glass", "aria-label": "เมนูหลัก" },
      h("div", { class: "brand" }, tile3d("slab", TILE.brand, 44), h("span", { class: "bi" }, h("b", {}, "HRM WorkSpace"), h("span", { class: "jp", lang: "ja" }, "熱間圧延 作業計画"))),
      NAV.map(([k, ic]) => item(`#/${k}${k === "plan" ? `/${ymStr()}` : ""}`, ic, k, page === k)),
      h("div", { class: "nav-sep" }),
      item("/m.html", "sun", ["งานวันนี้ (มือถือ)", "今日の作業"], false, { title: "เปิดหน้ามือถือ / tablet" }),
      h("div", { class: "spacer" }),
      h("button", { class: "me", title: "ออกจากระบบ", onclick: logout },
        h("span", { class: "av" }, initials), h("span", { class: "bi" }, h("b", {}, S.me.display_name), h("span", { class: "jp" }, S.me.role)), icon("logout"))),
    mainEl));
}
async function logout() {
  await api("/auth/logout", { method: "POST" }).catch(() => {});
  location.hash = ""; showLogin();
}
const ymStr = (ym = S.ym) => `${ym.y}-${String(ym.m).padStart(2, "0")}`;
const shiftMonth = d => { let { y, m } = S.ym; m += d; if (m < 1) { m = 12; y--; } if (m > 12) { m = 1; y++; } location.hash = `#/plan/${y}-${String(m).padStart(2, "0")}`; };
const err = e => toast(e instanceof ApiError ? e.message : String(e), "bad", 5000);

// master lookups
const allItems = () => S.master.flatMap(c => c.subcategories.flatMap(s => s.items.map(i => ({ ...i, sub: s, cat: c }))));
const itemById = id => allItems().find(i => i.id === id);
const catById = id => S.master.find(c => c.id === id);

// ───────────────────────── PLAN PAGE ─────────────────────────
async function planPage() {
  mainEl.replaceChildren(h("div", { class: "topbar" }, h("div", { class: "skeleton", style: { width: "320px", height: "46px" } })));
  try { S.view = await api(`/plans/${S.ym.y}/${S.ym.m}`); } catch (e) { return err(e); }
  S.scrolledToToday = false;
  renderPlan();
}
function renderPlan() {
  const v = S.view, p = v.plan;
  const status = p.revision === 0
    ? h("span", { class: "pill warn" }, "ยังไม่เคย Publish")
    : p.draft_dirty ? h("span", { class: "pill warn" }, "มีการแก้ไขที่ยังไม่ Publish")
      : h("span", { class: "pill ok" }, "Publish แล้ว");
  const top = h("div", { class: "topbar" },
    h("div", { class: "title" },
      h("div", {},
        h("div", { class: "month-title" }, TH_MONTH[p.month - 1], " ", h("span", { class: "yr" }, String(p.year + 543))),
        h("div", { class: "month-sub", lang: "ja" }, `${p.year}年${p.month}月 の月間計画`))),
    h("div", { style: { display: "flex", gap: "6px", marginLeft: "8px" } },
      h("button", { class: "btn icon", "aria-label": "เดือนก่อน", onclick: () => shiftMonth(-1) }, icon("chevL")),
      h("button", { class: "btn icon", "aria-label": "เดือนถัดไป", onclick: () => shiftMonth(1) }, icon("chevR")),
      h("button", { class: "btn ghost", onclick: () => { const t = pd(todayIso()); location.hash = `#/plan/${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}`; } }, "เดือนนี้")),
    h("div", { class: "grow" }),
    h("div", { class: "top-actions" },
    status,
    h("span", { class: "revtag", title: p.last_published_at ? `Publish ล่าสุด ${p.last_published_at.replace("T", " ").slice(0, 16)}` : "" },
      p.revision ? `REV.${String(p.revision).padStart(2, "0")}` : "REV.—"),
    can("leader") ? h("button", { class: "btn ghost collapse", onclick: copyPrior, "aria-label": T.copyPrior[0], title: T.copyPrior[0] }, icon("copy"), bi("copyPrior")) : null,
    can("leader") ? h("button", { class: "btn collapse", onclick: exportDialog, "aria-label": T.export[0], title: T.export[0] }, icon("download"), bi("export")) : null,
    can("leader") ? h("button", { class: "btn ink qe-toggle", "aria-expanded": String(!!S.qeOpen), onclick: () => toggleQE() }, icon("plus"), bi("quick")) : null,
    h("button", { class: "btn primary", onclick: publishDialog, disabled: p.revision > 0 && !p.draft_dirty }, icon("send"), bi("publish"))),
  );
  const board = h("section", { class: "board glass", "aria-label": "ตารางแผนรายเดือน" },
    h("div", { class: "legend" },
      h("span", {}, h("i", { class: "g", style: { "--cc": "var(--s-1)" } }), "แผน (ทั้งวัน)"),
      h("span", {}, h("i", { class: "g timed", style: { "--cc": "var(--s-1)" } }), "มีเวลา"),
      h("span", {}, h("i", { class: "g D", style: { "--cc": "var(--s-1)" } }), "กะกลางวัน D"),
      h("span", {}, h("i", { class: "g N", style: { "--cc": "var(--s-1)" } }), "กะกลางคืน N"),
      h("span", {}, h("i", { class: "g review" }, "?"), "รอตรวจ"),
      h("span", {}, h("i", { class: "g done" }, icon("check")), "เสร็จ (ยืนยันแล้ว)"),
      h("span", { style: { marginLeft: "auto" } }, "คลิกช่องว่าง = เพิ่ม  ·  คลิกช่องที่มีงาน หรือหัววันที่ = ดูรายละเอียดวัน")),
    h("div", { class: "matrix-wrap" }, matrix()));
  const planner = h("div", { class: `planner ${S.qeOpen ? "qe-open" : ""}`, style: { position: "relative" } }, board,
    h("div", { class: "qe-scrim", onclick: () => toggleQE(false) }), quickEntry());
  if (p.draft_dirty && p.revision > 0) {
    planner.append(h("div", { class: "pubbar", role: "status" }, h("span", { class: "dot", style: { "--c": "var(--abn)" } }),
      `มือถือยังแสดง REV.${String(p.revision).padStart(2, "0")} — แผนที่แก้ไขจะเห็นหลัง Publish`,
      h("button", { class: "btn primary", onclick: publishDialog }, icon("send"), "Publish ตอนนี้")));
  }
  mainEl.replaceChildren(top, planner);
  if (!S.scrolledToToday) {           // tablets: bring today's column into view once
    S.scrolledToToday = true;
    const wrap = document.querySelector(".matrix-wrap"), th = wrap?.querySelector(".dh.today");
    if (wrap && th && wrap.scrollWidth > wrap.clientWidth) wrap.scrollLeft = Math.max(0, th.offsetLeft - (wrap.querySelector(".namecol")?.offsetWidth || 240) - th.offsetWidth * 3);
  }
}
function toggleQE(open = !S.qeOpen) {
  S.qeOpen = open;
  document.querySelector(".planner")?.classList.toggle("qe-open", open);
  document.querySelector(".qe-toggle")?.setAttribute("aria-expanded", String(open));
}

function matrix() {
  const v = S.view, days = v.days, today = todayIso();
  const byCell = new Map(), lane = new Map();
  for (const e of v.entries) {
    if (e.work_item_id) { const k = `${e.work_item_id}|${e.date}`; (byCell.get(k) || byCell.set(k, []).get(k)).push(e); }
    else (lane.get(e.date) || lane.set(e.date, []).get(e.date)).push(e);
  }
  const dayCls = d => { const w = pd(d).getDay(); return [w === 0 || w === 6 ? "we" : "", v.holidays[d] ? "hol" : "", d === today ? "today" : ""].join(" "); };
  const head = h("tr", {}, h("th", { class: "namecol" }, bi("item")),
    days.map(d => { const dt = pd(d); return h("th", { class: `dh ${dayCls(d)}`, title: v.holidays[d] || "", onclick: () => dayDrawer(d), scope: "col" },
      h("span", { class: "n" }, dt.getDate()), h("span", { class: "w" }, TH_WD[dt.getDay()])); }));
  const body = h("tbody");
  // schedule lane
  // shift lane: which team is scheduled D / N (from the confirmed group calendar)
  if (Object.keys(v.shifts || {}).length) {
    body.append(h("tr", { class: "shiftlane" },
      h("td", { class: "namecol" }, h("div", { class: "rowname" }, icon("sun"), h("div", { class: "nm" }, bi(["ทีมเข้ากะ", "シフト班"])), h("span", { class: "meta lanekey" }, h("b", { class: "tD" }, "บน D"), h("b", { class: "tN" }, "ล่าง N")))),
      days.map(d => { const c = v.shifts[d] || {}; const t = k => Object.keys(c).filter(x => c[x] === k).join("");
        const shut = Object.values(c).every(x => x === "S") && Object.keys(c).length;
        return h("td", { class: `sc ${dayCls(d)}`, title: shut ? "Factory shutdown" : `D: ทีม ${t("D") || "-"} · N: ทีม ${t("N") || "-"}` },
          shut ? h("span", { class: "shut" }, "S") : [h("span", { class: "tD" }, t("D")), h("span", { class: "tN" }, t("N"))]); })));
  }
  body.append(h("tr", { class: "lane" },
    h("td", { class: "namecol" }, h("div", { class: "rowname" }, icon("users"), h("div", { class: "nm" }, bi("schedule")), h("span", { class: "meta" }, "นำเข้าและเฉพาะกิจ"))),
    days.map(d => { const es = lane.get(d) || []; const un = es.filter(e => !e.start_at).length;
      return h("td", { class: `c ${dayCls(d)}`, onclick: () => dayDrawer(d), title: es.length ? `${es.length} รายการ${un ? ` (ยังไม่กำหนดเวลา ${un})` : ""}` : "" },
        es.length ? h("span", { class: `lanecount ${un ? "un" : ""}` }, es.length) : null); })));
  const rows = new Set(v.rows);
  const items = allItems().filter(i => rows.has(i.id));
  if (!items.length) {
    body.append(h("tr", {}, h("td", { colspan: days.length + 1 },
      h("div", { class: "empty" }, art("grid", 76, "hero"), h("h3", {}, "เดือนนี้ยังไม่มีแถวงาน"),
        h("p", {}, "เลือกงานและวันที่จากแผงลงงานด่วนทางขวา หรือคัดลอกแถวงานจากเดือนก่อน"),
        can("leader") ? h("div", { style: { display: "flex", gap: "8px" } },
          h("button", { class: "btn", onclick: addRowsDialog }, icon("plus"), bi("addRow")),
          h("button", { class: "btn", onclick: copyPrior }, icon("copy"), bi("copyPrior"))) : null))));
  }
  let lastCat = null;
  for (const it of items) {
    if (it.cat.id !== lastCat) {
      lastCat = it.cat.id;
      body.append(h("tr", { class: "cat" }, h("td", { class: "namecol" }, h("div", { class: "catname" },
        h("span", { class: "sw", style: { background: it.cat.color } }), biName(it.cat.name_th, it.cat.name_jp))),
        h("td", { colspan: days.length })));
    }
    body.append(h("tr", {},
      h("td", { class: "namecol" }, h("div", { class: "rowname" },
        h("div", { class: "nm" }, biName(it.name_th, it.name_jp)),
        it.location ? h("span", { class: "sub" }, it.location) : null,
        h("span", { class: "meta", title: "ความถี่ตามเอกสารต้นฉบับ (ข้อความ ยังไม่คำนวณรอบ)" }, it.frequency_label),
        can("leader") ? h("button", { class: "rm", title: "เอาแถวออกจากเดือนนี้", onclick: () => removeRow(it) }, icon("x")) : null)),
      days.map(d => cell(it, d, byCell.get(`${it.id}|${d}`) || [], dayCls(d)))));
  }
  if (items.length && can("leader")) {
    body.append(h("tr", {}, h("td", { class: "namecol" }, h("div", { class: "rowname" },
      h("button", { class: "btn ghost", onclick: addRowsDialog }, icon("plus"), bi("addRow")))), h("td", { colspan: days.length })));
  }
  return h("table", { class: "mx" }, h("thead", {}, head), body);
}
function cell(it, d, es, cls) {
  const td = h("td", { class: `c ${cls}`, "data-item": it.id, "data-date": d });
  if (es.length) {
    const st = es.map(e => e.progress.status);
    const done = st.every(s => s === "completed"), review = st.some(s => s === "pending_review");
    const e0 = es[0];
    const g = h("i", { class: `g ${done ? "done" : review ? "review" : ""} ${!done && !review && e0.shift ? e0.shift : ""} ${e0.start_at ? "timed" : ""} ${es.length > 1 ? "multi" : ""}`,
      style: { "--cc": it.cat.color }, "data-n": es.length > 1 ? es.length : null }, done ? icon("check") : review ? "?" : "");
    td.append(g);
    td.title = es.map(e => `${e.title_th}${e.start_at ? ` ${hhmm(e.start_at)}–${hhmm(e.end_at)}` : ""} · ${STATUS[e.progress.status][0]}`).join("\n");
    td.onclick = () => dayDrawer(d, e0.uid);
  } else if (can("leader")) {
    td.title = `เพิ่ม ${it.name_th} วันที่ ${pd(d).getDate()}`;
    td.onclick = async () => {
      td.append(h("i", { class: "g", style: { "--cc": it.cat.color, opacity: .5 } }));
      try { await api(`/plans/${S.ym.y}/${S.ym.m}/toggle`, { method: "POST", body: { work_item_id: it.id, date: d } }); await refreshPlan(); }
      catch (e) { err(e); td.replaceChildren(); }
    };
  }
  return td;
}
async function refreshPlan() {
  const sc = document.querySelector(".matrix-wrap"); const pos = sc ? [sc.scrollLeft, sc.scrollTop] : null;
  const qeScroll = document.querySelector(".qe-body")?.scrollTop;
  S.view = await api(`/plans/${S.ym.y}/${S.ym.m}`);
  renderPlan();
  const sc2 = document.querySelector(".matrix-wrap"); if (sc2 && pos) [sc2.scrollLeft, sc2.scrollTop] = pos;
  const q2 = document.querySelector(".qe-body"); if (q2 && qeScroll) q2.scrollTop = qeScroll;
}

// ── Quick Entry panel ──
function recentIds() { try { return JSON.parse(localStorage.getItem("hrm.recent") || "[]"); } catch { return []; } }
function pushRecent(id) { try { localStorage.setItem("hrm.recent", JSON.stringify([id, ...recentIds().filter(x => x !== id)].slice(0, 6))); } catch {} }
function quickEntry() {
  const q = S.qe;
  const panel = h("aside", { class: "qe glass", "aria-label": "ลงงานด่วน" });
  if (!can("leader")) {
    panel.append(h("div", { class: "empty" }, art("info", 76, "hero"), h("h3", {}, "ดูอย่างเดียว"), h("p", {}, "บทบาทของคุณดูแผนได้ แต่แก้ไขไม่ได้ ติดต่อ Foreman หากต้องการสิทธิ์")));
    return panel;
  }
  const redraw = () => panel.replaceWith(quickEntry());
  const cats = S.master.filter(c => c.active && !c.is_schedule);
  const cat = cats.find(c => c.id === q.cat);
  const subs = cat ? cat.subcategories.filter(s => s.active) : [];
  const items = q.q
    ? allItems().filter(i => i.active && i.sub.active && i.cat.active && `${i.name_th} ${i.sub.name_th} ${i.location}`.toLowerCase().includes(q.q.toLowerCase()))
    : (subs.find(s => s.id === q.sub)?.items.filter(i => i.active) || []).map(i => ({ ...i, sub: subs.find(s => s.id === q.sub), cat }));
  const item = q.item ? itemById(q.item) : null;
  const recent = recentIds().map(itemById).filter(Boolean);

  const pick = (i) => { q.item = i.id; q.cat = i.cat.id; q.sub = i.sub.id; q.q = ""; redraw(); };
  let stepNo = 0; const nx = () => String(++stepNo);
  const body = h("div", { class: "qe-body" });

  body.append(h("div", { class: "seg", style: { marginBottom: "14px" } },
    h("button", { "aria-pressed": String(!q.adhoc), onclick: () => { q.adhoc = false; redraw(); } }, "งานจากข้อมูลหลัก"),
    h("button", { "aria-pressed": String(q.adhoc), onclick: () => { q.adhoc = true; redraw(); } }, "งานเฉพาะกิจ")));

  if (!q.adhoc) {
    if (recent.length) body.append(h("div", { class: "qe-step" }, h("div", { class: "lbl" }, icon("star"), "ใช้ล่าสุด"),
      h("div", { class: "chips" }, recent.map(i => h("button", { class: "chip", "aria-pressed": String(q.item === i.id), onclick: () => pick(i) },
        h("span", { class: "sw", style: { background: i.cat.color } }), i.name_th, i.location ? ` · ${i.location}` : "")))));
    body.append(h("div", { class: "qe-step " + (cat ? "done" : "") }, h("div", { class: "lbl" }, h("b", {}, nx()), bi("category")),
      h("div", { class: "chips" }, cats.map(c => h("button", { class: "chip", "aria-pressed": String(q.cat === c.id),
        onclick: () => { q.cat = c.id; q.sub = c.subcategories.find(s => s.active)?.id ?? null; q.item = null; q.q = ""; redraw(); } },
        h("span", { class: "sw", style: { background: c.color } }), c.name_th)))));
    if (cat) body.append(h("div", { class: "qe-step " + (q.sub ? "done" : "") }, h("div", { class: "lbl" }, h("b", {}, nx()), bi("subcategory")),
      h("div", { class: "chips" }, subs.map(s => h("button", { class: "chip", "aria-pressed": String(q.sub === s.id), onclick: () => { q.sub = s.id; q.item = null; redraw(); } }, s.name_th)))));
    const search = h("input", { class: "input", placeholder: "ค้นหางานทั้งหมด…", value: q.q, "aria-label": "ค้นหางาน" });
    search.oninput = () => { q.q = search.value; const pos = search.selectionStart; redraw(); const n = document.querySelector(".qe .search input"); n?.focus(); n?.setSelectionRange(pos, pos); };
    body.append(h("div", { class: "qe-step " + (item ? "done" : "") }, h("div", { class: "lbl" }, h("b", {}, nx()), bi("item")),
      h("div", { class: "search" }, icon("search"), search),
      items.length ? h("div", { class: "itemlist", role: "listbox" }, items.map(i => h("button", { role: "option", "aria-pressed": String(q.item === i.id), onclick: () => pick(i) },
        h("span", { class: "sw", style: { width: "8px", height: "8px", borderRadius: "2px", background: i.cat.color } }),
        h("span", {}, i.name_th, i.location ? h("span", { style: { color: "var(--steel-2)" } }, ` · ${i.location}`) : ""),
        h("span", { class: "fq" }, i.frequency_label))))
        : h("p", { class: "hint" }, q.q ? "ไม่พบงานที่ค้นหา — เพิ่มงานใหม่ได้ที่ ตั้งค่า" : "เลือกหมวดและหมวดย่อย หรือพิมพ์ค้นหา")));
  } else {
    const t = h("input", { class: "input", placeholder: "เช่น ตรวจสอบ Cover SUS ที่ Mill FM", value: q.title });
    t.oninput = () => { q.title = t.value; foot(); };
    const sel = h("select", { class: "input" }, S.master.filter(c => c.active).map(c => h("option", { value: c.id, selected: q.cat === c.id }, c.name_th)));
    sel.onchange = () => { q.cat = +sel.value; };
    if (!q.cat || !catById(q.cat)) q.cat = S.master.find(c => c.is_schedule)?.id ?? S.master[0]?.id;
    body.append(h("div", { class: "qe-step" }, h("div", { class: "lbl" }, h("b", {}, nx()), "ชื่องาน"), t),
      h("div", { class: "qe-step" }, h("div", { class: "lbl" }, h("b", {}, nx()), bi("category")), sel));
  }

  // dates
  const days = S.view.days, today = todayIso();
  const taken = new Set(S.view.entries.filter(e => e.work_item_id && e.work_item_id === q.item).map(e => e.date));
  for (const d of [...q.dates]) if (!days.includes(d)) q.dates.delete(d);
  const cal = h("div", { class: "minical", role: "group", "aria-label": "เลือกวันที่ (เลือกได้หลายวัน)" },
    TH_WD.map(w => h("div", { class: "wd" }, w)));
  const lead = pd(days[0]).getDay();
  for (let i = 0; i < lead; i++) cal.append(h("span"));
  let painting = null;
  for (const d of days) {
    const dt = pd(d), w = dt.getDay();
    const b = h("button", { type: "button", "aria-pressed": String(q.dates.has(d)),
      class: `${w === 0 || w === 6 ? "we" : ""} ${S.view.holidays[d] ? "hol" : ""} ${taken.has(d) ? "has" : ""} ${d === today ? "today" : ""}`,
      style: item ? { "--cc": item.cat.color } : null,
      title: `${TH_WD_L[w]} ${dt.getDate()}${S.view.holidays[d] ? " · " + S.view.holidays[d] : ""}${taken.has(d) ? " · มีงานนี้แล้ว" : ""}` }, dt.getDate());
    const set = on => { on ? q.dates.add(d) : q.dates.delete(d); b.setAttribute("aria-pressed", String(on)); foot(); };
    b.onpointerdown = e => { e.preventDefault(); painting = !q.dates.has(d); set(painting); };
    b.onpointerenter = () => { if (painting !== null) set(painting); };
    b.onkeydown = e => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); set(!q.dates.has(d)); } };
    cal.append(b);
  }
  document.addEventListener("pointerup", () => { painting = null; }, { once: false });
  const pickWeekday = () => {
    const first = [...q.dates].sort()[0]; if (!first) return toast("เลือกวันแรกก่อน แล้วกดอีกครั้ง", "warn");
    const w = pd(first).getDay(); days.filter(d => pd(d).getDay() === w).forEach(d => q.dates.add(d)); redraw();
  };
  body.append(h("div", { class: "qe-step " + (q.dates.size ? "done" : "") },
    h("div", { class: "lbl" }, h("b", {}, nx()), "วันที่ (ลากเพื่อเลือกหลายวัน)",
      h("span", { style: { marginLeft: "auto", display: "flex", gap: "4px" } },
        h("button", { class: "btn ghost", style: { height: "26px", padding: "0 8px", fontSize: "12px" }, onclick: pickWeekday }, "วันเดียวกันทุกสัปดาห์"),
        h("button", { class: "btn ghost", style: { height: "26px", padding: "0 8px", fontSize: "12px" }, onclick: () => { q.dates.clear(); redraw(); } }, "ล้าง"))),
    cal));

  // options
  const st = h("input", { class: "input", type: "time", value: q.start, "aria-label": "เวลาเริ่ม" });
  const en = h("input", { class: "input", type: "time", value: q.end, "aria-label": "เวลาสิ้นสุด" });
  st.onchange = () => { q.start = st.value; }; en.onchange = () => { q.end = en.value; };
  const notes = h("input", { class: "input", placeholder: "หมายเหตุ (ไม่บังคับ)", value: q.notes });
  notes.oninput = () => { q.notes = notes.value; };
  body.append(h("div", { class: "qe-step" }, h("div", { class: "lbl" }, h("b", {}, nx()), "กะ เวลา และหมายเหตุ"),
    h("div", { class: "seg", style: { marginBottom: "8px" } },
      [["", "ไม่ระบุกะ"], ["D", "กลางวัน D"], ["N", "กลางคืน N"]].map(([k, l]) =>
        h("button", { "aria-pressed": String(q.shift === k), onclick: () => { q.shift = k; redraw(); } }, k === "D" ? icon("sun") : k === "N" ? icon("moon") : null, l))),
    h("div", { class: "row2" }, st, en),
    h("p", { class: "hint", style: { margin: "6px 0 8px" } }, "ไม่ใส่เวลา = ยังไม่กำหนดเวลา · เวลาสิ้นสุดน้อยกว่าเวลาเริ่ม = ข้ามไปวันถัดไป"),
    notes));

  const footEl = h("div", { class: "qe-foot" });
  function foot() {
    const ready = q.dates.size && (q.adhoc ? q.title.trim() : q.item);
    const save = h("button", { class: "btn primary lg", disabled: !ready, onclick: saveQE }, icon("check"),
      q.dates.size ? `บันทึก ${q.dates.size} วัน` : "เลือกวันที่");
    footEl.replaceChildren(save);
  }
  async function saveQE() {
    if ((q.start && !q.end) || (!q.start && q.end)) return toast("ใส่ทั้งเวลาเริ่มและเวลาสิ้นสุด หรือเว้นว่างทั้งคู่", "warn");
    const payload = { dates: [...q.dates].sort(), shift: q.shift || null, notes: q.notes,
      ...(q.start ? { start_time: q.start, end_time: q.end } : {}),
      ...(q.adhoc ? { title_th: q.title.trim(), category_id: q.cat } : { work_item_id: q.item }) };
    try {
      const r = await api(`/plans/${S.ym.y}/${S.ym.m}/entries`, { method: "POST", body: payload });
      toast(`บันทึก ${r.created.length} รายการลงฉบับร่างแล้ว`);
      if (!q.adhoc) pushRecent(q.item);
      q.dates.clear(); q.notes = ""; q.title = "";
      await refreshPlan();
    } catch (e) { err(e); }
  }
  foot();
  panel.append(h("div", { class: "qe-h" }, h("h3", {}, bi("quick")), item ? h("span", { class: "pill glow", title: item.name_th }, item.name_th) : null,
    h("button", { class: "btn icon ghost qe-close", "aria-label": "ปิดแผงลงงาน", onclick: () => toggleQE(false) }, icon("x"))), body, footEl);
  return panel;
}

// ── Day drawer ──
function dayDrawer(d, focusUid) {
  const v = S.view, dt = pd(d);
  const es = v.entries.filter(e => e.date === d || e.op_day === d);
  const timed = es.filter(e => e.start_at).sort((a, b) => a.start_at.localeCompare(b.start_at));
  const untimed = es.filter(e => !e.start_at);
  const scrim = h("div", { class: "scrim" });
  const close = () => { scrim.remove(); dr.remove(); document.removeEventListener("keydown", esc); };
  const esc = e => e.key === "Escape" && close();
  document.addEventListener("keydown", esc); scrim.onclick = close;
  const strip = heatStrip(S.settings.planning_bands, { opDay: d });
  const lanes = h("div", { style: { position: "relative", height: `${Math.max(1, timed.length) * 8 + 4}px`, marginTop: "6px" } });
  const start = new Date(`${d}T08:00:00+07:00`).getTime();
  timed.forEach((e, i) => {
    const a = (new Date(e.start_at) - start) / 864e5, b = (new Date(e.end_at) - start) / 864e5;
    if (b < 0 || a > 1) return;
    lanes.append(h("i", { title: `${hhmm(e.start_at)}–${hhmm(e.end_at)} ${e.title_th}`, style: { position: "absolute", top: `${i * 8}px`, height: "5px", borderRadius: "3px",
      left: `${Math.max(0, a) * 100}%`, width: `${Math.max(.6, (Math.min(1, b) - Math.max(0, a)) * 100)}%`, background: e.category?.color || "var(--stop)" } }));
  });
  const list = h("div");
  const sec = (label, arr) => { if (!arr.length) return; list.append(h("div", { class: "sec" }, label, ` (${arr.length})`)); arr.forEach(e => list.append(entRow(e, d, close))); };
  sec("มีเวลา · ช่วง 08:00 วันนี้ ถึง 08:00 วันถัดไป", timed);
  sec(T.unscheduled[0], untimed);
  if (!es.length) list.append(h("div", { class: "empty" }, art("calendar", 76, "hero"), h("h3", {}, "ยังไม่มีงานในวันนี้"), h("p", {}, "คลิกช่องในตาราง หรือใช้แผงลงงานด่วนเพื่อเพิ่มงาน")));
  const dr = h("aside", { class: "drawer", role: "dialog", "aria-label": `รายละเอียดวันที่ ${dt.getDate()}` },
    h("div", { class: "drawer-h" },
      h("div", { style: { flex: 1 } }, h("div", { class: "d" }, `${dt.getDate()} ${TH_MONTH_S[dt.getMonth()]}`),
        h("div", { class: "s" }, `${TH_WD_L[dt.getDay()]}  ${dt.getFullYear() + 543}`, v.holidays[d] ? h("span", { class: "pill bad", style: { marginLeft: "8px" } }, v.holidays[d]) : null)),
      h("button", { class: "btn icon ghost", "aria-label": "ปิด", onclick: close }, icon("x"))),
    h("div", { class: "drawer-b" }, strip, lanes, list));
  document.body.append(scrim, dr);
  if (focusUid) dr.querySelector(`[data-uid="${focusUid}"]`)?.scrollIntoView({ block: "center" });
}
function entRow(e, d, closeDrawer) {
  const row = h("div", { class: "ent", "data-uid": e.uid });
  const nextDay = e.start_at && e.end_at && e.end_at.slice(0, 10) !== e.start_at.slice(0, 10);
  const shown = () => row.replaceChildren(
    h("div", { class: "tm" }, e.start_at ? [hhmm(e.start_at), h("small", {}, `ถึง ${hhmm(e.end_at)}${nextDay ? " (+1)" : ""}`)]
      : h("small", {}, e.time_slot ? { morning: "ช่วงเช้า", afternoon: "ช่วงบ่าย", other: "อื่นๆ" }[e.time_slot] : e.shift ? `กะ ${e.shift}` : "ทั้งวัน")),
    h("div", { class: "tt", style: { borderLeft: `3px solid ${e.category?.color || "var(--stop)"}`, paddingLeft: "10px" } },
      e.title_th, e.shift ? h("span", { class: "src" }, `กะ ${e.shift}`) : null,
      e.source_type === "import" ? h("span", { class: "src", title: "ตำแหน่งในไฟล์ต้นฉบับ" }, e.source_ref) : null,
      e.manually_edited ? h("span", { class: "src edited" }, "แก้หลังนำเข้า") : null,
      h("div", { class: "m" }, [e.location, e.mbo_ref ? `MBO ${e.mbo_ref}` : "", e.notes].filter(Boolean).join(" · ")),
      h("div", { style: { marginTop: "6px" } }, statusPill(e.progress.status))),
    can("leader") ? h("div", { class: "acts" },
      h("button", { class: "btn icon ghost", title: "แก้ไข", onclick: edit }, icon("edit")),
      h("button", { class: "btn icon ghost danger", title: "ลบ", onclick: del }, icon("trash"))) : h("span"));
  async function del() {
    dialog({ title: "ลบงานนี้จากฉบับร่าง?", body: h("p", {}, `${e.title_th} — วันที่ ${pd(e.date).getDate()}. ประวัติยังถูกเก็บใน REV ที่ Publish แล้ว`),
      actions: [{ label: "ยกเลิก" }, { label: "ลบงาน", kind: "danger", icon: "trash", run: async () => {
        try { await api(`/entries/${e.uid}`, { method: "DELETE" }); toast("ลบงานแล้ว"); closeDrawer(); await refreshPlan(); } catch (x) { err(x); return true; } } }] });
  }
  function edit() {
    const date = h("input", { class: "input", type: "date", value: e.date, min: S.view.days[0], max: S.view.days.at(-1) });
    const st = h("input", { class: "input", type: "time", value: hhmm(e.start_at) });
    const en = h("input", { class: "input", type: "time", value: hhmm(e.end_at) });
    const sh = h("select", { class: "input" }, [["", "ไม่ระบุกะ"], ["D", "กลางวัน D"], ["N", "กลางคืน N"]].map(([k, l]) => h("option", { value: k, selected: (e.shift || "") === k }, l)));
    const no = h("input", { class: "input", value: e.notes || "", placeholder: "หมายเหตุ" });
    row.replaceChildren(h("div"), h("div", { style: { gridColumn: "2 / 4" } },
      h("div", { class: "row2" }, h("div", { class: "field" }, h("label", {}, "วันที่"), date), h("div", { class: "field" }, h("label", {}, "กะ"), sh)),
      h("div", { class: "row2" }, h("div", { class: "field" }, h("label", {}, "เริ่ม"), st), h("div", { class: "field" }, h("label", {}, "สิ้นสุด"), en)),
      h("div", { class: "field" }, no),
      e.source_type === "import" ? h("p", { class: "hint" }, "งานนำเข้าที่แก้ไขแล้วจะไม่ถูกเขียนทับเมื่อนำเข้าไฟล์ซ้ำ") : null,
      h("div", { style: { display: "flex", gap: "8px", justifyContent: "flex-end" } },
        h("button", { class: "btn", onclick: shown }, "ยกเลิก"),
        h("button", { class: "btn ink", onclick: async () => {
          if (!!st.value !== !!en.value) return toast("ใส่ทั้งเวลาเริ่มและสิ้นสุด หรือเว้นว่างทั้งคู่", "warn");
          try {
            await api(`/entries/${e.uid}`, { method: "PATCH", body: { date: date.value, shift: sh.value, notes: no.value,
              ...(st.value ? { start_time: st.value, end_time: en.value } : { clear_time: true }) } });
            toast("บันทึกการแก้ไขแล้ว"); closeDrawer(); await refreshPlan(); dayDrawer(date.value, e.uid);
          } catch (x) { err(x); } } }, icon("check"), "บันทึก"))));
  }
  shown();
  return row;
}

// ── row management / dialogs ──
function addRowsDialog() {
  const have = new Set(S.view.rows);
  const sel = new Set();
  const list = h("div", { style: { maxHeight: "52vh", overflow: "auto" } });
  for (const c of S.master.filter(c => c.active && !c.is_schedule)) {
    list.append(h("div", { class: "sec", style: { fontWeight: 600, margin: "12px 0 6px", display: "flex", gap: "8px", alignItems: "center" } },
      h("span", { class: "sw", style: { width: "10px", height: "10px", borderRadius: "3px", background: c.color, display: "inline-block" } }), c.name_th));
    for (const s of c.subcategories.filter(s => s.active)) for (const i of s.items.filter(i => i.active)) {
      const cb = h("input", { type: "checkbox", checked: have.has(i.id), disabled: have.has(i.id) });
      cb.onchange = () => cb.checked ? sel.add(i.id) : sel.delete(i.id);
      list.append(h("label", { class: "toggle", style: { padding: "6px 0" } }, cb, `${s.name_th} · ${i.name_th}`, i.location ? h("span", { class: "hint" }, i.location) : null));
    }
  }
  dialog({ title: "เพิ่มแถวงานในเดือนนี้", body: list, actions: [{ label: "ยกเลิก" }, { label: "เพิ่มแถว", kind: "ink", icon: "plus", run: async () => {
    if (!sel.size) return;
    try { await api(`/plans/${S.ym.y}/${S.ym.m}/rows`, { method: "POST", body: { work_item_ids: [...sel] } }); await refreshPlan(); toast(`เพิ่ม ${sel.size} แถวแล้ว`); } catch (e) { err(e); return true; } } }] });
}
async function removeRow(it) {
  try { await api(`/plans/${S.ym.y}/${S.ym.m}/rows/${it.id}`, { method: "DELETE" }); await refreshPlan(); toast("เอาแถวออกแล้ว"); } catch (e) { err(e); }
}
function copyPrior() {
  const withDates = h("input", { type: "checkbox" });
  dialog({ title: "คัดลอกจากเดือนก่อน", body: h("div", {},
    h("p", {}, "คัดลอกแถวงานจากเดือนก่อนมายังฉบับร่างเดือนนี้ งานประชุมที่นำเข้าจะไม่ถูกคัดลอก"),
    h("label", { class: "toggle" }, withDates, "คัดลอกวันที่ด้วย (ใช้วันที่ตัวเลขเดิม เช่น 5 → 5)"),
    h("p", { class: "hint" }, "ควรตรวจวันหยุดและวันในสัปดาห์อีกครั้งหลังคัดลอก")),
    actions: [{ label: "ยกเลิก" }, { label: "คัดลอก", kind: "ink", icon: "copy", run: async () => {
      try { const r = await api(`/plans/${S.ym.y}/${S.ym.m}/copy-prior?with_dates=${withDates.checked}`, { method: "POST" });
        toast(`คัดลอก ${r.rows} แถว${withDates.checked ? `, ${r.entries} งาน` : ""}`); await refreshPlan(); } catch (e) { err(e); return true; } } }] });
}
async function publishDialog() {
  let d; try { d = await api(`/plans/${S.ym.y}/${S.ym.m}/pending`); } catch (e) { return err(e); }
  const n = d.added.length + d.removed.length + d.changed.length;
  const note = h("textarea", { class: "input", placeholder: "บันทึกการเปลี่ยนแปลง (แสดงในประวัติ)" });
  const nm = u => d.titles[u] ? `${d.titles[u][0]} (${pd(d.titles[u][1]).getDate()})` : d.removed_titles[u];
  const ul = (arr, f) => arr.length ? h("ul", { style: { margin: "4px 0 10px", paddingLeft: "18px", maxHeight: "120px", overflow: "auto", fontSize: "13px" } }, arr.slice(0, 40).map(x => h("li", {}, f(x))), arr.length > 40 ? h("li", {}, `…อีก ${arr.length - 40}`) : null) : null;
  dialog({ title: `Publish เป็น REV.${String(d.next_revision).padStart(2, "0")}`, body: h("div", {},
    h("p", {}, n ? "หลัง Publish ทีมจะเห็นแผนนี้บนมือถือทันที" : "ไม่มีการเปลี่ยนแปลงจาก REV ล่าสุด"),
    h("div", { class: "kpis", style: { margin: "12px 0" } },
      h("div", { class: "kpi" }, h("b", { style: { color: "var(--ok)" } }, d.added.length), h("span", {}, "เพิ่ม")),
      h("div", { class: "kpi" }, h("b", { style: { color: "var(--info)" } }, d.changed.length), h("span", {}, "เปลี่ยน")),
      h("div", { class: "kpi" }, h("b", { style: { color: "var(--bad)" } }, d.removed.length), h("span", {}, "ลบ"))),
    ul(d.changed, c => `${nm(c.uid)}: ${c.fields.join(", ")}`), ul(d.removed, nm),
    h("p", { class: "hint" }, "การแจ้งเตือนไปมือถือยังไม่เปิดใช้ (Milestone 5) — ทีมจะเห็นแผนเมื่อเปิดแอป"), note),
    actions: [{ label: "ยกเลิก" }, { label: "Publish", kind: "primary", icon: "send", run: async () => {
      if (!n) return;
      try { const r = await api(`/plans/${S.ym.y}/${S.ym.m}/publish`, { method: "POST", body: { note: note.value } });
        toast(`Publish แล้ว — REV.${String(r.revision).padStart(2, "0")}`); await refreshPlan(); } catch (e) { err(e); return true; } } }] });
}
function exportDialog() {
  const p = S.view.plan;
  let src = p.revision ? "published" : "draft";
  const seg = h("div", { class: "seg" });
  const draw = () => seg.replaceChildren(...[["published", `ฉบับ Publish (REV.${String(p.revision).padStart(2, "0")})`], ["draft", "ฉบับร่างปัจจุบัน"]].map(([k, l]) =>
    h("button", { "aria-pressed": String(src === k), disabled: k === "published" && !p.revision, onclick: () => { src = k; draw(); } }, l)));
  draw();
  dialog({ title: "ส่งออก Excel ตามแบบฟอร์ม HRM", body: h("div", {},
    h("p", {}, "ใช้ไฟล์ต้นฉบับ เอกสาร HRM_Work_Management เป็นแม่แบบ คงรูปแบบ หัวตาราง สี และการตั้งค่าพิมพ์เดิม"),
    seg,
    h("ul", { class: "hint", style: { paddingLeft: "18px", lineHeight: 1.7 } },
      h("li", {}, `แผน = ${S.settings.export_mark_mode?.planned || "●"}  เสร็จ (ยืนยัน) = ${S.settings.export_mark_mode?.completed || "✔"}  (รอยืนยัน Q-EX1)`),
      h("li", {}, "ประชุมที่นำเข้าและงานเฉพาะกิจอยู่ใน sheet Daily Detail"),
      h("li", {}, "ส่วนตารางกะเว้นว่าง จนกว่าจะได้ไฟล์รายชื่อพนักงาน"))),
    actions: [{ label: "ยกเลิก" }, { label: "สร้างไฟล์", kind: "ink", icon: "download", run: async () => {
      try { const r = await api("/exports", { method: "POST", body: { year: p.year, month: p.month, source: src } });
        const a = h("a", { href: r.url, download: r.file }); document.body.append(a); a.click(); a.remove(); toast(`สร้าง ${r.file} แล้ว`); }
      catch (e) { err(e); return true; } } }] });
}

// ───────────────────────── SETTINGS ─────────────────────────
// Category identity colours — drawn from the theme's system/status palette so they sit with the semantic colours
const PALETTE = ["#4F7FEA", "#1E9E91", "#D69330", "#6F4FE0", "#0B8B70", "#2F74E8", "#B07800", "#4A6488", "#C2417A", "#657083"];
const SEL = { cat: null, sub: null, item: null, mode: null };
async function settingsPage() {
  S.master = await api("/master");
  const c = S.master.find(x => x.id === SEL.cat) || S.master[0];
  SEL.cat = c?.id;
  const s = c?.subcategories.find(x => x.id === SEL.sub) || c?.subcategories[0];
  SEL.sub = s?.id;
  const col = (title, arr, cur, onPick, onAdd, render) => h("div", { class: "panel" },
    h("div", { class: "panel-h" }, h("h3", {}, title), h("span", { class: "grow", style: { flex: 1 } }),
      can("leader") && onAdd ? h("button", { class: "btn icon ghost", title: "เพิ่ม", onclick: onAdd }, icon("plus")) : null),
    h("div", { class: "col-list" }, arr.length ? arr.map(x => h("button", { class: `it ${x.active ? "" : "off"}`, "aria-current": String(cur === x.id), onclick: () => onPick(x) }, render(x)))
      : h("p", { class: "hint", style: { padding: "12px" } }, "ยังไม่มีรายการ — กด + เพื่อเพิ่ม")));
  const editor = h("div", { class: "panel", style: { position: "sticky", top: "0" } });
  const editTarget = SEL.mode === "item" ? s?.items.find(i => i.id === SEL.item) : SEL.mode === "sub" ? s : c;
  fillEditor(editor, SEL.mode || "cat", editTarget, c, s);
  const page = h("div", { class: "page" },
    h("div", { class: "miller" },
      col(bi("category"), S.master, SEL.cat, x => { SEL.cat = x.id; SEL.sub = null; SEL.mode = "cat"; settingsPage(); },
        () => { SEL.mode = "newcat"; fillEditor(editor, "newcat"); },
        x => [h("span", { class: "sw", style: { background: x.color } }), biName(x.name_th, x.name_jp, { admin: true }), h("span", { class: "cnt" }, x.subcategories.length)]),
      col(bi("subcategory"), c?.subcategories || [], SEL.sub, x => { SEL.sub = x.id; SEL.mode = "sub"; settingsPage(); },
        c ? () => { SEL.mode = "newsub"; fillEditor(editor, "newsub", null, c); } : null,
        x => [biName(x.name_th, x.name_jp, { admin: true }), h("span", { class: "cnt" }, x.items.length)]),
      col(bi("item"), s?.items || [], SEL.mode === "item" ? SEL.item : null, x => { SEL.item = x.id; SEL.mode = "item"; settingsPage(); },
        s ? () => { SEL.mode = "newitem"; fillEditor(editor, "newitem", null, c, s); } : null,
        x => [biName(x.name_th, x.name_jp, { admin: true }), h("span", { class: "cnt" }, x.location || x.frequency_label)]),
      editor),
    systemPanels());
  mainEl.replaceChildren(h("div", { class: "topbar" }, h("h1", { class: "page-h" }, bi("settings")), h("div", { class: "grow" }),
    h("span", { class: "hint" }, "แก้ชื่อ สี ลำดับ และเปิด/ปิดได้ — ไม่ลบจริงเพื่อรักษาประวัติแผน")), page);
}
function fillEditor(box, mode, obj, cat, sub) {
  const isNew = mode.startsWith("new");
  const kind = { cat: "category", newcat: "category", sub: "subcategory", newsub: "subcategory", item: "item", newitem: "item" }[mode];
  const o = obj || {};
  const f = {};
  const inp = (k, label, ph = "", type = "text") => { f[k] = h("input", { class: "input", type, value: o[k] ?? "", placeholder: ph }); return h("div", { class: "field" }, h("label", {}, label), f[k]); };
  const parts = [inp("name_th", "ชื่อ (ไทย)"), inp("name_jp", "ชื่อ (ญี่ปุ่น)", "[รอแปล] — ใส่เมื่อผ่านการตรวจคำแปลแล้ว")];
  let color = o.color || PALETTE[0];
  if (kind === "category") {
    const sw = h("div", { class: "swatches" });
    const drawSw = () => sw.replaceChildren(...PALETTE.map(p => h("button", { style: { background: p }, "aria-label": p, "aria-pressed": String(p === color), onclick: () => { color = p; drawSw(); } })));
    drawSw();
    parts.push(h("div", { class: "field" }, h("label", {}, "สี (ใช้แยกหมวดในตาราง)"), sw));
  }
  if (kind === "item") parts.push(inp("frequency_label", "ความถี่ (ข้อความตามเอกสาร)", "เช่น 1 เดือน/ครั้ง"), inp("location", "จุด / อุปกรณ์", "เช่น Housing"),
    inp("default_duration_min", "ระยะเวลาปกติ (นาที) — ไม่บังคับ", "", "number"));
  const act = h("input", { type: "checkbox", checked: isNew ? true : o.active });
  if (!isNew) parts.push(h("label", { class: "toggle", style: { margin: "4px 0 14px" } }, act, "ใช้งานอยู่ (ปิดเพื่อซ่อนจากการลงงานใหม่)"));
  if (o.source_ref) parts.push(h("p", { class: "srcref" }, `แหล่งที่มา: ${o.source_ref}`));
  const label = { cat: "แก้ไขหมวดหลัก", newcat: "เพิ่มหมวดหลัก", sub: "แก้ไขหมวดย่อย", newsub: `เพิ่มหมวดย่อยใน ${cat?.name_th}`, item: "แก้ไขรายการงาน", newitem: `เพิ่มงานใน ${sub?.name_th}` }[mode];
  const save = h("button", { class: "btn ink", disabled: !can("leader") }, icon("check"), isNew ? "เพิ่ม" : "บันทึก");
  save.onclick = async () => {
    const body = { name_th: f.name_th.value.trim(), name_jp: f.name_jp.value.trim() || null };
    if (!body.name_th) return toast("กรุณาใส่ชื่อภาษาไทย", "warn");
    if (kind === "category") body.color = color;
    if (kind === "item") Object.assign(body, { frequency_label: f.frequency_label.value, location: f.location.value,
      default_duration_min: f.default_duration_min.value ? +f.default_duration_min.value : null });
    if (!isNew) body.active = act.checked;
    const url = { category: "/categories", subcategory: "/subcategories", item: "/items" }[kind];
    if (mode === "newsub") body.category_id = cat.id;
    if (mode === "newitem") body.subcategory_id = sub.id;
    try {
      const r = await api(isNew ? url : `${url}/${o.id}`, { method: isNew ? "POST" : "PATCH", body });
      toast(isNew ? "เพิ่มแล้ว" : "บันทึกแล้ว");
      if (kind === "category") { SEL.cat = r.id; SEL.mode = "cat"; } else if (kind === "subcategory") { SEL.sub = r.id; SEL.mode = "sub"; } else { SEL.item = r.id; SEL.mode = "item"; }
      settingsPage();
    } catch (e) { err(e); }
  };
  box.replaceChildren(h("div", { class: "panel-h" }, h("h3", {}, label || "")),
    obj || isNew ? h("div", { style: { padding: "16px 18px" } }, parts, h("div", { style: { display: "flex", justifyContent: "flex-end" } }, save))
      : h("div", { class: "empty" }, art("edit", 76, "hero"), h("p", {}, "เลือกรายการเพื่อแก้ไข")));
}
function systemPanels() {
  const b = S.settings.planning_bands, r = S.settings.official_roster_times, mk = S.settings.export_mark_mode || {};
  const wrap = h("div", { class: "sysgrid" });
  wrap.append(h("div", { class: "panel" }, h("div", { class: "panel-h" }, h("h3", {}, bi("bands"))),
    h("div", { style: { padding: "16px 18px" } }, heatStrip(b, {}),
      h("p", { class: "hint", style: { marginTop: "12px" } }, "Timeline วางแผน: กะกลางวัน 08:00–20:00 (08–17 / 17–20) กะกลางคืน 20:00–08:00 (20–05 / 05–08) แยกด้วยสีเท่านั้น"),
      h("div", { class: "issue warn", style: { marginTop: "10px" } }, icon("alert"),
        `เวลากะตาม PDF: D ${r?.D?.start}–${r?.D?.end}, N ${r?.N?.start}–${r?.N?.end} — เก็บแยกไว้ ยังไม่ใช้คำนวณ รอยืนยัน (Q-SH1)`))));
  const mkSel = k => { const s = h("select", { class: "input", disabled: !can("admin") }, ["●", "✔", "✖"].map(x => h("option", { selected: mk[k] === x }, x)));
    s.onchange = async () => { try { S.settings.export_mark_mode = await api("/settings/export_mark_mode", { method: "PUT", body: { ...mk, [k]: s.value } }); toast("บันทึกแล้ว"); } catch (e) { err(e); } }; return s; };
  wrap.append(h("div", { class: "panel" }, h("div", { class: "panel-h" }, h("h3", {}, "เครื่องหมายใน Excel")),
    h("div", { style: { padding: "16px 18px" } }, h("div", { class: "row2" }, h("div", { class: "field" }, h("label", {}, "งานตามแผน"), mkSel("planned")),
      h("div", { class: "field" }, h("label", {}, "เสร็จ (ยืนยันแล้ว)"), mkSel("completed"))),
      h("p", { class: "hint" }, "Data validation ของแม่แบบ: ✔ ทำแล้ว · ● แผน · ✖ ไม่ได้ทำ แต่ตัวอย่างในไฟล์ใช้ ✔ ลงวันอนาคต (Q-EX1)"))));
  const users = h("div", { class: "panel" }, h("div", { class: "panel-h" }, h("h3", {}, bi("users")), h("span", { style: { flex: 1 } }),
    h("button", { class: "btn ghost", onclick: changePassword }, "เปลี่ยนรหัสผ่านของฉัน"),
    can("admin") ? h("button", { class: "btn icon ghost", title: "เพิ่มผู้ใช้", onclick: addUser }, icon("plus")) : null));
  wrap.append(users);
  wrap.append(rosterPanel());
  wrap.append(staffPanel());
  if (can("admin")) api("/users").then(list => users.append(h("div", { class: "col-list" }, list.map(u => h("div", { class: `it ${u.active ? "" : "off"}` },
    icon("user"), h("span", {}, u.display_name, h("span", { class: "hint" }, `  ${u.username}`)), h("span", { class: "cnt" }, u.role))))));
  else users.append(h("p", { class: "hint", style: { padding: "14px 18px" } }, "เฉพาะผู้ดูแลระบบ"));
  return wrap;
}
function rosterPanel() {
  const box = h("div", { class: "panel roster", style: { gridColumn: "1 / -1" } });
  let ym = { ...S.ym };
  const head = h("div", { class: "panel-h" }, h("h3", {}, bi(["ตารางกะ 3 Group", "3班2交替カレンダー"])), h("span", { class: "hint" }, "เวลากะ D 08:00–20:15 · N 20:00–08:15"), h("span", { style: { flex: 1 } }));
  const bodyEl = h("div", { style: { padding: "14px 18px 18px" } });
  box.append(head, bodyEl);
  const CODE_ORDER = ["D", "N", "H", "S"];
  async function load() {
    let m; try { m = await api(`/roster?year=${ym.y}&month=${ym.m}`); } catch (e) { return err(e); }
    const has = Object.values(m.days).some(x => Object.keys(x).length);
    const nav = h("div", { style: { display: "flex", gap: "8px", alignItems: "center", marginBottom: "10px" } },
      h("button", { class: "btn icon", "aria-label": "เดือนก่อน", onclick: () => { ym = ym.m === 1 ? { y: ym.y - 1, m: 12 } : { y: ym.y, m: ym.m - 1 }; load(); } }, icon("chevL")),
      h("b", { style: { minWidth: "140px", textAlign: "center" } }, `${TH_MONTH[ym.m - 1]} ${ym.y + 543}`),
      h("button", { class: "btn icon", "aria-label": "เดือนถัดไป", onclick: () => { ym = ym.m === 12 ? { y: ym.y + 1, m: 1 } : { y: ym.y, m: ym.m + 1 }; load(); } }, icon("chevR")),
      h("span", { style: { flex: 1 } }),
      can("leader") ? h("button", { class: `btn ${has ? "" : "primary"}`, onclick: preview }, icon("file"), has ? "ตรวจกับ PDF อีกครั้ง" : "ตรวจและนำเข้าตารางกะจาก PDF") : null);
    if (!has) {
      bodyEl.replaceChildren(nav, h("div", { class: "empty", style: { padding: "24px" } }, art("calendar", 76, "hero"), h("h3", {}, "ยังไม่มีตารางกะของเดือนนี้"),
        h("p", {}, "ข้อมูลถอดจาก ตารางกะ 3 Group.pdf (ม.ค. 2569 – มี.ค. 2570) พร้อมตรวจยอดกับคอลัมน์ WD และตารางสรุปใน PDF — กดตรวจก่อนนำเข้า")));
      return;
    }
    const days = Object.keys(m.days).sort();
    const grid = h("table", { class: "rgrid" }, h("thead", {}, h("tr", {}, h("th", {}, ""), days.map(d => { const dt = pd(d), w = dt.getDay();
      return h("th", { class: w === 0 || w === 6 ? "we" : "" }, h("b", {}, dt.getDate()), h("small", {}, TH_WD[w])); }))),
      h("tbody", {}, ["A", "B", "C"].map(t => h("tr", {}, h("th", {}, `ทีม ${t}`), days.map(d => {
        const c = m.days[d][t]; if (!c) return h("td");
        const td = h("td", { class: `rc ${c.code} ${c.fill || ""} ${c.edited ? "edited" : ""}`,
          title: `${d} ทีม ${t}: ${c.code}${c.fill === "special" ? " · ทำงานวันหยุดนักขัตฤกษ์" : c.fill === "substitution" ? " · Substitution" : ""}${c.edited ? " · แก้ไขด้วยมือ" : ""}` }, c.code);
        if (can("leader")) td.onclick = async () => {
          const next = CODE_ORDER[(CODE_ORDER.indexOf(c.code) + 1) % CODE_ORDER.length];
          try { await api(`/roster/${d}/${t}`, { method: "PATCH", body: { code: next } }); toast(`ทีม ${t} วันที่ ${pd(d).getDate()}: ${c.code} → ${next}`); load(); } catch (e) { err(e); }
        };
        return td; })))));
    bodyEl.replaceChildren(nav, h("div", { style: { overflowX: "auto" } }, grid),
      h("div", { class: "legend", style: { paddingBottom: 0 } },
        h("span", {}, h("i", { class: "rc D sw" }, "D"), "กลางวัน"), h("span", {}, h("i", { class: "rc N sw" }, "N"), "กลางคืน"),
        h("span", {}, h("i", { class: "rc H sw" }, "H"), "หยุด"), h("span", {}, h("i", { class: "rc S special sw" }, "S"), "Factory shutdown"),
        h("span", {}, h("i", { class: "rc D special sw" }, "D"), "ทำงานวันหยุดนักขัตฤกษ์"), h("span", {}, h("i", { class: "rc H substitution sw" }, "H"), "Substitution"),
        h("span", {}, h("i", { class: "rc D edited sw" }, "D"), "แก้ไขด้วยมือ"),
        can("leader") ? h("span", { style: { marginLeft: "auto" } }, "แตะช่องเพื่อเปลี่ยน D → N → H → S") : null));
  }
  async function preview() {
    let b; try { b = await api("/roster/preview", { method: "POST" }); } catch (e) { return err(e); }
    const c = b.checks;
    const row = (ok, text) => h("div", { class: `issue ${ok ? "info" : "error"}`, style: { fontSize: "14px", margin: "6px 0" } }, icon(ok ? "check" : "alert"), text);
    dialog({ title: "ตรวจตารางกะก่อนนำเข้า", wide: true, body: h("div", {},
      h("p", { class: "hint" }, `${b.source} · ${b.method}`),
      row(!c.wd_mismatches.length, `จำนวนวันทำงาน (WD) ตรงกับ PDF ${c.wd_rows_checked - c.wd_mismatches.length}/${c.wd_rows_checked} แถว (15 เดือน × 3 ทีม)`),
      ...c.wd_mismatches.map(x => row(false, x)),
      row(Object.values(c.summary_2026).every(x => x.match), `ตารางสรุปปี 2026 ตรงทุกค่า เมื่อจับคู่ ${c.group_mapping}`),
      ...Object.entries(c.summary_2026).map(([t, x]) => h("div", { class: "hint", style: { marginLeft: "24px" } },
        `ทีม ${t} (${x.label}): D ${x.counted.D} · N ${x.counted.N} · H ${x.counted.H} · S ${x.counted.S}`)),
      row(c.coverage_exceptions.every(x => x.explained_by_substitution),
        `วันที่จำนวนทีม D/N ไม่ครบ 1:1 มี ${c.coverage_exceptions.length} วัน — ตรงกับช่องสีเขียว (Substitution) ใน PDF ทั้งหมด: ${c.coverage_exceptions.map(x => x.date.slice(5)).join(", ")}`),
      row(true, `Factory shutdown ปี 2026 = ${c.shutdown_days_2026} วัน (ตามตาราง) · ช่องสีเหลือง ${c.fills.special} ช่อง (ทำงานวันหยุดนักขัตฤกษ์ / S) · สีเขียว ${c.fills.substitution} ช่อง (ตรวจจากสีพื้นในภาพ)`),
      h("div", { class: "issue warn", style: { fontSize: "14px", margin: "10px 0 0" } }, icon("alert"), `ตั้งแต่ ม.ค. 2570 เป็นข้อมูลชั่วคราว — ${c.provisional_note}`),
      h("p", { class: "hint", style: { marginTop: "12px" } }, "นำเข้าแล้วยังแก้รายวันได้ และวันที่แก้ด้วยมือจะไม่ถูกเขียนทับเมื่อนำเข้าซ้ำ")),
      actions: [{ label: "ยกเลิก" }, { label: "ยืนยันนำเข้าตารางกะ", kind: "primary", icon: "check", run: async () => {
        try { const r = await api(`/roster/${b.id}/commit`, { method: "POST" });
          toast(`นำเข้าตารางกะแล้ว: เพิ่ม ${r.added} อัปเดต ${r.updated}${r.kept_manually_edited ? ` (คงที่แก้มือ ${r.kept_manually_edited})` : ""}`); load(); }
        catch (e) { err(e); return true; } } }] });
  }
  load();
  return box;
}
function staffPanel() {
  const box = h("div", { class: "panel staff", style: { gridColumn: "1 / -1" } },
    h("div", { class: "panel-h" }, h("h3", {}, bi(["พนักงาน", "従業員"])), h("span", { class: "hint" }, "สลับทีมได้ด้วยการแตะ A / B / C ชื่อคงตามเอกสารต้นฉบับ"),
      h("span", { style: { flex: 1 } })));
  const grid = h("div", { class: "staff-grid" });
  box.append(grid);
  const draw = list => grid.replaceChildren(...["A", "B", "C"].map(t => h("div", { class: "staff-col" },
    h("div", { class: `staff-team t${t}` }, `ทีม ${t}`, h("span", {}, `${list.filter(e => e.team === t && e.active).length} คน`)),
    list.filter(e => e.team === t).map(e => {
      const pos = h("input", { class: "input", value: e.position, "aria-label": `ตำแหน่ง ${e.name}`, disabled: !can("leader") });
      pos.onchange = () => save(e, { position: pos.value });
      return h("div", { class: `staff-row ${e.active ? "" : "off"}` },
        h("div", { class: "who" }, h("b", {}, e.nickname || e.name.split(" ")[1] || e.name), h("span", {}, e.name), h("small", {}, e.code)),
        pos,
        h("div", { class: "seg", role: "group", "aria-label": `ทีมของ ${e.name}` }, ["A", "B", "C"].map(x =>
          h("button", { "aria-pressed": String(e.team === x), disabled: !can("leader"), onclick: () => e.team !== x && save(e, { team: x }) }, x))),
        h("label", { class: "toggle", title: "ใช้งานอยู่" }, h("input", { type: "checkbox", checked: e.active, disabled: !can("leader"),
          onchange: ev => save(e, { active: ev.target.checked }) })));
    }))));
  const load = () => api("/employees").then(draw).catch(err);
  const save = async (e, body) => {
    try { await api(`/employees/${e.id}`, { method: "PATCH", body }); toast(body.team ? `ย้าย ${e.nickname || e.name} ไปทีม ${body.team} แล้ว` : "บันทึกแล้ว"); load(); }
    catch (x) { err(x); }
  };
  load();
  return box;
}
function changePassword() {
  const cur = h("input", { class: "input", type: "password", autocomplete: "current-password" });
  const n1 = h("input", { class: "input", type: "password", autocomplete: "new-password" });
  const n2 = h("input", { class: "input", type: "password", autocomplete: "new-password" });
  dialog({ title: "เปลี่ยนรหัสผ่านของฉัน", body: h("div", {},
    h("div", { class: "field" }, h("label", {}, "รหัสผ่านเดิม"), cur),
    h("div", { class: "field" }, h("label", {}, "รหัสผ่านใหม่ (อย่างน้อย 6 ตัว)"), n1),
    h("div", { class: "field" }, h("label", {}, "พิมพ์รหัสผ่านใหม่อีกครั้ง"), n2)),
    actions: [{ label: "ยกเลิก" }, { label: "เปลี่ยนรหัสผ่าน", kind: "primary", run: async () => {
      if (n1.value !== n2.value) { toast("รหัสผ่านใหม่ทั้งสองช่องไม่ตรงกัน", "warn"); return true; }
      try { await api("/me/password", { method: "POST", body: { current: cur.value, new: n1.value } }); toast("เปลี่ยนรหัสผ่านแล้ว"); }
      catch (e) { err(e); return true; } } }] });
}
function addUser() {
  const f = { username: h("input", { class: "input" }), display_name: h("input", { class: "input" }), password: h("input", { class: "input", type: "password" }),
    role: h("select", { class: "input" }, [["viewer", "Viewer — ดู/ส่งตรวจ"], ["leader", "Leader — แก้ฉบับร่าง"], ["foreman", "Foreman — Publish/นำเข้า"], ["admin", "Admin"]].map(([k, l]) => h("option", { value: k }, l))) };
  dialog({ title: "เพิ่มผู้ใช้", body: h("div", {}, h("div", { class: "field" }, h("label", {}, "ชื่อผู้ใช้"), f.username), h("div", { class: "field" }, h("label", {}, "ชื่อที่แสดง"), f.display_name),
    h("div", { class: "field" }, h("label", {}, "รหัสผ่าน (อย่างน้อย 6 ตัว)"), f.password), h("div", { class: "field" }, h("label", {}, "บทบาท (ชั่วคราว รอยืนยัน Q-SY1)"), f.role)),
    actions: [{ label: "ยกเลิก" }, { label: "เพิ่มผู้ใช้", kind: "ink", run: async () => {
      try { await api("/users", { method: "POST", body: Object.fromEntries(Object.entries(f).map(([k, v]) => [k, v.value])) }); toast("เพิ่มผู้ใช้แล้ว"); settingsPage(); } catch (e) { err(e); return true; } } }] });
}

// ───────────────────────── IMPORT ─────────────────────────
const IMP = { batch: null, filter: "all" };
const ACT = { add: ["จะเพิ่ม", "ok"], skip: ["ข้าม", "idle"], skip_duplicate: ["ซ้ำ — ข้าม", "idle"], update_candidate: ["มีของเดิม", "info"],
  update: ["จะอัปเดต", "info"], conflict: ["ถูกแก้มือ — ไม่ทับ", "warn"], reject: ["ปฏิเสธ", "bad"] };
async function importPage() {
  const year = h("select", { class: "input", style: { width: "120px" } }, [2026, 2027].map(y => h("option", { value: y, selected: y === S.ym.y }, `${y + 543} (${y})`)));
  const file = h("input", { type: "file", accept: ".xlsx,.xlsm", class: "sr", id: "impfile" });
  const dz = h("label", { class: "dropzone", for: "impfile" }, icon("file", "big"),
    h("div", { style: { flex: 1 } }, h("div", { style: { fontWeight: 600, fontSize: "var(--t-lg)" } }, "ลากไฟล์ Monthly schedule มาวาง หรือคลิกเพื่อเลือก"),
      h("div", { class: "hint" }, "รองรับ .xlsx · ระบบจะแสดงตัวอย่างและตรวจวันที่ทุกแถวก่อนบันทึก ไม่มีอะไรถูกบันทึกจนกว่าจะกดยืนยัน")),
    h("div", { class: "field", style: { margin: 0 } }, h("label", {}, "ปีของไฟล์"), year), file);
  const upload = async f => {
    if (!f) return;
    const fd = new FormData(); fd.append("file", f); fd.append("year", year.value);
    dz.classList.add("over");
    try { IMP.batch = await api("/imports", { method: "POST", form: fd }); IMP.filter = "all"; renderImport(); toast("อ่านไฟล์แล้ว — ตรวจตัวอย่างก่อนยืนยัน"); }
    catch (e) { err(e); } finally { dz.classList.remove("over"); }
  };
  file.onchange = () => upload(file.files[0]);
  dz.ondragover = e => { e.preventDefault(); dz.classList.add("over"); };
  dz.ondragleave = () => dz.classList.remove("over");
  dz.ondrop = e => { e.preventDefault(); upload(e.dataTransfer.files[0]); };
  const hist = h("div", { class: "panel", style: { marginTop: "14px" } }, h("div", { class: "panel-h" }, h("h3", {}, "ประวัติการนำเข้า")));
  const body = h("div", { id: "impbody" });
  mainEl.replaceChildren(h("div", { class: "topbar" }, h("h1", { class: "page-h" }, bi("import")), h("div", { class: "grow" })),
    h("div", { class: "page" }, can("foreman") ? dz : h("p", { class: "hint" }, "การนำเข้าต้องใช้สิทธิ์ Foreman"), body, hist));
  renderImport();
  try {
    const list = await api("/imports");
    hist.append(list.length ? h("table", { class: "grid" }, h("thead", {}, h("tr", {}, ["ไฟล์", "เวลา", "สถานะ", "ผล", ""].map(x => h("th", {}, x)))),
      h("tbody", {}, list.map(b => h("tr", {}, h("td", {}, b.filename), h("td", {}, b.uploaded_at.replace("T", " ").slice(0, 16)),
        h("td", {}, h("span", { class: `pill ${b.status === "committed" ? "ok" : b.status === "reverted" ? "idle" : "warn"}` },
          { committed: "นำเข้าแล้ว", reverted: "ย้อนแล้ว", preview: "รอยืนยัน" }[b.status])),
        h("td", {}, b.summary.committed ? `เพิ่ม ${b.summary.committed.added} · อัปเดต ${b.summary.committed.updated}` : ""),
        h("td", { style: { textAlign: "right" } },
          b.status === "preview" ? h("button", { class: "btn", onclick: async () => { IMP.batch = await api(`/imports/${b.id}`); renderImport(); } }, "เปิดตัวอย่าง") : null,
          b.status === "committed" && can("foreman") ? h("button", { class: "btn danger", onclick: () => revert(b) }, icon("history"), bi("revert")) : null)))))
      : h("div", { class: "empty" }, art("upload", 76, "hero"), h("p", {}, "ยังไม่เคยนำเข้าไฟล์")));
  } catch (e) { if (e.status !== 403) err(e); }
}
function revert(b) {
  dialog({ title: "ย้อนการนำเข้านี้?", body: h("p", {}, "งานที่มาจากไฟล์นี้จะถูกนำออกจากฉบับร่าง ยกเว้นงานที่ถูกแก้ไขด้วยมือหลังนำเข้า"),
    actions: [{ label: "ยกเลิก" }, { label: "ย้อนการนำเข้า", kind: "danger", run: async () => {
      try { const r = await api(`/imports/${b.id}/revert`, { method: "POST" }); toast(`นำออก ${r.removed} รายการ${r.kept_manually_edited.length ? ` (เก็บที่แก้มือ ${r.kept_manually_edited.length})` : ""}`); importPage(); }
      catch (e) { err(e); return true; } } }] });
}
function renderImport() {
  const box = document.getElementById("impbody"); if (!box) return;
  const b = IMP.batch;
  if (!b) return box.replaceChildren();
  const counts = {}; b.rows.forEach(r => counts[r.action] = (counts[r.action] || 0) + 1);
  const rows = IMP.filter === "all" ? b.rows : IMP.filter === "issues" ? b.rows.filter(r => r.issues.some(i => i.level !== "info")) : b.rows.filter(r => r.action === IMP.filter);
  const sheets = b.summary.sheets || [];
  const editable = b.status === "preview" && can("foreman");
  const tbl = h("table", { class: "grid" }, h("thead", {}, h("tr", {}, ["ตำแหน่ง", "วันที่", "เวลา", "รายการ", "ห้อง / MBO", "ผลตรวจ", "การทำงาน"].map(x => h("th", {}, x)))),
    h("tbody", {}, rows.slice(0, 400).map(r => importRow(r, editable))));
  const kpi = (k, label, n) => h("button", { class: "kpi", "aria-pressed": String(IMP.filter === k), onclick: () => { IMP.filter = k; renderImport(); } }, h("b", {}, n ?? 0), h("span", {}, label));
  box.replaceChildren(h("div", { class: "panel", style: { marginTop: "14px" } },
    h("div", { class: "panel-h" }, h("h3", {}, b.filename), h("span", { class: "hint" }, `SHA-256 ${b.sha256.slice(0, 12)}… · ปี ${b.target_year + 543}`), h("span", { style: { flex: 1 } }),
      b.summary.previous_commit_same_file ? h("span", { class: "pill warn" }, "ไฟล์นี้เคยนำเข้าแล้ว") : null,
      editable ? (n => h("button", { class: "btn primary", onclick: commit, disabled: !n, title: n ? "" : "ไม่มีแถวที่จะเพิ่มหรืออัปเดต" }, icon("check"), n ? `ยืนยันนำเข้า ${n} รายการ` : "ไม่มีรายการใหม่"))(b.rows.filter(r => ["add", "update"].includes(r.action)).length) : h("span", { class: "pill ok" }, b.status)),
    h("div", { style: { padding: "14px 18px", display: "grid", gridTemplateColumns: "1fr 2fr", gap: "18px" } },
      h("div", {}, h("div", { class: "sec", style: { fontWeight: 600, fontSize: "12px", color: "var(--steel)", marginBottom: "6px" } }, "Sheet ที่พบ"),
        sheets.map(s => h("div", { style: { padding: "6px 0", borderBottom: "1px solid var(--line-soft)", fontSize: "13px" } },
          h("b", {}, s.sheet), " ", h("span", { class: `pill ${s.status === "parsed" ? "ok" : "idle"}` }, s.status === "parsed" ? `อ่านได้ ${s.days} วัน` : "ข้าม"),
          s.reason ? h("div", { class: "hint" }, s.reason) : null, (s.warnings || []).map(w => h("div", { class: "issue warn" }, icon("alert"), w))))),
      h("div", {}, h("div", { class: "kpis" }, kpi("all", "ทั้งหมด", b.rows.length), kpi("add", "จะเพิ่ม", counts.add), kpi("issues", "มีข้อสังเกต", b.rows.filter(r => r.issues.some(i => i.level !== "info")).length),
        kpi("reject", "ปฏิเสธ", counts.reject), kpi("skip_duplicate", "ซ้ำ", counts.skip_duplicate), kpi("update_candidate", "มีของเดิม", counts.update_candidate), kpi("conflict", "ถูกแก้มือ", counts.conflict)),
        h("p", { class: "hint", style: { marginTop: "10px" } }, "ระบบไม่เดาเวลา: รายการที่ไม่มีเวลาจะเข้า 'ยังไม่กำหนดเวลา' · การนำเข้าไม่ทำให้งานใดเป็น 'เสร็จ'")))),
    h("div", { style: { maxHeight: "60vh", overflow: "auto", borderTop: "1px solid var(--line-soft)" } }, tbl));
  async function commit() {
    try { const r = await api(`/imports/${b.id}/commit`, { method: "POST" }); toast(`นำเข้าแล้ว: เพิ่ม ${r.added} อัปเดต ${r.updated} — อยู่ในฉบับร่าง รอ Publish`); IMP.batch = null; importPage(); }
    catch (e) { err(e); }
  }
}
function importRow(r, editable) {
  const tr = h("tr", { class: r.action === "reject" ? "reject" : "" });
  const actSel = editable && !["conflict"].includes(r.action) ? h("select", { class: "input", style: { height: "34px" } },
    (r.action === "update_candidate" || r.action === "update" ? ["update", "skip"] : r.action === "reject" ? ["skip"] : ["add", "skip"])
      .concat(r.action === "reject" || r.action === "skip_duplicate" ? [r.action] : []).filter((v, i, a) => a.indexOf(v) === i)
      .map(a => h("option", { value: a, selected: a === r.action || (r.action === "update_candidate" && a === "skip") }, (ACT[a] || [a])[0]))) : null;
  if (actSel) actSel.onchange = async () => {
    if (["reject", "skip_duplicate"].includes(actSel.value)) return;
    try { Object.assign(r, await api(`/import-rows/${r.id}`, { method: "PATCH", body: { action: actSel.value } })); renderImport(); } catch (e) { err(e); }
  };
  let fix = null;
  if (editable && r.action === "reject") {
    const di = h("input", { class: "input", type: "date", style: { height: "34px" } });
    fix = h("div", { style: { display: "flex", gap: "6px", marginTop: "6px" } }, di, h("button", { class: "btn", onclick: async () => {
      if (!di.value) return toast("เลือกวันที่ที่ถูกต้องก่อน", "warn");
      try { Object.assign(r, await api(`/import-rows/${r.id}`, { method: "PATCH", body: { date: di.value } })); toast("แก้วันที่แล้ว — แถวนี้จะถูกเพิ่ม"); renderImport(); } catch (e) { err(e); } } }, "ใช้วันที่นี้"));
  }
  tr.append(
    h("td", { class: "ref" }, `${r.sheet}!${r.cell_ref}`, r.line_no > 1 ? `#${r.line_no}` : ""),
    h("td", {}, r.date ? `${pd(r.date).getDate()} ${TH_MONTH_S[pd(r.date).getMonth()]}` : "—"),
    h("td", { style: { whiteSpace: "nowrap" } }, r.start_at ? `${hhmm(r.start_at)}–${hhmm(r.end_at)}` : h("span", { class: "hint" }, { morning: "เช้า", afternoon: "บ่าย", other: "อื่นๆ" }[r.time_slot] || "—")),
    h("td", { style: { maxWidth: "420px" } }, r.title, h("div", { class: "hint" }, r.raw_text.length > r.title.length + 14 ? r.raw_text : "")),
    h("td", { style: { whiteSpace: "nowrap" } }, r.location, r.mbo_ref ? h("div", { class: "hint" }, `MBO ${r.mbo_ref}`) : null),
    h("td", {}, r.issues.filter(i => i.code !== "notes").map(i => h("div", { class: `issue ${i.level}` }, icon(i.level === "error" ? "alert" : "info"), i.msg)), fix),
    h("td", {}, actSel || h("span", { class: `pill ${(ACT[r.action] || ["", "idle"])[1]}` }, (ACT[r.action] || [r.action])[0])));
  return tr;
}

// ───────────────────────── HISTORY ─────────────────────────
async function historyPage() {
  let v; try { v = await api(`/plans/${S.ym.y}/${S.ym.m}`); } catch (e) { return err(e); }
  const items = v.versions;
  mainEl.replaceChildren(h("div", { class: "topbar" }, h("h1", { class: "page-h" }, bi("history")),
    h("span", { class: "hint" }, `${TH_MONTH[S.ym.m - 1]} ${S.ym.y + 543}`),
    h("button", { class: "btn icon", onclick: () => { shiftMonthH(-1); } }, icon("chevL")), h("button", { class: "btn icon", onclick: () => shiftMonthH(1) }, icon("chevR"))),
    h("div", { class: "page" }, items.length ? h("div", { class: "panel" }, items.map(x => h("div", { style: { display: "grid", gridTemplateColumns: "110px 1fr", gap: "18px", padding: "16px 18px", borderBottom: "1px solid var(--line-soft)" } },
      h("div", {}, h("div", { style: { fontSize: "var(--t-xl)", fontWeight: 600 } }, `REV.${String(x.revision).padStart(2, "0")}`), h("div", { class: "hint" }, x.published_at.replace("T", " ").slice(0, 16))),
      h("div", {}, h("div", { style: { display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" } }, h("span", { class: "pill ok" }, `เพิ่ม ${x.diff.added.length}`), h("span", { class: "pill info" }, `เปลี่ยน ${x.diff.changed.length}`),
        h("span", { class: "pill bad" }, `ลบ ${x.diff.removed.length}`), h("span", { class: "hint" }, `โดย ${x.published_by || "-"}`)),
        x.note ? h("p", { style: { margin: "8px 0 0" } }, x.note) : null,
        x.diff.changed.length ? h("ul", { class: "hint", style: { margin: "8px 0 0", paddingLeft: "18px" } }, x.diff.changed.slice(0, 12).map(c => h("li", {}, `${c.fields.join(", ")}: ${JSON.stringify(c.before)} → ${JSON.stringify(c.after)}`))) : null))))
      : h("div", { class: "empty" }, art("history", 76, "hero"), h("h3", {}, "ยังไม่มีการ Publish ในเดือนนี้"), h("p", {}, "เมื่อ Publish แผน ระบบจะเก็บแต่ละ REV และรายการที่เปลี่ยนไว้ที่นี่"))));
}
function shiftMonthH(d) { let { y, m } = S.ym; m += d; if (m < 1) { m = 12; y--; } if (m > 12) { m = 1; y++; } S.ym = { y, m }; location.hash = `#/history/${ymStr()}`; }

window.addEventListener("offline", () => document.body.append(h("div", { class: "offline-bar", id: "offbar" }, "ออฟไลน์ — การแก้ไขจะบันทึกไม่ได้จนกว่าจะเชื่อมต่อใหม่")));
window.addEventListener("online", () => document.getElementById("offbar")?.remove());
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
boot();
