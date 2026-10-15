"""Generate the anime-style Hot Rolling Mill backdrop (day + night) as SVG.

    python -m tools.draw_scene        → web/img/scene-day.svg, web/img/scene-night.svg

Pure geometry: a pinhole camera projects simple 3D boxes / cylinders, painted far → near
with flat pastel fills, a warm outline and light atmospheric haze. Generic equipment only —
no company layout, names or data.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

W, H = 1600, 1000
CX, HY, F = 760, 430, 900          # vanishing point & focal length (px)
CAM = (1.2, 2.5, 0.0)              # eye position (m): standing next to the line
OUT = Path(__file__).resolve().parent.parent / "web" / "img"

DAY = dict(
    sky0="#A9D8F2", sky1="#E9F5FB", cloud="#FFFFFF", cloud_sh="#DCEEF8", ground_out="#CFE3C4",
    haze="#E3EEF4", line="#86705E", star=None,
    wall="#F5EDE0", wall_sh="#E7DAC6", wain="#D9CDB8", roof="#EFE6D8", truss="#B9A890",
    col=("#E9DFC9", "#F6EFE2", "#D8CBB2"), floor="#CDD5CE", floor_ln="#BCC6BF", walk="#E9DEC9",
    safety="#F2D27A", stripe="#FBFAF5",
    house=("#A8C3D3", "#C3D7E3", "#8EABBF"), cap=("#9DB9CB", "#BCD1DE", "#86A4B9"),
    roll=("#C9D1D8", "#E8EDF1", "#AEB8C1"), roll_hi="#F8FAFB", motor=("#BFD8B0", "#D6E7CB", "#A6C397"),
    strip="#DDE4EA", strip_hi="#FFFFFF", strip_edge="#AEB9C3", table=("#8FA3B4", "#A9BAC8", "#7A8FA1"),
    crane=("#F2D58A", "#F8E6B4", "#DDBB66"), coil=("#D3DAE0", "#ECF0F3", "#B6C0C9"), coil_ring="#BFC8D0",
    coil_eye="#7F8B96", saddle=("#C9B79B", "#DCCDB4", "#B19E80"),
    furn=("#EBC0A8", "#F4D6C5", "#D7A68B"), glow="#FFD9A0", glow_core="#FFF3D6",
    sign="#FFFDF7", sign_ic="#7FA9C8", sign_ic2="#E8B04E", lamp="#D9CFC0", lamp_glow=None, mist="#FFFFFF",
    rail="#E2A54A", pipe=("#B9D3C9", "#D2E4DD", "#9FBFB3"),
)
NIGHT = dict(
    sky0="#1B2444", sky1="#3B4878", cloud="#5A6797", cloud_sh="#46527F", ground_out="#2E3A4E",
    haze="#2A3350", line="#1A1F30", star="#F4F1DC",
    wall="#3E465E", wall_sh="#343B51", wain="#2F3549", roof="#383F56", truss="#59617A",
    col=("#4A526B", "#5A637D", "#3C435A"), floor="#3A4152", floor_ln="#454D60", walk="#444A5C",
    safety="#C9A64C", stripe="#5B6274",
    house=("#4F6A82", "#62809A", "#425A70"), cap=("#4A6379", "#5D7891", "#3E5468"),
    roll=("#7D8996", "#A3AFBB", "#66717D"), roll_hi="#D7E0EA", motor=("#56705A", "#6A866E", "#485E4B"),
    strip="#9CA9B8", strip_hi="#E4ECF5", strip_edge="#6E7C8B", table=("#3F4D5D", "#4D5D6F", "#35424F"),
    crane=("#C9A653", "#DDBE73", "#A98A41"), coil=("#8B97A4", "#A9B4C0", "#717D89"), coil_ring="#7A8693",
    coil_eye="#2A3140", saddle=("#6B6255", "#7D7366", "#5A5247"),
    furn=("#9A6E5E", "#B08372", "#835C4E"), glow="#FFB866", glow_core="#FFE7B8",
    sign="#5D6578", sign_ic="#9EC3E6", sign_ic2="#F0C06A", lamp="#6E6A66", lamp_glow="#FFE4A8", mist="#C9D6E8",
    rail="#C08A3C", pipe=("#4E6A62", "#607E75", "#435B54"),
)


# ── projection & helpers ─────────────────────────────────────────────
def P(x, y, z):
    return (CX + F * (x - CAM[0]) / z, HY - F * (y - CAM[1]) / z)


def pts(ps):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in ps)


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t):
    A, B = _hex(a), _hex(b)
    return "#" + "".join(f"{round(A[i] + (B[i] - A[i]) * t):02X}" for i in range(3))


class Scene:
    def __init__(self, pal):
        self.p = pal
        self.items: list[tuple[float, str]] = []   # (near z, svg) painted far → near
        self.fx: list[str] = []                    # cartoon sparkles, drawn on top

    def fog(self, c, z):
        return mix(c, self.p["haze"], max(0.0, min(0.55, (z - 8) / 140)))

    def sw(self, z):
        return max(1.3, min(4.2, 30 / z))

    def poly(self, ps3, fill, z=None, stroke=True, extra=""):
        z = z if z is not None else min(p[2] for p in ps3)
        st = f' stroke="{self.p["line"]}" stroke-width="{self.sw(z):.2f}" stroke-linejoin="round"' if stroke else ""
        return f'<polygon points="{pts([P(*p) for p in ps3])}" fill="{self.fog(fill, z)}"{st}{extra}/>'

    def add(self, z, svg):
        self.items.append((z, svg))

    # axis-aligned box with only camera-facing faces
    def box(self, x0, x1, y0, y1, z0, z1, cols, key=None):
        front, top, side = cols
        cx, cy, _ = CAM
        out = []
        if cy > y1:
            out.append(self.poly([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], top, z0))
        if cy < y0:
            out.append(self.poly([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], side, z0))
        if cx < x0:
            out.append(self.poly([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], side, z0))
        if cx > x1:
            out.append(self.poly([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], side, z0))
        out.append(self.poly([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], front, z0))
        # cel highlight: a light sliver inside the left and top edges of the front face
        if (x1 - x0) > .3 and (y1 - y0) > .3:
            dx, dy = min(.12, (x1 - x0) * .14), min(.12, (y1 - y0) * .14)
            out.append(self.poly([(x0 + dx * .6, y0 + dy * 2, z0), (x0 + dx * 1.6, y0 + dy * 2, z0),
                                  (x0 + dx * 1.6, y1 - dy * 1.6, z0), (x0 + dx * .6, y1 - dy * 1.6, z0)],
                                 top, z0, stroke=False, extra=' opacity=".9"'))
        self.add(key if key is not None else z0, "".join(out))

    # cylinder with axis along z (coil face toward the camera)
    def coil(self, x, y, z0, r, length, key=None):
        p = self.p
        z1 = z0 + length
        ring = [(x + r * math.cos(a), y + r * math.sin(a)) for a in (i * math.tau / 72 for i in range(72))]
        sample = [P(a, b, z0) for a, b in ring] + [P(a, b, z1) for a, b in ring]
        hull = _hull(sample)
        fx, fy = P(x, y, z0)
        R = F * r / z0
        sw = self.sw(z0)
        g = [f'<polygon points="{pts(hull)}" fill="{self.fog(p["coil"][2], z0)}" stroke="{p["line"]}" stroke-width="{sw:.2f}" stroke-linejoin="round"/>',
             f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{R:.1f}" fill="{self.fog(p["coil"][1], z0)}" stroke="{p["line"]}" stroke-width="{sw:.2f}"/>']
        for k in range(1, 7):
            rr = R * (0.36 + 0.6 * k / 7)
            g.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{rr:.1f}" fill="none" stroke="{self.fog(p["coil_ring"], z0)}" stroke-width="{max(.6, sw * .55):.2f}"/>')
        # light glint across the wraps
        g.append(f'<path d="M{fx - R * .78:.1f},{fy - R * .42:.1f} A{R * .9:.1f},{R * .9:.1f} 0 0 1 {fx - R * .2:.1f},{fy - R * .86:.1f}" fill="none" stroke="{p["strip_hi"]}" stroke-width="{max(1.2, R * .06):.1f}" stroke-linecap="round" opacity=".85"/>')
        g.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{R * .32:.1f}" fill="{self.fog(p["coil_eye"], z0)}" stroke="{p["line"]}" stroke-width="{sw:.2f}"/>')
        if R > 40:
            self.fx.append(_spark(fx + R * .55, fy - R * .62, R * .16, p["strip_hi"]))
            self.fx.append(_spark(fx + R * .78, fy - R * .3, R * .08, p["strip_hi"]))
        self.add(key if key is not None else z0, "".join(g))


def _spark(x, y, r, c):
    """Four-point anime glint."""
    k = r * .22
    d = (f"M{x:.1f},{y - r:.1f} Q{x + k:.1f},{y - k:.1f} {x + r:.1f},{y:.1f} Q{x + k:.1f},{y + k:.1f} {x:.1f},{y + r:.1f} "
         f"Q{x - k:.1f},{y + k:.1f} {x - r:.1f},{y:.1f} Q{x - k:.1f},{y - k:.1f} {x:.1f},{y - r:.1f}Z")
    return f'<path d="{d}" fill="{c}"/>'


def _hull(ps):
    ps = sorted(set((round(x, 1), round(y, 1)) for x, y in ps))
    if len(ps) < 3:
        return ps

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for q in ps:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0:
            lo.pop()
        lo.append(q)
    for q in reversed(ps):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def cloud(cx, cy, s, fill, shade):
    blobs = [(-60, 8, 38), (-20, -14, 50), (30, -6, 44), (70, 10, 32), (0, 14, 46)]
    sh = "".join(f'<circle cx="{cx + dx * s:.0f}" cy="{cy + dy * s + 8 * s:.0f}" r="{r * s:.0f}"/>' for dx, dy, r in blobs)
    fr = "".join(f'<circle cx="{cx + dx * s:.0f}" cy="{cy + dy * s:.0f}" r="{r * s:.0f}"/>' for dx, dy, r in blobs)
    return f'<g fill="{shade}">{sh}</g><g fill="{fill}">{fr}</g>'


# ── the hall ─────────────────────────────────────────────────────────
WALL_L, WALL_R, ROOF, BACK = -9.0, 9.0, 13.0, 130.0
STANDS = [21.0, 27.0, 33.0, 39.0]
STAND_D = 1.6
SX0, SX1, TOP = -2.2, -0.2, 0.95   # strip edges (m) and pass line height


def build(pal, night=False):
    S = Scene(pal)
    p = pal
    rnd = random.Random(7)
    bg = []
    # sky + clouds (seen through windows, skylights and the far door)
    bg.append(f'<rect width="{W}" height="{H}" fill="url(#sky)"/>')
    if night:
        for _ in range(160):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, HY), rnd.choice([0.7, 0.9, 1.2, 1.6])
            bg.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{p["star"]}" opacity="{rnd.uniform(.4, 1):.2f}"/>')
        bg.append(f'<circle cx="1180" cy="150" r="46" fill="#FFF6D8"/><circle cx="1198" cy="138" r="40" fill="{p["sky0"]}"/>')
    for cx_, cy_, s in [(180, 120, 1.5), (560, 70, 1.1), (980, 160, 1.7), (1400, 90, 1.3), (760, 330, .9), (1250, 300, 1.0), (300, 330, 1.1)]:
        bg.append(cloud(cx_, cy_, s, p["cloud"], p["cloud_sh"]))
    bg.append(f'<rect x="0" y="{HY:.0f}" width="{W}" height="20" fill="{p["ground_out"]}"/>')

    # back wall with a big open bay door
    back = [P(WALL_L, 0, BACK), P(WALL_R, 0, BACK), P(WALL_R, ROOF, BACK), P(WALL_L, ROOF, BACK)]
    door = [P(-3.5, 0, BACK), P(-3.5, 8.5, BACK), P(3.5, 8.5, BACK), P(3.5, 0, BACK)]
    bg.append(f'<path d="M{pts(back)}Z M{pts(door)}Z" fill-rule="evenodd" fill="{S.fog(p["wall_sh"], BACK)}" stroke="{p["line"]}" stroke-width=".8"/>')

    # roof with skylights
    roof = [(WALL_L, ROOF, 9), (WALL_R, ROOF, 9), (WALL_R, ROOF, BACK), (WALL_L, ROOF, BACK)]
    holes = ""
    for z0 in range(30, 120, 18):
        holes += "M" + pts([P(-3, ROOF, z0), P(3, ROOF, z0), P(3, ROOF, z0 + 7), P(-3, ROOF, z0 + 7)]) + "Z "
    bg.append(f'<path d="M{pts([P(*q) for q in roof])}Z {holes}" fill-rule="evenodd" fill="{p["roof"]}" stroke="{p["line"]}" stroke-width="1"/>')
    # trusses
    for z in range(26, 128, 9):
        a, b, c = P(WALL_L, ROOF - .9, z), P(WALL_R, ROOF - .9, z), P(0, ROOF, z)
        web = " ".join(f'M{P(x, ROOF - .9, z)[0]:.1f},{P(x, ROOF - .9, z)[1]:.1f} L{P(x + 1.5, ROOF, z)[0]:.1f},{P(x + 1.5, ROOF, z)[1]:.1f}' for x in range(-9, 9, 3))
        bg.append(f'<path d="M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f} {web}" stroke="{S.fog(p["truss"], z)}" stroke-width="{S.sw(z) * 1.2:.2f}" fill="none"/>')

    # side walls with tall windows
    for X, side in ((WALL_L, "L"), (WALL_R, "R")):
        wall = [P(X, 0, 3), P(X, ROOF, 3), P(X, ROOF, BACK), P(X, 0, BACK)]
        wins = ""
        for z0 in range(16, 124, 12):
            wins += "M" + pts([P(X, 5.6, z0 + 2), P(X, 10.4, z0 + 2), P(X, 10.4, z0 + 9), P(X, 5.6, z0 + 9)]) + "Z "
        bg.append(f'<path d="M{pts(wall)}Z {wins}" fill-rule="evenodd" fill="{p["wall"] if side == "L" else p["wall_sh"]}" stroke="{p["line"]}" stroke-width="1.4"/>')
        # window mullions
        for z0 in range(16, 124, 12):
            m0, m1 = P(X, 8.0, z0 + 2), P(X, 8.0, z0 + 9)
            v0, v1 = P(X, 5.6, z0 + 5.5), P(X, 10.4, z0 + 5.5)
            bg.append(f'<path d="M{m0[0]:.1f},{m0[1]:.1f}L{m1[0]:.1f},{m1[1]:.1f}M{v0[0]:.1f},{v0[1]:.1f}L{v1[0]:.1f},{v1[1]:.1f}" stroke="{S.fog(p["wain"], z0)}" stroke-width="{S.sw(z0) * 1.4:.2f}"/>')
        wain = [P(X, 0, 3), P(X, 2.4, 3), P(X, 2.4, BACK), P(X, 0, BACK)]
        bg.append(f'<polygon points="{pts(wain)}" fill="{p["wain"]}" stroke="{p["line"]}" stroke-width="1.2"/>')
        # crane rail girder
        rail = [P(X, 9.6, 3), P(X, 10.4, 3), P(X, 10.4, BACK), P(X, 9.6, BACK)]
        bg.append(f'<polygon points="{pts(rail)}" fill="{p["crane"][2]}" stroke="{p["line"]}" stroke-width="1.2"/>')
        # wall pipe
        pp = [P(X, 3.4, 3), P(X, 3.8, 3), P(X, 3.8, BACK), P(X, 3.4, BACK)]
        bg.append(f'<polygon points="{pts(pp)}" fill="{p["pipe"][0]}" stroke="{p["line"]}" stroke-width="1"/>')

    # floor
    fl = [P(WALL_L, 0, 3.02), P(WALL_R, 0, 3.02), P(WALL_R, 0, BACK), P(WALL_L, 0, BACK)]
    bg.append(f'<polygon points="{pts(fl)}" fill="{p["floor"]}"/>')
    ln = ""
    for x in range(-9, 10, 3):
        a, b = P(x, 0, 3.02), P(x, 0, BACK)
        ln += f"M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}"
    for z in [4, 6, 9, 13, 18, 24, 31, 40, 52, 68, 90]:
        a, b = P(WALL_L, 0, z), P(WALL_R, 0, z)
        ln += f"M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}"
    bg.append(f'<path d="{ln}" stroke="{p["floor_ln"]}" stroke-width="1.2"/>')
    # walkway (right) with yellow safety lines
    walk = [P(1.4, 0, 3.02), P(8.4, 0, 3.02), P(8.4, 0, BACK), P(1.4, 0, BACK)]
    bg.append(f'<polygon points="{pts(walk)}" fill="{p["walk"]}" opacity=".85"/>')
    for x in (1.4, 1.6, 8.2):
        a, b, c, d = P(x, 0, 3.02), P(x + .12, 0, 3.02), P(x + .12, 0, BACK), P(x, 0, BACK)
        bg.append(f'<polygon points="{pts([a, b, c, d])}" fill="{p["safety"]}"/>')
    # floor crossing stripes (like a zebra crossing across the walkway)
    for i in range(6):
        x0 = 2.0 + i * 1.05
        q = [P(x0, 0, 3.3), P(x0 + .6, 0, 3.3), P(x0 + .6, 0, 4.9), P(x0, 0, 4.9)]
        bg.append(f'<polygon points="{pts(q)}" fill="{p["stripe"]}" opacity=".95"/>')
    # line pit under the mill
    pit = [P(SX0 - .5, 0, 3.02), P(SX1 + .5, 0, 3.02), P(SX1 + .5, 0, 60), P(SX0 - .5, 0, 60)]
    bg.append(f'<polygon points="{pts(pit)}" fill="{mix(p["floor"], p["line"], .18)}"/>')

    # ── objects (painted far → near) ──
    # wall columns
    for z in range(14, 126, 12):
        S.box(WALL_L, WALL_L + .6, 0, 10.6, z, z + .6, p["col"])
        S.box(WALL_R - .6, WALL_R, 0, 10.6, z, z + .6, p["col"])

    # reheating furnace on the left, glowing door on its line-side face
    S.box(-8.6, -4.6, 0, 5.2, 44, 78, p["furn"])
    door_q = [(-4.6, .8, 46.5), (-4.6, 3.6, 46.5), (-4.6, 3.6, 52), (-4.6, .8, 52)]
    S.add(43.9, S.poly(door_q, p["glow"], 46.5) + S.poly([(-4.6, 1.2, 47.5), (-4.6, 3.1, 47.5), (-4.6, 3.1, 51), (-4.6, 1.2, 51)], p["glow_core"], 47.5, stroke=False))
    for z in (50, 62, 72):
        S.box(-7.4, -6.6, 5.2, 12.4, z, z + .8, p["pipe"], key=z - .1)

    # roughing mill (bigger, farther) and finishing stands
    def stand(z, scale=1.0):
        hgt = 6.2 * scale
        S.box(SX0 - 1.1, SX0 - .4, 0, hgt, z, z + STAND_D, p["house"])
        S.box(SX1 + .4, SX1 + 1.1, 0, hgt, z, z + STAND_D, p["house"])
        S.box(SX0 - 1.3, SX1 + 1.3, hgt, hgt + .8, z - .05, z + STAND_D + .05, p["cap"], key=z - .06)
        # rolls: front faces between the posts (backup / work / work / backup)
        for (y0, y1, c) in [(1.42, 2.95, p["roll"]), (1.0, 1.4, p["roll"]), (0.5, 0.9, p["roll"]), (-0.3, 0.48, p["roll"])]:
            q = [(SX0 - .4, y0, z + .1), (SX1 + .4, y0, z + .1), (SX1 + .4, y1, z + .1), (SX0 - .4, y1, z + .1)]
            hi = [(SX0 - .4, y0 + (y1 - y0) * .62, z + .1), (SX1 + .4, y0 + (y1 - y0) * .62, z + .1),
                  (SX1 + .4, y0 + (y1 - y0) * .78, z + .1), (SX0 - .4, y0 + (y1 - y0) * .78, z + .1)]
            S.add(z + .05, S.poly(q, c[0], z) + S.poly(hi, p["roll_hi"], z, stroke=False, extra=' opacity=".75"'))
        # screw-down housing window shadow above the rolls
        S.add(z + .04, S.poly([(SX0 - .4, 3.0, z + .1), (SX1 + .4, 3.0, z + .1), (SX1 + .4, hgt, z + .1), (SX0 - .4, hgt, z + .1)], p["house"][2], z))
        # drive spindle + motor on the right
        S.box(SX1 + 1.1, SX1 + 2.6, .3, 1.3, z + .4, z + 1.2, p["motor"], key=z + .2)
        S.box(SX1 + 2.6, SX1 + 3.6, 0, 1.9, z + .2, z + 1.4, p["motor"], key=z + .1)
        # coolant mist at the roll bite
        mx, my = P((SX0 + SX1) / 2, 1.2, z)
        rx = F * 1.6 / z
        S.add(z - .2, f'<g fill="{p["mist"]}" opacity=".55"><ellipse cx="{mx - rx * .5:.1f}" cy="{my:.1f}" rx="{rx * .55:.1f}" ry="{rx * .22:.1f}"/>'
                      f'<ellipse cx="{mx + rx * .3:.1f}" cy="{my - rx * .12:.1f}" rx="{rx * .45:.1f}" ry="{rx * .2:.1f}"/></g>')

    stand(58, 1.35)
    for z in STANDS:
        stand(z)

    # strip + run-out table, split into spans between stands
    spans = [(1.0, STANDS[0])] + [(a + STAND_D, b) for a, b in zip(STANDS, STANDS[1:])] + [(STANDS[-1] + STAND_D, 58)]
    for z0, z1 in spans:
        S.box(SX0 - .22, SX0 - .04, .55, TOP - .02, z0, z1, p["table"], key=z0 + .01)
        S.box(SX1 + .04, SX1 + .22, .55, TOP - .02, z0, z1, p["table"], key=z0 + .01)
        rolls = ""
        z = z0 + .6
        while z < z1 - .3:
            cx_, cy_ = P(SX1 + .22, .76, z)
            rolls += f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="{F * .09 / z:.1f}" fill="{S.fog(p["roll"][1], z)}" stroke="{p["line"]}" stroke-width="{S.sw(z) * .6:.2f}"/>'
            z += 1.3
        top = [(SX0, TOP, z0), (SX1, TOP, z0), (SX1, TOP, z1), (SX0, TOP, z1)]
        # long highlight streak along the strip (the "wet road" sheen)
        hl = [(SX0 + .55, TOP, z0), (SX0 + .95, TOP, z0), (SX0 + .95, TOP, z1), (SX0 + .55, TOP, z1)]
        hl2 = [(SX0 + 1.25, TOP, z0), (SX0 + 1.38, TOP, z0), (SX0 + 1.38, TOP, z1), (SX0 + 1.25, TOP, z1)]
        edge = [(SX0, TOP - .04, z0), (SX0, TOP, z0), (SX0, TOP, z1), (SX0, TOP - .04, z1)]
        S.add(z0, rolls + S.poly(edge, p["strip_edge"], z0) + S.poly(top, p["strip"], z0)
              + S.poly(hl, p["strip_hi"], z0, stroke=False, extra=' opacity=".8"') + S.poly(hl2, p["strip_hi"], z0, stroke=False, extra=' opacity=".6"'))

    for x, y, z, r in [(-1.25, TOP, 5.0, .22), (-1.6, TOP, 8.5, .16), (-1.0, TOP, 13.0, .12)]:
        sx_, sy_ = P(x, y, z)
        S.fx.append(_spark(sx_, sy_, F * r / z, p["strip_hi"]))

    # handrail between line and walkway
    rail = ""
    for z in [4.0, 6.5, 9.0, 11.5, 14.0, 16.5, 19.0]:
        a, b = P(.8, 0, z), P(.8, 1.1, z)
        rail += f'<path d="M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}" stroke="{p["line"]}" stroke-width="{S.sw(z) * 2.2:.1f}" stroke-linecap="round"/>' \
                f'<path d="M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}" stroke="{p["rail"]}" stroke-width="{S.sw(z) * 1.3:.1f}" stroke-linecap="round"/>'
    for y in (1.1, .6):
        a, b = P(.8, y, 4.0), P(.8, y, 19.0)
        rail += f'<path d="M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}" stroke="{p["line"]}" stroke-width="4.2" stroke-linecap="round"/>' \
                f'<path d="M{a[0]:.1f},{a[1]:.1f}L{b[0]:.1f},{b[1]:.1f}" stroke="{p["rail"]}" stroke-width="2.4" stroke-linecap="round"/>'
    S.add(3.4, rail)

    # coils on saddles along the walkway
    for x, z in [(6.0, 7.5), (6.0, 10.7), (6.0, 13.9), (6.0, 17.1), (6.0, 20.3)]:
        S.box(5.1, 6.9, 0, .35, z + .1, z + 1.5, p["saddle"], key=z + .12)
        S.coil(x, 1.25, z, .95, 1.6, key=z)

    # overhead crane carrying a coil
    zc = 30.0
    S.box(WALL_L + .6, WALL_R - .6, 10.4, 11.5, zc, zc + 1.4, p["crane"], key=zc - .3)
    S.box(2.6, 5.4, 11.5, 12.5, zc - .2, zc + 1.6, p["crane"], key=zc - .4)
    a1, a2 = P(3.5, 11.5, zc + .6), P(4.5, 11.5, zc + .6)
    h1, h2 = P(3.7, 8.6, zc + .6), P(4.3, 8.6, zc + .6)
    S.add(zc - .35, f'<path d="M{a1[0]:.1f},{a1[1]:.1f}L{h1[0]:.1f},{h1[1]:.1f}M{a2[0]:.1f},{a2[1]:.1f}L{h2[0]:.1f},{h2[1]:.1f}" stroke="{p["line"]}" stroke-width="1.6"/>')
    S.box(3.5, 4.5, 8.0, 8.6, zc + .3, zc + .9, p["crane"], key=zc - .36)
    S.coil(4.0, 6.9, zc, 1.0, 1.4, key=zc - .37)
    # warning stripes on the crane girder
    st = ""
    for x in [-8, -5.8, -3.6, -1.4, 0.8, 3.0, 5.2, 7.2]:
        q = [(x, 10.55, zc), (x + .5, 10.55, zc), (x + 1.0, 11.35, zc), (x + .5, 11.35, zc)]
        st += S.poly(q, p["line"], zc, stroke=False, extra=' opacity=".55"')
    S.add(zc - .31, st)

    # hanging high-bay lamps
    for x in (-4.5, 5.5):
        for z in range(30, 120, 15):
            c = P(x, 12.2, z)
            r = F * .55 / z
            glow = ""
            if p["lamp_glow"]:
                glow = f'<circle cx="{c[0]:.1f}" cy="{c[1] + r * .6:.1f}" r="{r * 3.2:.1f}" fill="url(#lampglow)"/>'
            top_ = P(x, ROOF, z)
            S.add(z - .5, glow + f'<path d="M{top_[0]:.1f},{top_[1]:.1f}L{c[0]:.1f},{c[1]:.1f}" stroke="{p["line"]}" stroke-width=".8"/>'
                  f'<path d="M{c[0] - r * .35:.1f},{c[1]:.1f}L{c[0] + r * .35:.1f},{c[1]:.1f}L{c[0] + r:.1f},{c[1] + r * .7:.1f}L{c[0] - r:.1f},{c[1] + r * .7:.1f}Z" fill="{S.fog(p["lamp"], z)}" stroke="{p["line"]}" stroke-width="{S.sw(z) * .7:.2f}" stroke-linejoin="round"/>')

    # signs: round hanging sign (coil icon) and a vertical banner — shapes only, no text
    sx, sy = P(8.4, 6.2, 15.6)
    r = F * .9 / 15.6
    S.add(15.5, f'<g stroke="{p["line"]}" stroke-width="2" stroke-linejoin="round">'
               f'<path d="M{sx + r * .2:.1f},{sy - r * 1.4:.1f}L{sx + r * .2:.1f},{sy - r:.1f}" fill="none"/>'
               f'<rect x="{sx - r * 1.2:.1f}" y="{sy - r:.1f}" width="{r * 2.4:.1f}" height="{r * 1.5:.1f}" rx="{r * .75:.1f}" fill="{p["sign"]}"/>'
               f'<circle cx="{sx:.1f}" cy="{sy - r * .25:.1f}" r="{r * .5:.1f}" fill="{p["sign_ic"]}"/>'
               f'<circle cx="{sx:.1f}" cy="{sy - r * .25:.1f}" r="{r * .18:.1f}" fill="{p["sign"]}"/></g>')
    bx, by = P(8.4, 8.6, 24.2)
    bw, bh = F * .55 / 24.2, F * 3.2 / 24.2
    dots = "".join(f'<rect x="{bx - bw * .28:.1f}" y="{by + bh * (.12 + i * .17):.1f}" width="{bw * .56:.1f}" height="{bh * .1:.1f}" rx="2" fill="{p["sign"]}"/>' for i in range(5))
    S.add(24.1, f'<g stroke="{p["line"]}" stroke-width="1.6"><rect x="{bx - bw / 2:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" fill="{p["motor"][0]}"/></g>{dots}'
               f'<circle cx="{bx:.1f}" cy="{by + bh * .96:.1f}" r="{bw * .22:.1f}" fill="{p["sign_ic"]}" stroke="{p["line"]}" stroke-width="1.4"/>')
    # floor information board on the walkway
    b0 = P(2.5, 0, 9.0)
    b1 = P(3.9, 0, 9.0)
    t0, t1 = P(2.5, 2.0, 9.0), P(3.9, 2.0, 9.0)
    m0, m1 = P(2.6, 1.9, 9.0), P(3.8, 1.0, 9.0)
    S.add(8.9, f'<g stroke="{p["line"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
              f'<path d="M{b0[0]:.1f},{b0[1]:.1f}L{t0[0]:.1f},{t0[1]:.1f}M{b1[0]:.1f},{b1[1]:.1f}L{t1[0]:.1f},{t1[1]:.1f}" stroke-width="6"/>'
              f'<path d="M{b0[0]:.1f},{b0[1]:.1f}L{t0[0]:.1f},{t0[1]:.1f}M{b1[0]:.1f},{b1[1]:.1f}L{t1[0]:.1f},{t1[1]:.1f}" stroke="{p["saddle"][0]}" stroke-width="3.4"/>'
              f'<rect x="{m0[0]:.1f}" y="{m0[1]:.1f}" width="{m1[0] - m0[0]:.1f}" height="{m1[1] - m0[1]:.1f}" rx="6" fill="{p["sign"]}"/></g>'
              f'<rect x="{m0[0] + 10:.1f}" y="{m0[1] + 12:.1f}" width="{(m1[0] - m0[0]) * .32:.1f}" height="{(m1[1] - m0[1]) * .32:.1f}" rx="4" fill="{p["sign_ic2"]}"/>'
              f'<rect x="{m0[0] + (m1[0] - m0[0]) * .5:.1f}" y="{m0[1] + 20:.1f}" width="{(m1[0] - m0[0]) * .36:.1f}" height="{(m1[1] - m0[1]) * .46:.1f}" rx="4" fill="{p["sign_ic"]}"/>'
              f'<rect x="{m0[0] + 10:.1f}" y="{m0[1] + (m1[1] - m0[1]) * .62:.1f}" width="{(m1[0] - m0[0]) * .3:.1f}" height="6" rx="3" fill="{p["coil_ring"]}"/>')

    body = "".join(svg for _, svg in sorted(S.items, key=lambda t: -t[0]))
    defs = (f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p["sky0"]}"/>'
            f'<stop offset=".55" stop-color="{p["sky1"]}"/></linearGradient>'
            '<radialGradient id="lampglow"><stop offset="0" stop-color="#FFE4A8" stop-opacity=".55"/><stop offset="1" stop-color="#FFE4A8" stop-opacity="0"/></radialGradient></defs>')
    ink = ('<filter id="ink" x="-2%" y="-2%" width="104%" height="104%">'
           '<feTurbulence type="fractalNoise" baseFrequency=".011" numOctaves="2" seed="3" result="n"/>'
           '<feDisplacementMap in="SourceGraphic" in2="n" scale="7" xChannelSelector="R" yChannelSelector="G"/></filter>'
           '<filter id="ink2" x="-2%" y="-2%" width="104%" height="104%">'
           '<feTurbulence type="fractalNoise" baseFrequency=".02" numOctaves="1" seed="9" result="n"/>'
           '<feDisplacementMap in="SourceGraphic" in2="n" scale="4" xChannelSelector="R" yChannelSelector="G"/></filter>')
    defs = defs.replace("</defs>", ink + "</defs>")
    sky, rest = bg[0], "".join(bg[1:])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMax slice">'
            f'{defs}{sky}<g filter="url(#ink)">{rest}</g><g filter="url(#ink2)">{body}{"".join(S.fx)}</g></svg>')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, pal, night in (("scene-day.svg", DAY, False), ("scene-night.svg", NIGHT, True)):
        (OUT / name).write_text(build(pal, night), encoding="utf-8")
        print(name, (OUT / name).stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
