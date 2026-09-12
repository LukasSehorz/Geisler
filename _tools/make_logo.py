#!/usr/bin/env python3
"""Vector-clean logo extraction: every pixel = alpha * brand ink over white."""
from PIL import Image
import numpy as np
B = "site/assets/img/brand/"
SRC = "_research/geissler/img/home__ida40d4bec15e56b5.jpg"
INKS = {"green": (1, 122, 51), "gray": (112, 113, 115), "sage": (152, 185, 140)}
def extract(box=None):
    im = Image.open(SRC).convert("RGB")
    if box: im = im.crop(box)
    p = np.array(im).astype(float)
    d = 255.0 - p                                   # = a * (255 - ink)
    best_a = np.zeros(p.shape[:2]); best_err = np.full(p.shape[:2], 1e9); best_k = np.zeros(p.shape[:2], int)
    for k, ink in enumerate(INKS.values()):
        di = 255.0 - np.array(ink, float)
        a = np.clip((d * di).sum(-1) / (di * di).sum(), 0, 1)
        err = ((d - a[..., None] * di) ** 2).sum(-1)
        m = err < best_err
        best_err[m], best_a[m], best_k[m] = err[m], a[m], k
    best_a[best_a < 0.035] = 0
    return best_a, best_k, im.size
def render(alpha, kind, colors):
    h, w = alpha.shape
    out = np.zeros((h, w, 4), np.uint8)
    for k, col in enumerate(colors):
        m = kind == k
        out[m, :3] = col
    out[..., 3] = np.round(np.clip(alpha, 0, 1) * 255)
    img = Image.fromarray(out, "RGBA")
    return img.crop(img.getbbox())
alpha, kind, _ = extract()
inks = list(INKS.values())
color = render(alpha, kind, inks)
light = render(alpha, kind, [(255, 255, 255), (232, 233, 228), (196, 219, 184)])
white = render(alpha, kind, [(255, 255, 255)] * 3)
for name, img in [("logo-color", color), ("logo-light", light), ("logo-white", white)]:
    img.save(B + f"{name}.png", optimize=True)
    t = img.copy(); t.thumbnail((840, 840)); t.save(B + f"{name}-840.png", optimize=True)
print("logo", color.size, "840:", Image.open(B + "logo-color-840.png").size)
# favicon: tree only
a2, k2, _ = extract((540, 25, 1035, 470))
tree = render(a2, k2, inks)
for size in (32, 192, 512):
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    tt = tree.copy(); tt.thumbnail((int(size * 0.8), int(size * 0.8)), Image.LANCZOS)
    canvas.alpha_composite(tt, ((size - tt.width) // 2, (size - tt.height) // 2))
    canvas.save(B + f"favicon-{size}.png", optimize=True)
S = "/private/tmp/claude-501/-Users-jannikvomhofe-Desktop-Webdesign-Galabau-Geissler/73b50ba3-7852-46db-a53f-a831f9c48fdd/scratchpad/"
x = Image.open(B + "logo-light-840.png"); bg = Image.new("RGBA", x.size, (46, 58, 42, 255)); bg.alpha_composite(x)
y = Image.open(B + "logo-color-840.png"); bg2 = Image.new("RGBA", y.size, (255, 255, 255, 255)); bg2.alpha_composite(y)
f = Image.open(B + "favicon-192.png").convert("RGB")
sheet = Image.new("RGB", (x.width * 2 + 212, x.height), (255, 255, 255))
sheet.paste(bg.convert("RGB"), (0, 0)); sheet.paste(bg2.convert("RGB"), (x.width, 0)); sheet.paste(f, (x.width * 2 + 10, 10))
sheet.save(S + "brand_test2.jpg")
