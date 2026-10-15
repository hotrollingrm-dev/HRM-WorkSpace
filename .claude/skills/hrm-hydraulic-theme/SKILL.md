---
name: "hrm-hydraulic-theme"
description: "Apply the HRM Hydraulic Management visual theme (soft liquid-glass, Thai+EN bilingual, industrial status colors) to any factory/production app, dashboard or check sheet."
---

# HRM Hydraulic Theme

The house style of the HRM Hydraulic Management app (UACJ Thailand, Hot Rolling Mill). Use it for every new production-floor tool so all apps look like one product family: oil/level monitors, check sheets, trouble reports, OT/duty tools, dashboards.

Character: calm, premium, Apple-like clarity over a soft ambient background. Frosted-glass panels for chrome, solid readable content, big tabular numbers, consistent semantic status colors, custom 3D icon tiles, Thai first with a smaller secondary language underneath.

## 1. Principles

1. Thai is primary, a second language (EN default, JA optional) sits under it, smaller and grey. Never the other way round.
2. Glass is for chrome (sidebar, header, cards, modals, tooltips, toasts). Data inside stays high-contrast and solid.
3. Color always means something. Status colors are fixed across every screen and every app (table in §3).
4. Numbers are the hero: large, bold, `font-variant-numeric: tabular-nums`, unit smaller and grey next to it.
5. Big targets for the shop floor: buttons ≥ 60px (header 48px), inputs 54–58px, icon buttons 44–54px, segmented buttons ≥ 42px.
6. One screen at 1920×1080 with no window scroll: panes scroll inside themselves. Narrower windows reflow, never scroll sideways.
7. Every empty, missing, error and loading state is designed (hatched "no record", dashed missing card, toast errors).
8. Avoid: neon/cyberpunk, purple-blue hero gradients, gradient text, emoji, mixed icon families, heavy shadows, everything-is-a-card dashboards.

## 2. Design tokens (copy verbatim)

```css
:root{
  --bg:#E9EDF4;
  --amb1:rgba(88,140,255,.30); --amb2:rgba(40,190,170,.20); --amb3:rgba(255,184,76,.22); --amb4:rgba(150,120,255,.14);
  --glass:rgba(255,255,255,.55); --glass-strong:rgba(255,255,255,.74); --glass-card:rgba(255,255,255,.65);
  --glass-border:rgba(255,255,255,.78); --glass-line:rgba(255,255,255,.62); --glass-hi:rgba(255,255,255,.9); --glass-edge:rgba(30,50,90,.08);
  --card:rgba(255,255,255,.80); --surface:#FFFFFF; --surface-2:rgba(236,240,247,.85); --line:#DCE2EB; --grid:#E1E6EE;
  --fg:#111722; --fg-2:#535D6D; --fg-3:#828B9A;
  --primary:#2862E6; --primary-soft:rgba(40,98,230,.12); --on-primary:#FFFFFF;
  --run:#138D4C; --run-soft:rgba(19,141,76,.12);
  --stop:#657083; --stop-soft:rgba(101,112,131,.13);
  --leak:#D0353C; --leak-soft:rgba(208,53,60,.11);      /* critical / alarm / destructive */
  --abn:#D5600C;  --abn-soft:rgba(213,96,12,.12);       /* warning / attention / editing */
  --refill:#0B8B70; --drain:#2F74E8; --low:#B07800; --maint:#6F4FE0; --adj:#4A6488;
  --s-1:#4F7FEA; --s-2:#1E9E91; --s-3:#D69330;          /* per-system/line identity colors */
  --toast-bg:rgba(24,30,42,.9); --toast-fg:#FFFFFF; --toast-en:#B3BCCB;
  --shadow:0 1px 1px rgba(18,28,48,.04),0 12px 32px rgba(18,28,48,.07);
  --shadow-up:0 24px 60px rgba(18,28,48,.22); --scrim:rgba(18,26,42,.28);
  --font:"Thonburi","Noto Sans Thai","Leelawadee UI","Sukhumvit Set",system-ui,sans-serif;
  --r-xl:28px; --r-l:24px; --r-m:20px; --r-s:16px;
  --ease:cubic-bezier(.22,.9,.24,1); --gap:12px;
}
/* dark: apply under @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){…}} AND :root[data-theme="dark"]{…} */
--bg:#0B0F16; --amb1:rgba(70,110,255,.22); --amb2:rgba(30,170,150,.13); --amb3:rgba(255,160,60,.10); --amb4:rgba(140,100,255,.12);
--glass:rgba(28,34,46,.52); --glass-strong:rgba(26,32,44,.76); --glass-card:rgba(24,30,40,.62); --glass-border:rgba(255,255,255,.09); --glass-line:rgba(255,255,255,.08); --glass-hi:rgba(255,255,255,.14);
--card:rgba(24,29,39,.78); --surface:#171C25; --surface-2:rgba(40,47,60,.7); --line:#2C3441; --grid:#262E3A;
--fg:#EEF1F6; --fg-2:#A9B2C0; --fg-3:#7F8898; --primary:#7EA5FF; --primary-soft:rgba(126,165,255,.16); --on-primary:#0B0F16;
--run:#4CCB86; --stop:#9EA7B5; --leak:#FF7478; --abn:#FF9E55; --refill:#3FCCA8; --drain:#7EA9FF; --low:#EDB93A; --maint:#A98FFF;
--s-1:#86A9FF; --s-2:#4FCDBF; --s-3:#F0B861;
--toast-bg:rgba(236,240,246,.92); --toast-fg:#111722; --toast-en:#535D6D;
```

Print/PDF paper always uses the fixed light palette (white page, `#121821` text, 2px dark rule under the header).

## 3. Semantic status (never change between apps)

| Meaning | Token | Usage |
|---|---|---|
| Running / Normal / Success | `--run` | status dot, running pill, confirmed |
| Stopped / Offline / Neutral | `--stop` | stopped pill, idle |
| Warning / Near-limit / Editing | `--abn` | warning zone, pending review, edit mode ring |
| Critical / Alarm / Leak / Delete | `--leak` | below threshold, missing-data alert, destructive buttons |
| Information / Primary action | `--primary` | selection, focus, links, totals in money |
| Added / Refill (positive amount) | `--refill` | `+200 L` |
| Maintenance | `--maint` | | 
| Adjustment / calibration | `--adj` | |

Status dot: 11px circle + halo `box-shadow:0 0 0 4px color-mix(in srgb,var(--c) 18%,transparent)` + bold colored Thai label + small EN label. Soft backgrounds use the `-soft` variants; warning/critical cards add an inset 2px ring at 40–45% mix.

## 4. Ground, glass and surfaces

- `body`: `--bg` plus a fixed `::before` layer of 4 large soft radial gradients (`--amb1` top-left, `--amb2` top-right, `--amb3` bottom-right, `--amb4` bottom-left, each fading to transparent ~70%) over a subtle linear lift. This is the only "color wash"; it stays behind glass.
- `.glass` / `.card`: `background:var(--glass-card); backdrop-filter:blur(20px) saturate(140%); border:1px solid var(--glass-line); box-shadow:inset 0 1px 0 var(--glass-hi), inset 0 0 0 1px rgba(255,255,255,.06), 0 12px 40px rgba(20,30,60,.07)`; a `::before` top highlight `linear-gradient(180deg,rgba(255,255,255,.28),transparent 45%)`; card radius `--r-xl` (26–28px), padding 20–24px.
- Inner tiles (KPI cells, form rows, list rows): `--surface-2`, radius `--r-m`, no shadow. Hover: `--glass-strong`.
- Inputs: `--surface`, 2px `--line` border, radius 16, focus border `--primary` + no outline glow except `:focus-visible` 3px primary outline.

## 5. Typography

- Font stack `--font` (Thonburi first). Body 18px / 1.5. Bold 700 for headings and numbers, 600 for labels, never bold everything.
- Scale: hero number clamp(76–112px) · large value 40–56px · card value 24–34px · page title 25px · card title 21px · body 18px · label 15–17px · secondary/EN 12–14px.
- Bilingual label component:
```html
<span class="bi"><span class="th">ระดับน้ำมัน</span><span class="en">Oil Level</span></span>
```
`.bi{display:inline-flex;flex-direction:column;line-height:1.25}` `.bi .en{font-size:max(14px,.78em);color:var(--fg-2);font-weight:400}`. In tight horizontal places use `flex-direction:row;gap:6px;align-items:baseline`.
- Keep all strings in one dictionary `{key:[th,en,ja]}` and render via `L(key)`; hide `.en` when identical to Thai.
- Dates: Thai Buddhist year (`1 ต.ค. 2569`) with Gregorian secondary; time always 24h `HH:MM`, numeric input auto-formats `0830 → 08:30`.
- Money `฿3,000`, liters `5,620 L`, temperature `46.2 °C`; unit at ~0.4–0.6em, `--fg-2`.

## 6. Layout shell

```
.app  grid: [sidebar auto][main 1fr], gap 12, padding 12, height 100vh, overflow hidden
.sidebar  floating glass, radius 24, width 200 (collapsed 68), nav items 50px, radius 16
.main  grid rows: [header auto][content 1fr]
.header  glass, radius 22, min-height 62: title · context button (e.g. month) · status pills · clock · icon buttons · secondary + primary action
.content  scrolls internally (scrollbar-gutter:stable), pages animate in
```
- Active nav item: `--glass-card` background, primary icon/text, 4px primary bar on the left. Collapsed sidebar shows a dark glass tooltip (TH + EN) on hover.
- Dashboard = workflow, not KPI soup: thin top strip (alerts chip + compact money/volume KPIs) → main graph card (≈ 80%) → narrow timeline rail of latest events. Warnings surface as a pulsing red chip with a direct action ("ลงข้อมูลย้อนหลัง →").
- Split views: filter pane 320–360px | list | detail pane ~30%.
- Breakpoints: 1680 / 1440 / 1280 (stack to one column, page scrolls) / 1024 (tablet: icon-only sidebar, 1-col forms) / 640 (phone: 60px rail, 2-col header buttons).

## 7. Components

**Buttons** (pill, radius 999, gap 12, font 19/600, `:active{transform:scale(.97)}`, ripple on press):
- `.btn-primary` gradient `linear-gradient(180deg,color-mix(in srgb,var(--primary) 88%,#fff),var(--primary))`, white text, inset top highlight, glow `0 8px 20px color-mix(primary 32%)`. One per area.
- `.btn-tonal` primary-soft bg + primary text · `.btn-plain` surface-2 · `.btn-glass` glass-strong · `.btn-danger` leak-soft + leak text.
- Buttons may carry a two-line bilingual label.
- `.icon-btn` 54px circle, surface-2, hover glass-strong, `.danger` = leak color.

**Pills / badges**: `.pill` icon-tile + bilingual label on tinted soft bg (running = run-soft). `.badge` 15px/600, radius 999, variants ok / abn / blue.

**Segmented control**: track `--glass-card` or surface-2 with 4–5px padding, radius 999; buttons 42–52px; active = `--surface` or `--glass-strong` + `0 2px 10px rgba(20,40,90,.12)` + primary text. Small label at the start (`แสดงข้อมูล / Display`). Under 1024px swap to a `<select>`.

**Choice cards** (`.opt-card`, aria-pressed): 78px min, 2px line border, radius 20, icon tile + bilingual label + 26px check circle at right; pressed = primary border + primary-soft bg + filled check. Use for machine status, oil type, findings, language.

**Toggle switch**: 60×36, knob 28 white, checked track primary, `--ease` slide.

**Check sheet / data entry grid** (the signature form):
- Rows = shifts (กะเช้า 07:00–19:00 with sun tile, กะดึก with moon tile), columns = systems/machines with a 4px colored top border in the system color.
- Each cell: glass-card tile radius 18; large right-aligned number input (54px, 24px bold) with unit inside on the right; optional second small input (e.g. °C); live status dot under it; focus ring = system color 4px at 18%.
- Recorded cell becomes read-only summary (big value + ✓ บันทึกแล้ว in run color, run-tinted bg); double-click to edit → orange edit mode (ring `--abn`, "กำลังแก้ไข" badge, "เดิม …" old value shown, edit history kept).
- Under each shift row: meta bar (24h time, recorder, team A/B/C segmented, Running/Stopped segmented).
- Current shift row highlighted with primary-soft + 2px primary inset.
- Missing earlier entries → red banner at top; later days locked until backfilled.

**Modal**: centered glass sheet, radius 32, max 700px (wide 1100–1480px), scrim `--scrim` + blur(6px); header = back? · icon tile · bilingual title · close; sticky bottom action bar fading from transparent; enter `translateY(20px) scale(.97)` → none in .34s `--ease`. Prefer modal only for focused entry; detail can also be a side pane.

**Toast**: bottom-right, dark glass `--toast-bg`, radius 24, 48px icon tile + bold title + detail line (numbers bold), slides from right, auto-hide 3.8s.

**Tooltip (charts)**: glass-strong, radius 22, width 360, sections separated by 1px line, small primary uppercase section keys (`เกิดอะไรขึ้น / What happened`, `ข้อมูลน้ำมัน`, `สาเหตุ / รายละเอียด`), rows label-left value-right tabular.

**Empty / missing**: `.empty` centered fg-2 text with icon; missing-period card = dashed 2px line border + diagonal hatch `repeating-linear-gradient(135deg,transparent 0 10px,var(--surface-2) 10px 20px)`.

**Lists / tables**: grid rows (not `<table>`) 78px min, surface-2, radius 20, 8px gap; time big (24px bold), value huge (27px) with mini progress bar, status dot, sticky day headers fading out (`linear-gradient(var(--card) 70%,transparent)`). Hide low-priority columns at breakpoints.

## 8. Icons

Two families only, never emoji.
- **3D tile icons** (status/event/type): 48×48 viewBox; soft shadow tile offset 2.5px at 16% of the color; tile rect rx 14 with vertical gradient from color mixed 93% → 80% white (dark mode 66% → 80% into `#1c222c`); 0.75 white rim; glyph filled with vertical gradient (color +28% white → color −10% black) plus a 22% dark copy offset 1.6px down for depth; white highlights at 0.4–0.6 opacity. Palette: brand `#2A64E8`, refill `#0E9A7B`, oil change `#0F86A8`, leak `#D93A40`, drain `#2F7BF6`, low `#D39A06`, abnormal `#E36C12`, maintenance `#7652E8`, adjust `#4F6B8F`, running `#1C9B55`, idle `#7F8898`, day `#E7A21B`, night `#5566C8`, temperature `#E2683C`. Sizes 24–60.
- **Line icons** (navigation/actions): 24 viewBox, `stroke-width:2`, round caps/joins, `currentColor`, rounded-rect geometry.

## 9. Charts

- One lane per machine/system, each with its own Y scale; lane header = system dot (halo) · name · type chip · latest value pill · status · updated time · scale text.
- Primary series: monotone cubic line 2.8px in the system color, area gradient 22% → 0, points r4 (white 1.6 stroke); night readings = hollow centre.
- Secondary series (e.g. temperature): same hue mixed 45% toward `#1d2533`, dashed `6 4`, 2px, no fill, ring points, right axis.
- Zones: warning band `--abn` 12%, below-limit band `--leak` 7%, limit line `--leak` 1.6px dashed `6 5`.
- Grid: major lines 1.2px `--grid`, minor 0.7px at 70%; labels 13px fg-2; today column `--primary-soft` rounded; missing slots hatched and the line breaks (never interpolate over missing data).
- Event markers: 20–28px 3D icon tiles placed above the point with drop-shadow and a count badge; hover → glass tooltip, click → detail.
- Hover: column highlight 8% system color + enlarged points.
- Line draw-on animation 1s `--ease` on first render.

## 10. Motion

All on `--ease`. Page enter fade + translateY(12px) .36s · modal .34s · button press scale .97 · ripple .55s at 18% currentColor · toast slide 0.4s · tank/level fill 1.1s ease-in-out · pulsing alert ring 2.4s (only for unresolved critical items). Respect `prefers-reduced-motion` (durations → .01ms).

## 11. Applying to PySide6 / PyQt6 desktop apps

No backdrop blur in QSS, so: window bg `#E9EDF4` (paint the 4 radial ambients on the central widget via `QPainter` + `QRadialGradient`), cards `rgba(255,255,255,210)` with `border:1px solid rgba(255,255,255,200)`, `border-radius:26px`, add `QGraphicsDropShadowEffect(blurRadius=40, yOffset=12, color=rgba(20,30,60,18))`. Same tokens as a Python dict; buttons `min-height:60px; border-radius:30px`; primary uses `qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #4A7DEB, stop:1 #2862E6)`; inputs `min-height:56px; border:2px solid #DCE2EB; border-radius:16px`, focus `#2862E6`. Font `Thonburi` → fallback `Noto Sans Thai` / `Leelawadee UI`, 18px base. Charts in matplotlib: same colors, `linewidth=2.8`, `fill_between` alpha .22→0, zone `axhspan`, dashed limit line, no top/right spines, grid `#E1E6EE`. Animate with `QPropertyAnimation` using `QEasingCurve.OutCubic`.

## 12. Checklist before delivering

- [ ] Tokens defined once, light + dark, nothing hard-coded outside them
- [ ] Thai primary + secondary language on every label, from one dictionary
- [ ] Status colors match §3 exactly
- [ ] Hero numbers tabular, units smaller
- [ ] Touch targets ≥ 44px, primary actions ≥ 60px
- [ ] Empty / missing / error / loading states designed
- [ ] No horizontal scroll at 1920, 1440, 1280, 1024, 390px
- [ ] Reduced-motion respected; `:focus-visible` visible
- [ ] PDF/print uses fixed light paper