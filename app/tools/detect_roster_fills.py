"""Detect yellow (special day) and green (substitution) cell fills in the scanned roster PDF.

Usage: python -m tools.detect_roster_fills <pdf> [--out hrm/data/roster_pdf_fills.json]
Needs `pdftoppm` (poppler) and Pillow + numpy. Writes {"YYYY-MM-DD": {"A": "special"|"substitution", ...}}.
Grid lines are found from the image (dark rows/columns), so no hard-coded pixel positions.
"""
from __future__ import annotations

import calendar
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

MONTHS = [(2026, m) for m in range(1, 13)] + [(2027, m) for m in range(1, 4)]


def _runs(mask, gap=3):
    idx = np.flatnonzero(mask)
    out, start = [], None
    for i, v in enumerate(idx):
        if start is None:
            start = prev = v
        elif v - prev > gap:
            out.append((start + prev) // 2)
            start = v
        prev = v
    if start is not None:
        out.append((start + prev) // 2)
    return out


def classify(rgb):
    r, g, b = rgb
    if r > 200 and g > 200 and b < 140:
        return "special"          # yellow
    if g > 150 and r < 190 and b < 150 and g - r > 25:
        return "substitution"     # green
    return None


def detect(pdf: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", "300", "-png", pdf, f"{td}/p"], check=True)
        im = Image.open(next(Path(td).glob("p*.png"))).convert("RGB")
    a = np.asarray(im).astype(int)
    gray = a.mean(axis=2)
    H, W = gray.shape
    hlines = _runs((gray < 120).sum(axis=1) > W * 0.5)
    # month blocks are delimited by the thick lines; each block = 2 header rows + 3 group rows
    blocks = [(hlines[i], hlines[i + 1]) for i in range(len(hlines) - 1) if 150 < hlines[i + 1] - hlines[i] < 220]
    blocks = blocks[:15]
    # One table → one column grid. Coloured fills hide lines in some months, so take the
    # grid from the block where the most vertical lines are visible (label + 31 days + WD = 34).
    grids = [_runs((gray[y0:y1] < 120).sum(axis=0) > (y1 - y0) * 0.6) for y0, y1 in blocks]
    vlines = max(grids, key=len)
    if len(vlines) != 34:
        raise RuntimeError(f"expected 34 vertical grid lines, found {len(vlines)}")
    out = {}
    for (y0, y1), (yy, mm) in zip(blocks, MONTHS):
        # block = 5 equal rows: day number, weekday, Group A, Group B, Group C
        h5 = (y1 - y0) / 5
        bands = [(int(y0 + h5 * k), int(y0 + h5 * (k + 1))) for k in (2, 3, 4)]
        cols = list(zip(vlines[:-1], vlines[1:]))[1:]            # skip label column
        n = calendar.monthrange(yy, mm)[1]
        for di in range(n):
            x0, x1 = cols[di]
            for gi, (r0, r1) in enumerate(bands):
                patch = a[r0 + 6:r1 - 6, x0 + 6:x1 - 6].reshape(-1, 3)
                # dominant colour = median of the brightest half (ignores glyph strokes)
                lum = patch.mean(axis=1)
                bg = np.median(patch[lum >= np.median(lum)], axis=0)
                kind = classify(bg)
                if kind:
                    out.setdefault(f"{yy}-{mm:02d}-{di + 1:02d}", {})["ABC"[gi]] = kind
    return out


if __name__ == "__main__":
    pdf = sys.argv[1]
    res = detect(pdf)
    if "--out" in sys.argv:
        Path(sys.argv[sys.argv.index("--out") + 1]).write_text(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, sort_keys=True))
