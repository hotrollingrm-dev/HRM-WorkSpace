// Hand-drawn sticker icons ("emoji") in the same pen-and-pastel language as the mill backdrop.
// Outline colour comes from CSS (--stk-line) so stickers sit right in light and dark mode.
// Semi-formal by design: equipment and objects only, no faces.

const O = 'class="o"';   // inked outline
const spark = (x, y, r, fill = "#FFE7A3") => {
  const k = r * .25;
  return `<path ${O} style="stroke-width:1.2" fill="${fill}" d="M${x},${y - r}Q${x + k},${y - k} ${x + r},${y}Q${x + k},${y + k} ${x},${y + r}Q${x - k},${y + k} ${x - r},${y}Q${x - k},${y - k} ${x},${y - r}Z"/>`;
};
const glint = d => `<path d="${d}" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" opacity=".9"/>`;

const S = {
  coil: `<path d="M15 36L33 12L37 15L19 39Z" fill="#B7C3CF"/><path ${O} d="M15 36L19 39M33 12L37 15" fill="none"/>
    <circle ${O} cx="28" cy="27" r="15" fill="#A7B4C1"/>
    <circle ${O} cx="24" cy="24" r="15" fill="#EAF0F5"/>
    <circle cx="24" cy="24" r="11.3" fill="none" stroke="#C6D0DA" stroke-width="1.3"/><circle cx="24" cy="24" r="8.3" fill="none" stroke="#C6D0DA" stroke-width="1.3"/>
    <circle ${O} cx="24" cy="24" r="5" fill="#7E8C9A"/>${glint("M13.5 19.5A11.5 11.5 0 0 1 19.5 12.8")}${spark(39.5, 8.5, 4.5)}`,
  sun: `<g ${O} style="stroke-width:5.4">${[0, 45, 90, 135, 180, 225, 270, 315].map(a => { const r = a * Math.PI / 180;
      return `<line x1="${(24 + 14 * Math.cos(r)).toFixed(1)}" y1="${(24 + 14 * Math.sin(r)).toFixed(1)}" x2="${(24 + 19 * Math.cos(r)).toFixed(1)}" y2="${(24 + 19 * Math.sin(r)).toFixed(1)}"/>`; }).join("")}</g>
    <g stroke="#F6B73C" stroke-width="3" stroke-linecap="round">${[0, 45, 90, 135, 180, 225, 270, 315].map(a => { const r = a * Math.PI / 180;
      return `<line x1="${(24 + 14 * Math.cos(r)).toFixed(1)}" y1="${(24 + 14 * Math.sin(r)).toFixed(1)}" x2="${(24 + 19 * Math.cos(r)).toFixed(1)}" y2="${(24 + 19 * Math.sin(r)).toFixed(1)}"/>`; }).join("")}</g>
    <circle ${O} cx="24" cy="24" r="10.5" fill="#FFD36E"/><path d="M31.4 17.4A10.5 10.5 0 0 1 17.4 31.4A12 12 0 0 0 31.4 17.4Z" fill="#F6B73C"/>${glint("M17.6 21A7 7 0 0 1 21 17.6")}`,
  moon: `<path ${O} fill="#FFE08A" d="M29 7.5A17 17 0 1 0 41 33A13 13 0 1 1 29 7.5Z"/><path d="M15 34A17 17 0 0 0 41 33A13.5 13.5 0 0 1 21 31Z" fill="#F5C95C" opacity=".8"/>
    <circle cx="17" cy="22" r="2.2" fill="#F2C35A"/><circle cx="22" cy="33" r="1.6" fill="#F2C35A"/>${glint("M13.5 18A13 13 0 0 1 19.5 11")}${spark(40, 11, 4.6, "#FFF4CC")}${spark(34, 4.8, 2.4, "#FFF4CC")}`,
  check: `<circle ${O} cx="24" cy="24" r="17" fill="#86D7A0"/><path d="M36 13A17 17 0 0 1 14 38A15 15 0 0 0 36 13Z" fill="#62C17F"/>
    <path d="M16 24.5L21.5 30L32.5 18" fill="none" stroke="var(--stk-line)" stroke-width="6.6" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M16 24.5L21.5 30L32.5 18" fill="none" stroke="#fff" stroke-width="3.8" stroke-linecap="round" stroke-linejoin="round"/>${glint("M12 19A12.5 12.5 0 0 1 18 11.5")}`,
  alert: `<path ${O} fill="#FFC774" d="M24 6.5C25.7 6.5 26.8 7.5 27.6 9L42 35C43.4 37.6 41.8 40.5 38.8 40.5H9.2C6.2 40.5 4.6 37.6 6 35L20.4 9C21.2 7.5 22.3 6.5 24 6.5Z"/>
    <path d="M41.4 33.8L42 35C43.4 37.6 41.8 40.5 38.8 40.5H12L36 30Z" fill="#F6AE4E"/>
    <path d="M24 16.5V27.5" stroke="#5E3F22" stroke-width="4.2" stroke-linecap="round"/><circle cx="24" cy="34" r="2.5" fill="#5E3F22"/>`,
  info: `<circle ${O} cx="24" cy="24" r="17" fill="#A7D0FF"/><path d="M36 13A17 17 0 0 1 14 38A15 15 0 0 0 36 13Z" fill="#86BBF5"/>
    <circle cx="24" cy="15.5" r="2.7" fill="#24476F"/><path d="M24 21.5V33" stroke="#24476F" stroke-width="4.4" stroke-linecap="round"/>${glint("M12 19A12.5 12.5 0 0 1 18 11.5")}`,
  calendar: `<rect ${O} x="7" y="10" width="34" height="31" rx="6" fill="#FFFDF8"/>
    <path ${O} fill="#F2958A" d="M7 16A6 6 0 0 1 13 10H35A6 6 0 0 1 41 16V20H7Z"/>
    <rect ${O} x="14" y="6" width="4.4" height="8.5" rx="2.2" fill="#93A1AE"/><rect ${O} x="29.6" y="6" width="4.4" height="8.5" rx="2.2" fill="#93A1AE"/>
    ${[13, 20, 27, 34].map(x => [25, 32].map(y => `<rect x="${x - 2}" y="${y - 2}" width="5" height="5" rx="1.6" fill="${x === 27 && y === 32 ? "#7FB2F0" : "#EADFCF"}"/>`).join("")).join("")}
    ${glint("M11 13.5A3.5 3.5 0 0 1 13.8 12.2")}`,
  clipboard: `<rect ${O} x="9" y="7.5" width="30" height="34.5" rx="5" fill="#DDB98E"/><rect ${O} x="13" y="12.5" width="22" height="25.5" rx="2.5" fill="#FFFDF8"/>
    <rect ${O} x="17" y="4.5" width="14" height="7" rx="3" fill="#A3B0BD"/>
    <path d="M17 20H31M17 25.5H31M17 31H24" stroke="#CDBEA8" stroke-width="2.2" stroke-linecap="round"/>
    <path d="M27 31.2L29.6 33.8L34.6 27.6" fill="none" stroke="#4FB872" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>`,
  upload: `<rect ${O} x="7.5" y="27" width="33" height="14" rx="4.5" fill="#EBD4B0"/><path d="M7.5 33H40.5" stroke="var(--stk-line)" stroke-width="1.6" opacity=".45"/>
    <path ${O} fill="#86B9F4" d="M24 5.5L35.5 18H29V30H19V18H12.5Z"/>${glint("M19.5 9.5L22.5 6.5")}`,
  history: `<circle ${O} cx="24" cy="24.5" r="17" fill="#FFFDF8"/><circle cx="24" cy="24.5" r="13.2" fill="none" stroke="#B5D2EE" stroke-width="2.4"/>
    <path d="M24 15V24.5L30.5 28.5" fill="none" stroke="#475A70" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="24" cy="24.5" r="2.3" fill="#F2958A"/>${spark(39, 9, 4)}`,
  settings: `<path ${O} fill="#CAD5DF" d="M40.0,20.1 L43.3,21.5 L43.3,26.5 L40.0,27.9 L38.1,32.6 L39.5,35.9 L35.9,39.5 L32.6,38.1 L27.9,40.0 L26.5,43.3 L21.5,43.3 L20.1,40.0 L15.4,38.1 L12.1,39.5 L8.5,35.9 L9.9,32.6 L8.0,27.9 L4.7,26.5 L4.7,21.5 L8.0,20.1 L9.9,15.4 L8.5,12.1 L12.1,8.5 L15.4,9.9 L20.1,8.0 L21.5,4.7 L26.5,4.7 L27.9,8.0 L32.6,9.9 L35.9,8.5 L39.5,12.1 L38.1,15.4Z"/>
    <path d="M37 30A15 15 0 0 1 18 38.5A13 13 0 0 0 37 30Z" fill="#AEBCC9"/><circle ${O} cx="24" cy="24" r="6.2" fill="#FFFDF8"/>${glint("M13.5 19A11 11 0 0 1 18.5 13.5")}`,
  users: `<path ${O} fill="#FFD36E" d="M9 30C9 19.5 15.5 12 24 12C32.5 12 39 19.5 39 30Z"/><path d="M33 16.5C36.8 20 39 24.6 39 30H31C31 24.8 32 20 33 16.5Z" fill="#F6B73C"/>
    <path d="M24 12V29" stroke="var(--stk-line)" stroke-width="2" opacity=".55"/><rect ${O} x="5" y="29" width="38" height="6.5" rx="3.2" fill="#F2A93B"/>
    ${glint("M14 22A11 11 0 0 1 19 15.5")}`,
  user: `<path ${O} fill="#A7D0FF" d="M9 41C9 31.5 15.5 27 24 27C32.5 27 39 31.5 39 41Z"/><circle ${O} cx="24" cy="17" r="8.2" fill="#FFE2C6"/>
    <path ${O} fill="#FFD36E" d="M15.4 15.5C15.4 10.5 19.2 7.6 24 7.6C28.8 7.6 32.6 10.5 32.6 15.5Z"/><rect ${O} x="13" y="14.6" width="22" height="3.2" rx="1.6" fill="#F2A93B"/>`,
  edit: `<path ${O} fill="#FFD36E" d="M11 37L13 29L31 11L37 17L19 35Z"/><path ${O} fill="#F3DDBF" d="M11 37L13 29L19 35Z"/><path d="M11 37L12 33L15 36Z" fill="var(--stk-line)"/>
    <path ${O} fill="#F4A6A6" d="M28 14L31 11L37 17L34 20Z"/>${glint("M16 29L28 17")}`,
  wifiOff: `<path ${O} fill="#E3EBF3" d="M14 36H35A8 8 0 0 0 36 20A11 11 0 0 0 15 18A9 9 0 0 0 14 36Z"/>
    <path d="M10 10L38 38" stroke="var(--stk-line)" stroke-width="6.4" stroke-linecap="round"/><path d="M10 10L38 38" stroke="#EE7B7B" stroke-width="3.6" stroke-linecap="round"/>`,
  sparkle: `${spark(22, 24, 15)}${spark(38, 11, 5.5)}${spark(38, 36, 4)}`,
};
// aliases used around the app
Object.assign(S, { gear: S.settings, slab: S.coil, grid: S.clipboard, plan: S.calendar, import: S.upload, ok: S.check, bad: S.alert, warn: S.alert });

export const hasSticker = name => name in S;
export const sticker = (name, size = 32, cls = "") => {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 48 48"); s.setAttribute("width", size); s.setAttribute("height", size);
  s.setAttribute("class", `stk ${cls}`.trim()); s.setAttribute("aria-hidden", "true");
  s.innerHTML = S[name] || S.info;
  return s;
};
