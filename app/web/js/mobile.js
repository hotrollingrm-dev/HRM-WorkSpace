import { h, icon, bi, T, toast, tile3d, TILE, api, ApiError, TH_MONTH_S, TH_WD_L, JP_WD, pd, iso, hhmm, todayIso, statusPill, heatStrip } from "./ui.js";
import { loginView } from "./login.js";

const RANK = { viewer: 0, leader: 1, foreman: 2, admin: 3 };
const app = document.getElementById("app");
const S = { me: null, day: null, data: null, tab: "today" };
const can = r => S.me && RANK[S.me.role] >= RANK[r];
const err = e => toast(e instanceof ApiError ? e.message : String(e), "bad", 5000);

async function boot() {
  try { S.me = await api("/me"); }
  catch (e) {
    if (e.status === 401) return app.replaceChildren(loginView(boot, { compact: true }));
    return app.replaceChildren(h("div", { class: "empty", style: { minHeight: "80vh" } }, icon("wifiOff"), h("h3", {}, "เชื่อมต่อไม่ได้"),
      h("p", {}, e.message), h("button", { class: "btn lg", onclick: boot }, "ลองใหม่")));
  }
  const tab = location.hash.slice(2);
  if (["today", "next", "shift", "me"].includes(tab)) S.tab = tab;
  await load();
}
async function load() {
  try { S.data = await api(`/today${S.day ? `?d=${S.day}` : ""}`); S.day = S.data.op_day; render(); }
  catch (e) { if (e.status === 401) return boot(); err(e); render(); }
}
const bandOf = e => { if (!e.start_at) return "un"; const hr = +e.start_at.slice(11, 13); return hr >= 8 && hr < 20 ? "day" : "night"; };
const nowBand = nowIso => { const hr = +nowIso.slice(11, 13); return hr >= 8 && hr < 20 ? ["กะกลางวัน", "sun"] : ["กะกลางคืน", "moon"]; };

function render() {
  const d = S.data;
  const tabbar = h("nav", { class: "tabbar", "aria-label": "เมนู" },
    [["today", "sun", "today"], ["next", "calendar", "upcoming"], ["shift", "users", "shift"], ["me", "user", "account"]].map(([k, ic, t]) =>
      h("a", { href: `#/${k}`, "aria-current": S.tab === k ? "page" : null, onclick: e => { e.preventDefault(); S.tab = k; history.replaceState(null, "", `#/${k}`); render(); } },
        icon(ic), T[t][0])));
  if (!d) return app.replaceChildren(h("div", { class: "m-body" }, h("div", { class: "skeleton", style: { height: "220px", borderRadius: "22px" } })), tabbar);
  const view = { today: todayView, next: nextView, shift: shiftView, me: meView }[S.tab]();
  app.replaceChildren(...view, tabbar);
}

function hero() {
  const d = S.data, dt = pd(d.op_day), isToday = d.op_day === S.data.now.slice(0, 10) || (todayIso() === d.op_day);
  let [bandName] = nowBand(d.now);
  const ph = d.shift?.now_phase, team = c => d.shift?.shifts?.find(x => x.code === c)?.team;
  if (ph === "handover") bandName = "ช่วงส่งมอบกะ";
  else if (ph) bandName = `${ph === "D" ? "กะกลางวัน" : "กะกลางคืน"}${team(ph) ? ` · ทีม ${team(ph)}` : ""}`;
  const done = d.entries.filter(e => e.progress.status === "completed").length;
  const review = d.entries.filter(e => e.progress.status === "pending_review").length;
  const step = n => { const x = pd(S.day); x.setDate(x.getDate() + n); S.day = iso(x); load(); };
  return h("header", { class: "m-hero glass" }, h("div", {},
    h("div", { class: "m-top" },
      h("div", { class: "m-brand" }, tile3d("slab", TILE.brand, 36), "HRM WorkSpace"),
      h("div", { class: "m-daynav" },
        h("button", { "aria-label": "วันก่อน", onclick: () => step(-1) }, icon("chevL")),
        !isToday ? h("button", { "aria-label": "กลับวันนี้", onclick: () => { S.day = null; load(); }, style: { width: "auto", padding: "0 12px", fontSize: "13px" } }, "วันนี้") : null,
        h("button", { "aria-label": "วันถัดไป", onclick: () => step(1) }, icon("chevR")))),
    h("div", { class: "m-date" }, `${TH_WD_L[dt.getDay()]} ${dt.getDate()} ${TH_MONTH_S[dt.getMonth()]}`,
      h("small", {}, `08:00 วันนี้ ถึง 08:00 วันถัดไป${d.holiday ? ` · ${d.holiday}` : ""}`),
      h("span", { class: "jp", lang: "ja" }, `${dt.getMonth() + 1}月${dt.getDate()}日（${JP_WD[dt.getDay()]}）`)),
    h("div", { class: "m-now" }, isToday ? h("span", {}, "ตอนนี้ ", h("b", {}, bandName), `  ${d.now.slice(11, 16)}`) : h("span", {}, "ดูแผนล่วงหน้า / ย้อนหลัง"),
      d.entries[0]?.revision ? h("span", {}, `REV.${String(d.entries[0].revision).padStart(2, "0")}`) : null),
    heatStrip(d.bands, { nowIso: isToday ? d.now : null, opDay: d.op_day, big: true }),
    h("div", { class: "m-stats" },
      h("div", {}, h("b", {}, d.entries.length), h("span", {}, "งานทั้งหมด")),
      h("div", {}, h("b", {}, done), h("span", {}, "เสร็จแล้ว")),
      h("div", {}, h("b", {}, review), h("span", {}, "รอตรวจ")))));
}

function todayView() {
  const d = S.data;
  const body = h("main", { class: "m-body" });
  body.append(shiftCard(d.shift));
  if (!d.entries.length) {
    body.append(h("div", { class: "empty" }, icon("calendar"), h("h3", {}, "ไม่มีงานที่ Publish สำหรับวันนี้"),
      h("p", {}, "ถ้าคาดว่าควรมีงาน ให้ Foreman ตรวจว่าแผนเดือนนี้ Publish แล้ว"),
      h("button", { class: "btn lg", onclick: () => { S.tab = "next"; render(); } }, "ดูงาน 7 วันถัดไป")));
    return [hero(), body];
  }
  const groups = [["day", "ช่วงกลางวัน 08:00–20:00", "var(--day)"], ["night", "ช่วงกลางคืน 20:00–08:00", "var(--night)"],
    ["un", T.unscheduled[0], "repeating-linear-gradient(90deg,var(--fg-3) 0 4px,transparent 4px 7px)"]];
  for (const [k, label, bg] of groups) {
    const es = d.entries.filter(e => bandOf(e) === k);
    if (!es.length) continue;
    body.append(h("div", { class: "m-sec" }, h("span", { class: "band", style: { background: bg } }), label, h("span", { class: "n" }, `${es.length} งาน`)));
    es.forEach(e => body.append(taskCard(e)));
  }
  return [hero(), body];
}

function nextAction(e) {
  const st = e.progress.status;
  if (st === "planned" || st === "on_hold") return [["in_progress", "เริ่มงาน", "play", "ink"]];
  if (st === "in_progress") return can("leader") ? [["completed", "เสร็จแล้ว", "check", "primary"]] : [["pending_review", "ส่งตรวจ", "check", "primary"]];
  if (st === "pending_review" && can("leader")) return [["completed", "ยืนยันเสร็จ", "check", "primary"]];
  return [];
}
function taskCard(e) {
  const st = e.progress.status;
  const nextDay = e.end_at && e.start_at && e.end_at.slice(0, 10) !== e.start_at.slice(0, 10);
  const card = h("article", { class: `task ${st === "completed" || st === "cancelled" ? "done" : ""}`, style: { "--cc": e.category?.color } },
    h("div", { class: "cb" }),
    h("div", { class: "in" },
      h("div", { class: "row", onclick: () => sheet(e), style: { cursor: "pointer" } },
        h("div", { class: "tm" }, e.start_at ? [hhmm(e.start_at), h("small", {}, `ถึง ${hhmm(e.end_at)}${nextDay ? " +1" : ""}`)]
          : h("small", { style: { marginTop: 0 } }, e.shift ? `กะ ${e.shift}` : e.time_slot === "morning" ? "ช่วงเช้า" : e.time_slot === "afternoon" ? "ช่วงบ่าย" : "ทั้งวัน")),
        h("div", { class: "tt" }, e.title_th,
          h("div", { class: "m" }, [e.category?.name_th, e.location].filter(Boolean).join(" · ")),
          h("div", { style: { marginTop: "6px" } }, statusPill(st)))),
      nextAction(e).length ? h("div", { class: "acts" }, nextAction(e).map(([s, l, ic, k]) => h("button", { class: `btn ${k}`, onclick: () => setStatus(e, s) }, icon(ic), l))) : null));
  return card;
}
async function setStatus(e, status, note = "") {
  try {
    await api(`/progress/${e.uid}`, { method: "POST", body: { status, note } });
    toast({ in_progress: "เริ่มงานแล้ว", completed: "บันทึกว่าเสร็จแล้ว", pending_review: "ส่งให้ Leader ตรวจแล้ว", on_hold: "พักงานไว้", cancelled: "ยกเลิกงานแล้ว", planned: "คืนเป็นแผน" }[status] || "บันทึกแล้ว");
    navigator.vibrate?.(12);
    await load();
  } catch (x) { err(x); }
}
function sheet(e) {
  const scrim = h("div", { class: "scrim" });
  const close = () => { scrim.remove(); sh.remove(); };
  scrim.onclick = close;
  const st = e.progress.status;
  const opts = [];
  for (const a of nextAction(e)) opts.push(h("button", { class: `btn ${a[3]}`, onclick: () => { close(); setStatus(e, a[0]); } }, icon(a[2]), a[1]));
  if (st === "in_progress") opts.push(h("button", { class: "btn", onclick: () => { close(); setStatus(e, "on_hold"); } }, icon("pause"), "พักงาน"));
  if (can("leader") && st !== "cancelled" && st !== "completed") opts.push(h("button", { class: "btn danger", onclick: () => { close(); setStatus(e, "cancelled"); } }, icon("x"), "ยกเลิกงานนี้"));
  if (can("leader") && (st === "completed" || st === "cancelled")) opts.push(h("button", { class: "btn", onclick: () => { close(); setStatus(e, "planned"); } }, icon("history"), "คืนสถานะเป็นแผน"));
  const sh = h("section", { class: "sheet", role: "dialog", "aria-label": e.title_th },
    h("div", { class: "grab" }), h("h2", {}, e.title_th), statusPill(st),
    h("dl", { class: "kv" },
      h("dt", {}, "เวลา"), h("dd", {}, e.start_at ? `${hhmm(e.start_at)} – ${hhmm(e.end_at)}` : T.unscheduled[0]),
      h("dt", {}, "หมวด"), h("dd", {}, e.category?.name_th || "—", e.subcategory ? ` / ${e.subcategory}` : ""),
      e.location ? [h("dt", {}, "สถานที่"), h("dd", {}, e.location)] : null,
      e.shift ? [h("dt", {}, "กะ"), h("dd", {}, e.shift === "D" ? "กลางวัน (D)" : "กลางคืน (N)")] : null,
      e.mbo_ref ? [h("dt", {}, "MBO"), h("dd", {}, e.mbo_ref)] : null,
      e.notes ? [h("dt", {}, "หมายเหตุ"), h("dd", {}, e.notes)] : null,
      e.source_type === "import" ? [h("dt", {}, "ที่มา"), h("dd", {}, `นำเข้าจาก ${e.source_ref}`)] : null,
      h("dt", {}, "แผน"), h("dd", {}, `REV.${String(e.revision).padStart(2, "0")}`)),
    opts, h("button", { class: "btn ghost", onclick: close }, "ปิด"));
  document.body.append(scrim, sh);
}

function nextView() {
  const d = S.data, body = h("main", { class: "m-body" });
  body.append(h("h1", { style: { fontSize: "28px", margin: "8px 4px 2px", fontWeight: 600 } }, bi("upcoming")));
  if (!d.upcoming.length) { body.append(h("div", { class: "empty" }, icon("calendar"), h("h3", {}, "ยังไม่มีงานที่ Publish ใน 7 วันถัดไป"))); return [body]; }
  const byDay = {};
  d.upcoming.forEach(e => (byDay[e.op_day] ||= []).push(e));
  for (const [day, es] of Object.entries(byDay).sort()) {
    const dt = pd(day);
    body.append(h("div", { class: "m-day" }, `${TH_WD_L[dt.getDay()]} ${dt.getDate()} ${TH_MONTH_S[dt.getMonth()]}`, h("small", {}, `${es.length} งาน`)));
    es.forEach(e => body.append(h("button", { class: "mini", style: { width: "100%", textAlign: "left" }, onclick: () => sheet(e) },
      h("span", { class: "b", style: { background: e.category?.color || "var(--stop)" } }),
      h("span", { class: "tm" }, e.start_at ? hhmm(e.start_at) : "—"), h("span", { class: "tt" }, e.title_th), statusPill(e.progress.status))));
  }
  return [body];
}
const tm = iso => iso ? iso.slice(11, 16) : "";
function shiftCard(sh) {
  const go = () => { S.tab = "shift"; render(); };
  if (sh.status !== "scheduled") return h("button", { class: "m-shift", onclick: go },
    h("span", { class: "ic2" }, icon("users")),
    h("span", {}, h("div", { class: "t" }, "กะวันนี้"), h("div", { class: "s" }, sh.message)), icon("chevR"));
  return h("button", { class: "m-shift2", onclick: go, "aria-label": "ดูรายชื่อกะวันนี้" },
    sh.shifts.map(x => h("span", { class: `sh ${x.code} ${sh.now_phase === x.code ? "now" : ""}` },
      h("i", {}, tile3d(x.code === "D" ? "sun" : "moon", x.code === "D" ? TILE.day : TILE.night, 46)),
      h("span", { class: "who" }, h("b", {}, x.team ? `ทีม ${x.team}` : "—", x.also.length ? ` + ${x.also.join(", ")}` : ""),
        h("small", {}, h("span", {}, x.code === "D" ? "กะกลางวัน" : "กะกลางคืน"), h("span", {}, `${tm(x.start)}–${tm(x.end)}`))),
      sh.now_phase === x.code ? h("em", {}, "ตอนนี้") : null)),
    sh.now_phase === "handover" ? h("span", { class: "handover" }, "ช่วงส่งมอบกะ") : null,
    sh.provisional ? h("span", { class: "prov" }, "ปฏิทินปี 2027 อาจเปลี่ยน") : null);
}
function shiftView() {
  const sh = S.data.shift;
  const body = h("main", { class: "m-body" }, h("h1", { style: { fontSize: "28px", margin: "8px 4px 14px", fontWeight: 600 } }, bi("shift")));
  const member = m => h("li", {}, h("span", {}, m.nickname ? h("b", {}, m.nickname, "  ") : "", h("small", {}, m.name)), h("small", {}, m.position));
  if (sh.status !== "scheduled") {
    body.append(h("div", { class: "issue warn", style: { margin: "0 4px 14px" } }, icon("alert"), sh.message));
    for (const t of ["A", "B", "C"]) body.append(h("section", { class: "team-card" }, h("h3", {}, `ทีม ${t}`), h("ul", {}, (sh.teams[t] || []).map(member))));
    return [body];
  }
  body.append(shiftCard(sh));
  for (const x of sh.shifts) {
    body.append(h("section", { class: `team-card ${x.code}` },
      h("h3", {}, `${x.code === "D" ? "กะกลางวัน" : "กะกลางคืน"} · ทีม ${x.team || "—"}`, h("span", {}, `${tm(x.start)}–${tm(x.end)}${x.code === "N" ? " (+1)" : ""}`)),
      x.fill ? h("p", { class: "hint", style: { margin: "0 0 6px" } }, x.fill === "special" ? "วันนี้ทำงานวันหยุดนักขัตฤกษ์" : "วันสลับวันทำงาน (Substitution)") : null,
      h("ul", {}, x.members.map(member)),
      x.also.length ? h("p", { class: "hint" }, `ทีม ${x.also.join(", ")} เข้ากะเดียวกันวันนี้ (วันสลับวันทำงาน)`) : null));
  }
  if (sh.off.length) body.append(h("p", { class: "hint", style: { margin: "4px" } },
    "หยุด: ", sh.off.map(o => `ทีม ${o.team} (${o.code === "S" ? "Factory shutdown" : "หยุด"})`).join(" · ")));
  body.append(h("p", { class: "hint", style: { margin: "10px 4px" } }, sh.note));
  return [body];
}
function meView() {
  return [h("main", { class: "m-body" }, h("h1", { style: { fontSize: "28px", margin: "8px 4px 14px", fontWeight: 600 } }, bi("account")),
    h("div", { class: "mini" }, icon("user"), h("span", { class: "tt" }, S.me.display_name, h("div", { class: "hint" }, `${S.me.username} · ${S.me.role}`))),
    h("p", { class: "hint", style: { margin: "14px 4px" } }, "การแจ้งเตือนบนมือถือจะเปิดใน Milestone 5 หลังได้รับอนุมัติจาก IT — ตอนนี้ให้เปิดแอปเพื่อดูแผนล่าสุด"),
    h("button", { class: "btn lg", style: { width: "100%", justifyContent: "center" }, onclick: async () => { await api("/auth/logout", { method: "POST" }).catch(() => {}); S.me = null; boot(); } }, icon("logout"), bi("logout")))];
}

window.addEventListener("online", () => load());
document.addEventListener("visibilitychange", () => { if (!document.hidden && S.me) load(); });
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
boot();
