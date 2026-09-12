"""Build the stylised service-area map ("Einzugsgebiet") for Gartengestaltung Geißler.

Usage:  _tools/.venv/bin/python _tools/map/build_map.py [--svg-only]
Geodata: OpenStreetMap contributors (ODbL), cached in _tools/map/cache/.
Outputs: site/assets/img/map/einzugsgebiet*.{svg,webp,jpg}, _data/einzugsgebiet.json
"""
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import geodata  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FONT_DIR = os.path.join(ROOT, "site", "assets", "fonts")
OUT_DIR = os.path.join(ROOT, "site", "assets", "img", "map")
DATA_JSON = os.path.join(ROOT, "_data", "einzugsgebiet.json")
TMP_DIR = os.path.join(HERE, "_out")

RADIUS_KM = 30

C = {
    "bg": "#f7f6f5",
    "ctx_fill": "#ecebe7",
    "svc_fill": "#e6ebe2",
    "mil_fill": "#e3eadf",
    "line": "#d9d7d0",
    "sage": "#98b98c",
    "sage_dark": "#6f8f63",
    "green": "#017a33",
    "grey": "#707173",
    "text": "#131313",
    "water": "#a9c3c1",
}

# display labels (JSON keeps the official names)
SHORT = {
    "Obernburg am Main": "Obernburg",
    "Erlenbach am Main": "Erlenbach",
    "Klingenberg am Main": "Klingenberg",
    "Wörth am Main": "Wörth",
    "Sulzbach am Main": "Sulzbach",
}
NEVER_DROP = ["Aschaffenburg", "Miltenberg", "Obernburg am Main", "Amorbach", "Mespelbrunn"]
MAJOR = {"Aschaffenburg", "Miltenberg"}

# The site ships variable fonts; accept both the current names (…-normal.woff2) and the
# older per-weight copies (…-normal-400.woff2) so the map survives a font-folder rename.
FONT_FILES = {
    "sans": ["HankenGrotesk-normal.woff2", "HankenGrotesk-normal-400.woff2", "HankenGrotesk-normal-500.woff2"],
    "serif-i": ["Newsreader-italic.woff2", "Newsreader-italic-400.woff2", "Newsreader-italic-300.woff2"],
}
# (css family, css style, candidate files) for the SVG's @font-face src fallback list
CSS_FACES = [
    ("Hanken Grotesk", "normal", ["HankenGrotesk-normal.woff2", "HankenGrotesk-normal-400.woff2"]),
    ("Newsreader", "italic", ["Newsreader-italic.woff2", "Newsreader-italic-400.woff2"]),
]
_font_cache = {}


def _load_font(family, weight, size):
    for fn in FONT_FILES[family]:
        path = os.path.join(FONT_DIR, fn)
        if not os.path.exists(path):
            continue
        f = ImageFont.truetype(path, size)
        try:
            axes = f.get_variation_axes()
            vals = []
            for a in axes:
                nm = a.get("name", b"")
                nm = nm.decode() if isinstance(nm, bytes) else str(nm)
                if "eight" in nm:
                    vals.append(weight)
                elif "ptical" in nm:
                    vals.append(max(a["minimum"], min(a["maximum"], size)))
                else:
                    vals.append(a["default"])
            f.set_variation_by_axes(vals)
        except Exception:
            pass  # static font
        return f
    raise FileNotFoundError(f"no font file for {family} in {FONT_DIR}")


def measure(text, family="sans", weight=400, size=32, spacing=0.0):
    key = (family, weight, size)
    if key not in _font_cache:
        _font_cache[key] = _load_font(family, weight, size)
    f = _font_cache[key]
    w = f.getlength(text) + spacing * len(text)
    cap = -f.getbbox("H", anchor="ls")[1]
    top = -(cap + 0.14 * size)            # room for umlauts
    bottom = 0.24 * size if any(ch in text for ch in "gjpqy,") else 0.05 * size
    return w, top, bottom, cap


# --------------------------------------------------------------------------- geometry
def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Projection:
    """Equirectangular with cos(lat) correction, anchored on the company seat."""

    def __init__(self, lat0, lon0, px_per_km, cx, cy):
        self.lat0, self.lon0, self.cx, self.cy = lat0, lon0, cx, cy
        self.ky = 111.195 * px_per_km
        self.kx = 111.195 * math.cos(math.radians(lat0)) * px_per_km
        self.s = px_per_km

    def xy(self, lat, lon):
        return self.cx + (lon - self.lon0) * self.kx, self.cy - (lat - self.lat0) * self.ky

    def arr(self, coords_latlon):
        a = np.asarray(coords_latlon, dtype=float)
        return np.column_stack([self.cx + (a[:, 1] - self.lon0) * self.kx,
                                self.cy - (a[:, 0] - self.lat0) * self.ky])


def simplify(pts, tol):
    """Douglas-Peucker (iterative) on an (n,2) array."""
    n = len(pts)
    if n < 3:
        return pts
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = pts[i], pts[j]
        seg = pts[i + 1:j]
        ab = b - a
        L = math.hypot(*ab)
        if L == 0:
            d = np.hypot(*(seg - a).T)
        else:
            d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L
        k = int(np.argmax(d))
        if d[k] > tol:
            m = i + 1 + k
            keep[m] = True
            stack += [(i, m), (m, j)]
    return pts[keep]


def chaikin(pts, iterations=2, closed=False):
    for _ in range(iterations):
        if len(pts) < 3:
            return pts
        p = np.vstack([pts, pts[:1]]) if closed else pts
        q = 0.75 * p[:-1] + 0.25 * p[1:]
        r = 0.25 * p[:-1] + 0.75 * p[1:]
        mid = np.empty((len(q) * 2, 2))
        mid[0::2], mid[1::2] = q, r
        pts = mid if closed else np.vstack([p[:1], mid, p[-1:]])
    return pts


def densify(pts, step=7.0):
    if len(pts) < 2:
        return pts
    seg = pts[1:] - pts[:-1]
    L = np.hypot(seg[:, 0], seg[:, 1])
    res = []
    for i in range(len(seg)):
        n = max(1, int(L[i] // step))
        t = np.arange(n) / n
        res.append(pts[i] + np.outer(t, seg[i]))
    res.append(pts[-1:])
    return np.vstack(res)


def path_d(pts, closed=False):
    s = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    return s + ("Z" if closed else "")


def stitch(lines):
    """Join polylines that share endpoints into longer chains."""
    segs = [list(map(tuple, l)) for l in lines if len(l) > 1]
    out = []
    while segs:
        cur = segs.pop(0)
        grown = True
        while grown:
            grown = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                grown = True
                break
        out.append(cur)
    return out


def rings_of(geojson):
    t, c = geojson["type"], geojson["coordinates"]
    polys = [c] if t == "Polygon" else c
    for poly in polys:
        for ring in poly:
            yield [(lat, lon) for lon, lat in ring]


def point_in_rings(x, y, rings):
    inside = False
    for r in rings:
        xs, ys = r[:, 0], r[:, 1]
        xj, yj = np.roll(xs, 1), np.roll(ys, 1)
        cond = ((ys > y) != (yj > y)) & (x < (xj - xs) * (y - ys) / (yj - ys + 1e-12) + xs)
        if np.count_nonzero(cond) % 2:
            inside = not inside
    return inside


class Box:
    __slots__ = ("x0", "y0", "x1", "y1", "tag")

    def __init__(self, x0, y0, x1, y1, tag=""):
        self.x0, self.y0, self.x1, self.y1, self.tag = x0, y0, x1, y1, tag

    def pad(self, p):
        return Box(self.x0 - p, self.y0 - p, self.x1 + p, self.y1 + p, self.tag)

    def overlap(self, o):
        w = min(self.x1, o.x1) - max(self.x0, o.x0)
        h = min(self.y1, o.y1) - max(self.y0, o.y0)
        return w * h if (w > 0 and h > 0) else 0.0

    def inside(self, x0, y0, x1, y1):
        return self.x0 >= x0 and self.y0 >= y0 and self.x1 <= x1 and self.y1 <= y1

    def dist(self, x, y):
        dx = max(self.x0 - x, 0, x - self.x1)
        dy = max(self.y0 - y, 0, y - self.y1)
        return math.hypot(dx, dy)


def pts_in_box(pts, b):
    if pts is None or len(pts) == 0:
        return 0
    m = (pts[:, 0] >= b.x0) & (pts[:, 0] <= b.x1) & (pts[:, 1] >= b.y0) & (pts[:, 1] <= b.y1)
    return int(m.sum())


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --------------------------------------------------------------------------- variants
VARIANTS = {
    "landscape": dict(W=2400, H=1800, s=22.0, cx=1370, cy=905, label_size=31, major_size=34,
                      landscape_names=[("Spessart", 49.985, 9.445, None), ("Odenwald", 49.70, 8.90, None)],
                      district_labels=[("Landkreis Miltenberg", 49.62, 9.30, "lk_miltenberg"),
                                       ("Landkreis Aschaffenburg", 50.10, 9.30, "lk_aschaffenburg")],
                      arc_pref=-45, river_label_pref=(50.11, 8.78)),
    "portrait": dict(W=1500, H=2000, s=20.0, cx=750, cy=1010, label_size=31, major_size=34,
                     landscape_names=[("Spessart", 50.00, 9.44, None), ("Odenwald", 49.58, 9.06, None)],
                     district_labels=[("Landkreis Miltenberg", 49.60, 9.30, "lk_miltenberg"),
                                      ("Landkreis Aschaffenburg", 50.10, 9.30, "lk_aschaffenburg")],
                     arc_pref=-55, river_label_pref=(50.12, 8.85)),
}


def build_variant(name, cfg, geo):
    W, H, s = cfg["W"], cfg["H"], cfg["s"]
    center = geo["center"]
    P = Projection(center["lat"], center["lon"], s, cfg["cx"], cfg["cy"])
    R = RADIUS_KM * s
    ex, ey = P.xy(center["lat"], center["lon"])
    view = (-60, -60, W + 60, H + 60)
    margin = 72
    obstacles = []   # static boxes (dots, pin, UI, arc text)
    border_pts = []
    rings_px = {}

    # ---------------- districts
    def district_paths(keys, tol=0.7):
        ds = []
        for k in keys:
            b = geo["boundaries"].get(k)
            if not b:
                continue
            parts = []
            for ring in rings_of(b["geojson"]):
                pts = P.arr(ring)
                if (pts[:, 0].max() < view[0] or pts[:, 0].min() > view[2]
                        or pts[:, 1].max() < view[1] or pts[:, 1].min() > view[3]):
                    continue
                pts = simplify(pts, tol)
                if len(pts) >= 4:
                    parts.append(path_d(pts, closed=True))
                    border_pts.append(densify(pts))
                    rings_px.setdefault(k, []).append(pts)
            if parts:
                ds.append((k, " ".join(parts)))
        return ds

    ctx_keys = [k for k, v in geo["boundaries"].items() if v["role"] == "context"]
    ctx = district_paths(ctx_keys)
    svc = district_paths(["lk_aschaffenburg", "st_aschaffenburg"])
    mil = district_paths(["lk_miltenberg"])

    # ---------------- rivers
    main_px = [chaikin(simplify(P.arr(ch), 1.2), 2) for ch in stitch([l["coords"] for l in geo["rivers"]["main"]])]
    main_all = np.vstack([densify(p) for p in main_px])
    streams_px = []
    by_name = {}
    for l in geo["rivers"]["streams"]:
        by_name.setdefault(l["name"], []).append(l["coords"])
    for nm, lines in by_name.items():
        for ch in stitch(lines):
            streams_px.append((nm, chaikin(simplify(P.arr(ch), 1.2), 2)))
    water_all = np.vstack([main_all] + [densify(p) for _, p in streams_px])

    ang = np.linspace(0, 2 * math.pi, 900)
    circle_pts = np.column_stack([ex + R * np.cos(ang), ey + R * np.sin(ang)])
    line_all = np.vstack([water_all, circle_pts] + border_pts)

    # ---------------- fixed UI furniture (bottom-left scale + north, bottom-right attribution)
    km10 = 10 * s
    sb_x, sb_y = margin + 8, H - margin - 36
    obstacles.append(Box(sb_x - 20, sb_y - 170, sb_x + km10 + 90, sb_y + 50, "scale"))
    attr = "Kartendaten © OpenStreetMap-Mitwirkende (ODbL)"
    aw, at, ab, _ = measure(attr, "sans", 400, 22)
    ax, ay = W - margin, H - margin + 12
    obstacles.append(Box(ax - aw - 16, ay + at - 12, ax + 10, ay + ab + 10, "attr"))

    # ---------------- towns (dots are hard obstacles for every label)
    pin_r = 58
    obstacles.append(Box(ex - pin_r, ey - pin_r, ex + pin_r, ey + pin_r, "pin"))
    town_dots = []
    dot_boxes = []
    for t in geo["towns"]:
        if t["name"] == "Eschau":
            continue
        x, y = P.xy(t["lat"], t["lon"])
        town_dots.append((t, x, y))
        dot_boxes.append(Box(x - 9, y - 9, x + 9, y + 9, "dot:" + t["name"]))

    # ---------------- Eschau label block
    e_size, cap_size = 66, 25
    e_w, e_top, e_bot, _ = measure("Eschau", "serif-i", 400, e_size)
    c_txt = "Gartengestaltung Geißler"
    c_w, c_top, c_bot, _ = measure(c_txt, "sans", 500, cap_size, spacing=0.4)
    gap_line = 12
    block_w = max(e_w, c_w)
    block_h = (-e_top) + e_bot + gap_line + (-c_top) + c_bot

    def eschau_candidates():
        off = 40
        e_hi = ey - 26 + e_top          # block top so that the caption sits level with the pin
        yield "start", ex + off, e_hi                       # E
        yield "start", ex + off * 0.7, ey - block_h - 18    # NE
        yield "start", ex + off * 0.7, ey + 34              # SE
        yield "end", ex - off, e_hi                         # W
        yield "end", ex - off * 0.7, ey - block_h - 18      # NW
        yield "end", ex - off * 0.7, ey + 34                # SW

    best = None
    for pref, (anchor, bx, by) in enumerate(eschau_candidates()):
        x0 = bx if anchor == "start" else bx - block_w
        box = Box(x0, by, x0 + block_w, by + block_h, "eschau")
        hits = sum(box.pad(10).overlap(o) > 0 for o in dot_boxes)
        cost = pref + 20 * hits + 3 * min(pts_in_box(main_all, box.pad(4)), 3)
        if best is None or cost < best[0]:
            best = (cost, anchor, bx, by, box)
    _, e_anchor, e_bx, e_by, e_box = best
    obstacles.append(e_box)
    e_base = e_by - e_top
    c_base = e_base + e_bot + gap_line - c_top

    # ---------------- "Einzugsgebiet · ca. 30 km" along the circle (angle search: away from water/dots)
    arc_txt = "Einzugsgebiet · ca. 30 km"
    arc_size, arc_sp = 23, 3.0
    aw2, _, _, _ = measure(arc_txt, "sans", 500, arc_size, spacing=arc_sp)
    arc_R = R + 14
    span = math.degrees((aw2 + 40) / arc_R)
    ring_mask = np.abs(np.hypot(water_all[:, 0] - ex, water_all[:, 1] - ey) - (arc_R + 14)) < 40
    ring_water = water_all[ring_mask]
    best_arc = None
    for mid in list(range(-88, -6, 2)):
        a_s = np.radians(np.linspace(mid - span / 2, mid + span / 2, 18))
        sx = ex + (arc_R + 12) * np.cos(a_s)
        sy = ey + (arc_R + 12) * np.sin(a_s)
        boxes = [Box(x - 17, y - 17, x + 17, y + 17, "arc") for x, y in zip(sx, sy)]
        if not all(b.inside(margin, margin, W - margin, H - margin) for b in boxes):
            continue
        hit_w = sum(pts_in_box(ring_water, b) for b in boxes)
        hit_o = sum(1 for b in boxes for o in dot_boxes + obstacles if b.pad(8).overlap(o))
        cost = hit_w * 2 + hit_o * 50 + abs(mid - cfg["arc_pref"]) / 4
        if best_arc is None or cost < best_arc[0]:
            best_arc = (cost, mid, boxes)
    _, arc_mid, arc_boxes = best_arc
    obstacles += arc_boxes
    a0, a1 = math.radians(arc_mid - span / 2), math.radians(arc_mid + span / 2)
    arc_d = (f"M{ex + arc_R * math.cos(a0):.1f} {ey + arc_R * math.sin(a0):.1f} "
             f"A{arc_R:.1f} {arc_R:.1f} 0 0 1 {ex + arc_R * math.cos(a1):.1f} {ey + arc_R * math.sin(a1):.1f}")

    # ---------------- town labels: 8 positions, greedy by priority + one-swap repair
    safe = (margin - 20, margin - 20, W - margin + 20, H - margin + 20)
    all_dots = [(x, y) for _, x, y in town_dots]
    cands = {}
    meta = {}
    for t, x, y in town_dots:
        disp = SHORT.get(t["name"], t["name"])
        major = t["name"] in MAJOR
        size = cfg["major_size"] if major else cfg["label_size"]
        weight = 500 if major else 400
        w, top, bot, cap = measure(disp, "sans", weight, size)
        meta[t["name"]] = (disp, major, size, x, y)
        rd, g = 8, 11
        vc = cap / 2
        positions = [
            ("start", x + rd + g, y + vc),                  # E
            ("start", x + rd * 0.5 + 5, y - rd - 7),        # NE
            ("start", x + rd * 0.5 + 5, y + rd + 7 + cap),  # SE
            ("end", x - rd - g, y + vc),                    # W
            ("end", x - rd * 0.5 - 5, y - rd - 7),          # NW
            ("end", x - rd * 0.5 - 5, y + rd + 7 + cap),    # SW
            ("middle", x, y - rd - 11),                     # N
            ("middle", x, y + rd + 11 + cap),               # S
        ]
        lst = []
        own = "dot:" + t["name"]
        for pref, (anchor, bx, by) in enumerate(positions):
            x0 = bx if anchor == "start" else (bx - w if anchor == "end" else bx - w / 2)
            box = Box(x0, by + top, x0 + w, by + bot, "lbl:" + t["name"])
            if not box.inside(*safe):
                continue
            # pin is a circle (pulse ring): test true distance instead of its bounding square
            hit_tags = [o.tag for o in obstacles if o.tag != "pin" and box.pad(5).overlap(o)] + \
                (["pin"] if box.dist(ex, ey) < pin_r + 6 else []) + \
                [o.tag for o in dot_boxes if o.tag != own and box.pad(5).overlap(o)]
            static_hit = bool(hit_tags)
            d_own = box.dist(x, y)
            d_other = min((box.dist(ox, oy) for ox, oy in all_dots if (ox, oy) != (x, y)), default=1e9)
            ambiguous = d_other < d_own * 1.3 + 8
            cost = (pref * 1.0 + 4 * min(pts_in_box(main_all, box.pad(2)), 2)
                    + 3 * min(pts_in_box(circle_pts, box.pad(3)), 2) + (14 if ambiguous else 0))
            lst.append((cost, static_hit, anchor, bx, by, box, pref, hit_tags))
        lst.sort(key=lambda c: c[0])
        cands[t["name"]] = lst

    def order_key(item):
        t = item[0]
        if t["name"] in NEVER_DROP:
            return (0, NEVER_DROP.index(t["name"]))
        return (1, -t.get("population", 0))

    # Each town picks one of its 8 candidate positions or is left unlabeled. Overlapping labels are
    # a hard constraint; leaving a town unlabeled costs more the larger the town is. Greedy start,
    # then simulated annealing (deterministic seed) to find a better global arrangement.
    names = [t["name"] for t, _, _ in sorted(town_dots, key=order_key)]
    pops = {t["name"]: (t.get("population") or 4500) for t, _, _ in town_dots}
    opts = {}
    for nm in names:
        o_ = [c for c in cands[nm] if not c[1]]
        if not o_ and nm in NEVER_DROP:
            print(f"  ! forced label has no obstacle-free position: {nm}")
            o_ = [(c[0] + 200,) + c[1:] for c in cands[nm]]
        opts[nm] = o_
    drop_pen = {nm: 20 + pops[nm] / 400 for nm in names}

    idx = [(nm, k) for nm in names for k in range(len(opts[nm]))]
    conflict = {key: {} for key in idx}
    for a in range(len(idx)):
        na, ka = idx[a]
        ba = opts[na][ka][5].pad(7)   # breathing room between neighbouring labels
        for b in range(a + 1, len(idx)):
            nb, kb = idx[b]
            if nb != na and ba.overlap(opts[nb][kb][5]):
                conflict[(na, ka)].setdefault(nb, set()).add(kb)
                conflict[(nb, kb)].setdefault(na, set()).add(ka)

    state = {nm: -1 for nm in names}
    for nm in names:
        for k in range(len(opts[nm])):
            if not any(state[o] in ks for o, ks in conflict[(nm, k)].items()):
                state[nm] = k
                break
        if state[nm] == -1 and nm in NEVER_DROP and opts[nm]:
            state[nm] = 0

    def local(nm, k):
        if k < 0:
            return drop_pen[nm]
        return opts[nm][k][0] + 1000 * sum(1 for o, ks in conflict[(nm, k)].items() if state[o] in ks)

    def total():
        e, hard = 0.0, 0
        for nm in names:
            k = state[nm]
            if k < 0:
                e += drop_pen[nm]
            else:
                e += opts[nm][k][0]
                hard += sum(1 for o, ks in conflict[(nm, k)].items() if state[o] in ks)
        return e + 500 * hard, hard // 2

    rng = random.Random(42)
    cur_e, cur_h = total()
    greedy_e, greedy_dropped = cur_e, [nm for nm in names if state[nm] < 0]
    best_e, best_state = (cur_e, dict(state)) if cur_h == 0 else (float("inf"), dict(state))
    iters = 120000
    for it in range(iters):
        T = 30.0 * (0.01 / 30.0) ** (it / iters)
        nm = names[rng.randrange(len(names))]
        choices = list(range(len(opts[nm]))) + ([] if nm in NEVER_DROP else [-1])
        if len(choices) < 2:
            continue
        new = choices[rng.randrange(len(choices))]
        old = state[nm]
        if new == old:
            continue
        d = local(nm, new) - local(nm, old)
        if d <= 0 or rng.random() < math.exp(-d / T):
            state[nm] = new
            cur_e += d
            if cur_e < best_e - 1e-9:
                e_chk, h = total()
                if h == 0:
                    best_e, best_state = e_chk, dict(state)
    state = best_state
    placed = {nm: opts[nm][k] for nm, k in state.items() if k >= 0}
    dropped = [nm for nm in names if state[nm] < 0]
    if os.environ.get("MAP_DEBUG"):
        pos = ["E", "NE", "SE", "W", "NW", "SW", "N", "S"]
        print(f"  [debug {name}] greedy energy {greedy_e:.1f} dropped={greedy_dropped}")
        print(f"  [debug {name}] annealed energy {best_e:.1f} dropped={dropped}")
        for nm in dropped:
            print(f"    {nm}: {len(cands[nm])} in-bounds candidates, {len(opts[nm])} obstacle-free")
            for c in cands[nm]:
                line = f"      {pos[c[6]]:2s} cost={c[0]:.1f}"
                if c[1]:
                    line += f" static:{c[7]}"
                else:
                    k = opts[nm].index(c)
                    blockers = [f"{o}@{pos[opts[o][state[o]][6]]}" for o, ks in conflict[(nm, k)].items()
                                if state[o] in ks]
                    line += f" blocked-by:{blockers}"
                print(line)

    label_boxes = [c[5] for c in placed.values()]
    labels_svg, dots_svg = [], []
    for t, x, y in town_dots:
        nm = t["name"]
        if nm in placed:
            dots_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" class="town-dot"/>')
            anchor, bx, by = placed[nm][2], placed[nm][3], placed[nm][4]
            disp, major, size, _, _ = meta[nm]
            cls = "t-town t-major" if major else "t-town"
            labels_svg.append(f'<text x="{bx:.1f}" y="{by:.1f}" text-anchor="{anchor}" class="{cls}" '
                              f'font-size="{size}">{esc(disp)}</text>')
        else:
            dots_svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" class="town-dot town-dot--minor"/>')

    # ---------------- decorative names: free-spot search near a preferred point
    taken = obstacles + dot_boxes + label_boxes

    def find_spot(w, top, bot, px, py, within=None, radius=240, step=12):
        best = None
        for dy in range(-radius, radius + 1, step):
            for dx in range(-radius, radius + 1, step):
                x, y = px + dx, py + dy
                box = Box(x - w / 2, y + top, x + w / 2, y + bot)
                if not box.inside(margin + 40, margin + 30, W - margin - 40, H - margin - 30):
                    continue
                if any(box.pad(22).overlap(o) for o in taken):
                    continue
                if within is not None and not point_in_rings(x, y + (top + bot) / 2, within):
                    continue
                hits = pts_in_box(line_all, box.pad(3))
                if hits > 5:          # at most one thin line may cross the (spaced) lettering
                    continue
                cost = math.hypot(dx, dy) / 40 + 8.0 * hits
                if best is None or cost < best[0]:
                    best = (cost, x, y, box)
        return best

    deco_svg = []
    for label, lat, lon, _ in cfg["landscape_names"]:
        size, sp = 44, 10.0
        w, top, bot, _ = measure(label, "serif-i", 300, size, spacing=sp)
        spot = find_spot(w, top, bot, *P.xy(lat, lon))
        if spot:
            _, x, y, box = spot
            taken.append(box)
            deco_svg.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" class="t-area" '
                            f'font-size="{size}" letter-spacing="{sp}">{esc(label)}</text>')
        else:
            print("  ! no spot for", label)
    for label, lat, lon, key in cfg["district_labels"]:
        size, sp = 19, 5.2
        txt = label.upper()
        w, top, bot, _ = measure(txt, "sans", 500, size, spacing=sp)
        spot = find_spot(w, top, bot, *P.xy(lat, lon), within=rings_px.get(key), radius=420, step=14)
        if spot:
            _, x, y, box = spot
            taken.append(box)
            deco_svg.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" class="t-district" '
                            f'font-size="{size}" letter-spacing="{sp}">{esc(txt)}</text>')
        else:
            print("  ! no spot for", label)

    # ---------------- river label "Main" on a calm stretch of the river
    river_label_svg = ""
    txt = "Main"
    rw, _, _, _ = measure(txt, "serif-i", 400, 40, spacing=4)
    need = rw + 40
    prefx, prefy = P.xy(*cfg["river_label_pref"])
    bestw = None
    for ch in main_px:
        dch = densify(ch, 4)
        seglen = np.hypot(*np.diff(dch, axis=0).T)
        cum = np.concatenate([[0], np.cumsum(seglen)])
        for i in range(0, len(dch), 4):
            j = int(np.searchsorted(cum, cum[i] + need))
            if j >= len(dch):
                break
            win = dch[i:j + 1]
            a, b = win[0], win[-1]
            ab = b - a
            L = math.hypot(*ab)
            dev = np.abs(ab[0] * (win[:, 1] - a[1]) - ab[1] * (win[:, 0] - a[0])).max() / max(L, 1e-6)
            if dev > 10 or abs(ab[1]) > abs(ab[0]) * 0.9:
                continue
            box = Box(win[:, 0].min() - 8, win[:, 1].min() - 60, win[:, 0].max() + 8, win[:, 1].max() + 10)
            if not box.inside(margin + 40, margin + 40, W - margin - 40, H - margin - 40):
                continue
            if any(box.pad(10).overlap(o) for o in taken):
                continue
            # glyphs sit left of the reading direction, 16-44 px off the line: that band must be river-free
            # the label is set on the straight chord (parallel to the river); glyphs sit 16-44 px above it
            ww = win if win[-1, 0] >= win[0, 0] else win[::-1]
            dirv = (ww[-1] - ww[0]) / max(L, 1e-6)
            nrm = np.array([dirv[1], -dirv[0]])
            core = ww[0] + np.outer(np.linspace(20, L - 20, 24), dirv)
            band = np.vstack([core + nrm * off for off in (18, 30, 42)])
            bb = Box(band[:, 0].min(), band[:, 1].min(), band[:, 0].max(), band[:, 1].max()).pad(12)
            near = main_all[(main_all[:, 0] >= bb.x0) & (main_all[:, 0] <= bb.x1)
                            & (main_all[:, 1] >= bb.y0) & (main_all[:, 1] <= bb.y1)]
            if len(near):
                dmin = np.sqrt(((band[:, None, :] - near[None, :, :]) ** 2).sum(-1)).min()
                if dmin < 7:
                    continue
            mx, my = win[len(win) // 2]
            d = math.hypot(mx - prefx, my - prefy) + dev * 8
            if bestw is None or d < bestw[0]:
                bestw = (d, win, box)
    if bestw:
        _, win, box = bestw
        if win[-1, 0] < win[0, 0]:
            win = win[::-1]
        taken.append(box)
        text_path = np.array([win[0], win[-1]])   # straight chord parallel to the river
        river_label_svg = (f'<path id="main-label-path-{name}" d="{path_d(text_path)}" fill="none"/>'
                           f'<text class="t-river" font-size="40" letter-spacing="4" dy="-16">'
                           f'<textPath href="#main-label-path-{name}" startOffset="50%" text-anchor="middle">{txt}</textPath></text>')

    # ---------------- assemble SVG
    font_face = "".join(
        f"@font-face{{font-family:'{fam}';font-style:{st};font-weight:300 500;font-display:swap;src:"
        + ",".join(f"url('../../fonts/{fn}') format('woff2')" for fn in files) + "}"
        for fam, st, files in CSS_FACES)
    style = (
        "/*FONTFACE-BEGIN*/" + font_face + "/*FONTFACE-END*/"
        ".t-town,.t-district,.t-ui,.t-caption{font-family:'Hanken Grotesk',ui-sans-serif,system-ui,sans-serif}"
        ".t-eschau,.t-area,.t-river{font-family:'Newsreader',Georgia,'Times New Roman',serif;font-style:italic}"
        f".t-town{{fill:{C['text']};font-weight:400;paint-order:stroke;stroke:{C['bg']};stroke-width:6px;"
        "stroke-opacity:.6;stroke-linejoin:round}"
        ".t-major{font-weight:500}"
        f".t-area{{fill:{C['sage_dark']};fill-opacity:.55;font-weight:300}}"
        f".t-district{{fill:{C['sage_dark']};fill-opacity:.8;font-weight:500;paint-order:stroke;stroke:#eef1ea;"
        "stroke-width:5px;stroke-opacity:.85;stroke-linejoin:round}"
        ".t-river{fill:#86a8a6;font-weight:400}"
        f".t-ui{{fill:{C['grey']};font-weight:400}}"
        f".town-dot{{fill:{C['grey']};stroke:#fff;stroke-width:3px}}"
        ".town-dot--minor{fill-opacity:.55;stroke-width:2px}"
        ".pin-eschau .pulse{transform-box:fill-box;transform-origin:center}"
    )

    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             f'role="img" aria-labelledby="map-title-{name} map-desc-{name}">')
    o.append(f'<title id="map-title-{name}">Einzugsgebiet Gartengestaltung Geißler</title>')
    o.append(f'<desc id="map-desc-{name}">Karte des Einzugsgebiets rund um Eschau (ca. {RADIUS_KM} km) '
             f'mit den Landkreisen Miltenberg und Aschaffenburg. Kartendaten © OpenStreetMap-Mitwirkende (ODbL).</desc>')
    o.append(f"<defs><style>{style}</style>")
    o.append(f'<radialGradient id="fade-{name}" cx="50%" cy="50%" r="62%">'
             '<stop offset="0.40" stop-color="#fff"/><stop offset="0.78" stop-color="#fff" stop-opacity="0.4"/>'
             '<stop offset="0.96" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    o.append(f'<radialGradient id="fade-water-{name}" cx="50%" cy="50%" r="64%">'
             '<stop offset="0.60" stop-color="#fff"/><stop offset="0.95" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    o.append(f'<mask id="m-ctx-{name}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
             f'<rect width="{W}" height="{H}" fill="url(#fade-{name})"/></mask>')
    o.append(f'<mask id="m-water-{name}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
             f'<rect width="{W}" height="{H}" fill="url(#fade-water-{name})"/></mask>')
    o.append(f'<radialGradient id="svc-{name}" gradientUnits="userSpaceOnUse" cx="{ex:.1f}" cy="{ey:.1f}" r="{R:.1f}">'
             f'<stop offset="0" stop-color="{C["sage"]}" stop-opacity="0.34"/>'
             f'<stop offset="0.55" stop-color="{C["sage"]}" stop-opacity="0.24"/>'
             f'<stop offset="1" stop-color="{C["sage"]}" stop-opacity="0.13"/></radialGradient>')
    o.append(f'<path id="arc-{name}" d="{arc_d}" fill="none"/>')
    o.append("</defs>")
    o.append(f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>')

    o.append(f'<g class="districts-context" mask="url(#m-ctx-{name})" fill="none" stroke="{C["line"]}" '
             'stroke-width="1.6" stroke-opacity="0.8" stroke-linejoin="round">')
    o += [f'<path d="{d}"/>' for _, d in ctx]
    o.append("</g>")
    o.append(f'<g class="districts-service" fill="{C["svc_fill"]}" stroke="{C["line"]}" stroke-width="1.8" stroke-linejoin="round">')
    o += [f'<path d="{d}"/>' for _, d in svc]
    o.append("</g>")
    o.append(f'<g class="district-miltenberg" fill="{C["mil_fill"]}" stroke="{C["sage"]}" stroke-width="2.6" stroke-linejoin="round">')
    o += [f'<path d="{d}"/>' for _, d in mil]
    o.append("</g>")

    o.append(f'<g class="service-area"><circle cx="{ex:.1f}" cy="{ey:.1f}" r="{R:.1f}" fill="url(#svc-{name})"/>'
             f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{R:.1f}" fill="none" stroke="{C["sage"]}" stroke-width="2.6" '
             'stroke-dasharray="1 13" stroke-linecap="round"/></g>')

    o.append(f'<g class="water" mask="url(#m-water-{name})">'
             f'<g fill="none" stroke="{C["water"]}" stroke-linecap="round" stroke-linejoin="round">')
    for nm, pts in streams_px:
        o.append(f'<path d="{path_d(pts)}" stroke-width="2.6" stroke-opacity="0.85"/>')
    for pts in main_px:
        o.append(f'<path d="{path_d(pts)}" stroke-width="6.5"/>')
    o.append("</g>" + river_label_svg + "</g>")

    o.append('<g class="labels-deco">' + "".join(deco_svg) +
             f'<text class="t-district" font-size="{arc_size}" letter-spacing="{arc_sp}" style="fill-opacity:1">'
             f'<textPath href="#arc-{name}" startOffset="50%" text-anchor="middle">{esc(arc_txt)}</textPath></text></g>')

    o.append('<g class="towns">' + "".join(dots_svg) + "</g>")
    o.append('<g class="town-labels">' + "".join(labels_svg) + "</g>")

    o.append(f'<g class="pin-eschau" transform="translate({ex:.1f} {ey:.1f})">'
             f'<circle class="pulse" r="{pin_r}" fill="none" stroke="{C["green"]}" stroke-opacity="0.28" stroke-width="2.5"/>'
             f'<circle class="halo" r="34" fill="{C["green"]}" fill-opacity="0.13"/>'
             f'<circle class="ring" r="19" fill="#fff"/>'
             f'<circle class="dot" r="12" fill="{C["green"]}"/></g>')
    o.append(f'<g class="label-eschau"><text class="t-eschau" x="{e_bx:.1f}" y="{e_base:.1f}" text-anchor="{e_anchor}" '
             f'font-size="{e_size}" font-weight="400" fill="{C["text"]}">Eschau</text>'
             f'<text class="t-caption" x="{e_bx + (3 if e_anchor == "start" else -3):.1f}" y="{c_base:.1f}" text-anchor="{e_anchor}" '
             f'font-size="{cap_size}" font-weight="500" letter-spacing="0.4" fill="{C["green"]}">{esc(c_txt)}</text></g>')

    # scale bar (10 km) + north arrow
    tick = 12
    ui = [f'<g class="scale" stroke="{C["grey"]}" stroke-width="2" stroke-linecap="round" fill="none">',
          f'<path d="M{sb_x:.1f} {sb_y:.1f} H{sb_x + km10:.1f} M{sb_x:.1f} {sb_y - tick} V{sb_y} '
          f'M{sb_x + km10 / 2:.1f} {sb_y - tick * 0.6:.1f} V{sb_y} M{sb_x + km10:.1f} {sb_y - tick} V{sb_y}"/>',
          '</g>',
          f'<text class="t-ui" x="{sb_x:.1f}" y="{sb_y + 34:.1f}" font-size="22" text-anchor="middle">0</text>',
          f'<text class="t-ui" x="{sb_x + km10 / 2:.1f}" y="{sb_y + 34:.1f}" font-size="22" text-anchor="middle">5</text>',
          f'<text class="t-ui" x="{sb_x + km10:.1f}" y="{sb_y + 34:.1f}" font-size="22" text-anchor="start" dx="-6">10 km</text>']
    nx, ny = sb_x, sb_y - 72
    ui += [f'<g class="north" stroke="{C["grey"]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none">',
           f'<path d="M{nx} {ny + 26} V{ny - 34} M{nx - 9} {ny - 20} L{nx} {ny - 34} L{nx + 9} {ny - 20}"/></g>',
           f'<text class="t-ui" x="{nx + 18}" y="{ny - 20}" font-size="22" font-weight="500">N</text>']
    ui.append(f'<text class="t-ui" x="{ax:.1f}" y="{ay:.1f}" font-size="22" text-anchor="end">{esc(attr)}</text>')
    o.append('<g class="map-ui">' + "".join(ui) + "</g>")
    o.append("</svg>")
    shown = sorted(placed)
    print(f"  [{name}] town labels: {len(shown)} + Eschau, unlabeled dots: {dropped}, "
          f"arc at {arc_mid}°, river label: {bool(bestw)}")
    return "\n".join(o), shown, dropped


# --------------------------------------------------------------------------- raster
def rasterise(svg_path, stem, W, H, sizes, jpg=False):
    os.makedirs(TMP_DIR, exist_ok=True)
    png = os.path.join(TMP_DIR, stem + "@2x.png")
    subprocess.run(["python3", os.path.join(HERE, "render.py"), svg_path, png, str(W), str(H), "2"], check=True)
    im = Image.open(png).convert("RGB")
    for w in sizes:
        h = round(H * w / W)
        r = im.resize((w, h), Image.LANCZOS)
        out = os.path.join(OUT_DIR, f"{stem}-{w}.webp")
        r.save(out, "WEBP", quality=88, method=6)
        print("  wrote", os.path.relpath(out, ROOT), f"{w}x{h}", f"{os.path.getsize(out) // 1024} KB")
        if jpg and w == max(sizes):
            outj = os.path.join(OUT_DIR, f"{stem}-{w}.jpg")
            r.save(outj, "JPEG", quality=88, optimize=True, progressive=True)
            print("  wrote", os.path.relpath(outj, ROOT), f"{os.path.getsize(outj) // 1024} KB")


def main():
    raw = geodata.fetch_all()
    company = raw["company"]
    center = {"name": "Eschau", "lat": round(company["lat"], 5), "lon": round(company["lon"], 5)}
    geo = dict(raw, center=center)

    os.makedirs(OUT_DIR, exist_ok=True)
    only_svg = "--svg-only" in sys.argv
    for name, cfg in VARIANTS.items():
        svg, shown, dropped = build_variant(name, cfg, geo)
        stem = "einzugsgebiet" if name == "landscape" else "einzugsgebiet-portrait"
        svg_path = os.path.join(OUT_DIR, stem + ".svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg)
        print("  wrote", os.path.relpath(svg_path, ROOT), f"{os.path.getsize(svg_path) // 1024} KB")
        if only_svg:
            continue
        if name == "landscape":
            rasterise(svg_path, stem, cfg["W"], cfg["H"], [2400, 1400, 800], jpg=True)
        else:
            rasterise(svg_path, stem, cfg["W"], cfg["H"], [1500, 900])

    towns = []
    for t in raw["towns"]:
        if t["name"] == "Eschau":
            continue
        towns.append({"name": t["name"], "lat": round(t["lat"], 5), "lon": round(t["lon"], 5),
                      "distance_km": round(haversine_km(center["lat"], center["lon"], t["lat"], t["lon"]), 1)})
    towns.sort(key=lambda t: t["distance_km"])
    os.makedirs(os.path.dirname(DATA_JSON), exist_ok=True)
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump({"center": center, "radius_km": RADIUS_KM, "towns": towns,
                   "attribution": "Kartendaten © OpenStreetMap-Mitwirkende (ODbL)"}, f, ensure_ascii=False, indent=2)
    print("  wrote", os.path.relpath(DATA_JSON, ROOT), f"({len(towns)} towns)")


if __name__ == "__main__":
    main()
