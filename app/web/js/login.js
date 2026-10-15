import { h, icon, bi, api, toast } from "./ui.js";

// Rolling-mill illustration: a slab glows its way through four roll stands, once, on load.
export const millArt = () => {
  const NS = "http://www.w3.org/2000/svg";
  const s = document.createElementNS(NS, "svg");
  s.setAttribute("viewBox", "0 0 640 220"); s.setAttribute("class", "mill"); s.setAttribute("aria-hidden", "true");
  s.innerHTML = `
  <defs>
    <linearGradient id="slab" x1="0" x2="1"><stop offset="0" stop-color="#FFE39A"/><stop offset=".35" stop-color="#FF9A2E"/><stop offset=".8" stop-color="#FF6A13"/><stop offset="1" stop-color="#B5420A"/></linearGradient>
    <filter id="glow" x="-30%" y="-200%" width="160%" height="500%"><feGaussianBlur stdDeviation="9"/></filter>
    <linearGradient id="roll" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".95"/><stop offset="1" stop-color="#C9D4E6" stop-opacity=".9"/></linearGradient>
  </defs>
  <g opacity=".5" stroke="var(--line)" stroke-width="2">${Array.from({ length: 24 }, (_, i) => `<line x1="${i * 28}" y1="150" x2="${i * 28 + 14}" y2="150"/>`).join("")}</g>
  ${[150, 270, 390, 510].map(x => `
    <rect x="${x - 34}" y="40" width="68" height="132" rx="6" fill="var(--glass-card)" stroke="var(--line)" stroke-width="2"/>
    <circle cx="${x}" cy="104" r="24" fill="url(#roll)" stroke="var(--line)" stroke-width="2"/><circle cx="${x}" cy="104" r="5" fill="var(--fg-3)"/>
    <circle cx="${x}" cy="160" r="24" fill="url(#roll)" stroke="var(--line)" stroke-width="2"/><circle cx="${x}" cy="160" r="5" fill="var(--fg-3)"/>`).join("")}
  <g class="slab-move">
    <rect x="0" y="125" width="190" height="14" rx="3" fill="url(#slab)" filter="url(#glow)" opacity=".9"/>
    <rect x="0" y="128" width="190" height="8" rx="2" fill="url(#slab)"/>
  </g>`;
  const st = document.createElementNS(NS, "style");
  st.textContent = `.slab-move{animation:roll 3.4s cubic-bezier(.35,.1,.2,1) .3s both}@keyframes roll{from{transform:translateX(-220px)}to{transform:translateX(430px)}}
  @media (prefers-reduced-motion:reduce){.slab-move{animation:none;transform:translateX(430px)}}`;
  s.prepend(st);
  return s;
};

export const loginView = (onDone, { compact } = {}) => {
  const u = h("input", { class: "input", autocomplete: "username", id: "lg-u", autocapitalize: "none" });
  const p = h("input", { class: "input", type: "password", autocomplete: "current-password", id: "lg-p" });
  const msg = h("p", { class: "issue error", role: "alert", style: { minHeight: "20px" } });
  const btn = h("button", { class: "btn primary lg", style: { width: "100%", justifyContent: "center" }, type: "submit" }, bi("login"));
  const form = h("form", {}, h("h2", { style: { margin: "0 0 4px", fontSize: "var(--t-2xl)", fontWeight: 600 } }, "เข้าสู่ระบบ"),
    h("p", { class: "hint", style: { margin: "0 0 24px" } }, "ใช้บัญชีที่ผู้ดูแลระบบสร้างให้"),
    h("div", { class: "field" }, h("label", { for: "lg-u" }, "ชื่อผู้ใช้"), u),
    h("div", { class: "field" }, h("label", { for: "lg-p" }, "รหัสผ่าน"), p), msg, btn);
  form.onsubmit = async e => {
    e.preventDefault(); btn.disabled = true; msg.textContent = "";
    try { await api("/auth/login", { method: "POST", body: { username: u.value, password: p.value } }); await onDone(); }
    catch (x) { msg.replaceChildren(icon("alert"), x.message); btn.disabled = false; p.select(); }
  };
  setTimeout(() => u.focus(), 50);
  if (compact) return h("div", { class: "m-login" }, h("div", { class: "art glass" }, millArt(),
    h("div", { class: "m-brand" }, "HRM WorkSpace"), h("p", {}, "แผนงานรีดร้อน วันนี้และกะถัดไป")), h("div", { class: "form glass" }, form));
  return h("div", { class: "login" },
    h("div", { class: "art glass" }, millArt(),
      h("h1", {}, "HRM WorkSpace"),
      h("p", {}, "วางแผนงานบำรุงรักษาและงานประจำของรีดร้อน ครั้งเดียว แล้วให้ทีมเห็นบนมือถือทันทีหลัง Publish"),
      h("p", { lang: "ja", style: { fontFamily: "var(--f-jp)", fontSize: "14px", marginTop: "10px", color: "var(--fg-3)" } }, "熱間圧延 作業計画")),
    h("div", { class: "form glass" }, h("div", {}, form)));
};
