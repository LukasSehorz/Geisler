#!/usr/bin/env python3
"""Static site generator for Gartengestaltung Geißler.

Run with the project venv:  _tools/.venv/bin/python _tools/build.py
Templates: src/templates (Jinja2) · Data: _data/*.json · Output: site/
"""
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
OUT = ROOT / "site"
DATA = ROOT / "_data"
IMG_OUT = OUT / "assets" / "img" / "r"
IMG_OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "gen": ROOT / "_gen",
    "gal": ROOT / "_research" / "geissler" / "img",
    "site": OUT / "assets" / "img",
}


def load(name, default=None):
    p = DATA / name
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- images
_img_cache = {}


def _resolve(src):
    kind, _, rest = src.partition(":")
    base = SOURCES.get(kind)
    if base is None:
        raise ValueError(f"unknown image source {src}")
    path = base / rest
    if not path.exists() and kind == "gen" and not path.suffix:
        path = base / f"{rest}.png"
    if not path.exists():
        raise FileNotFoundError(src)
    return path


def _crop(im, ratio, focus):
    if not ratio:
        return im
    w, h = im.size
    rw, rh = [float(x) for x in str(ratio).replace(":", "/").split("/")]
    target = rw / rh
    fx, fy = focus
    if w / h > target:  # too wide -> crop width
        nw = round(h * target)
        x0 = min(max(round(fx * w - nw / 2), 0), w - nw)
        return im.crop((x0, 0, x0 + nw, h))
    nh = round(w / target)
    y0 = min(max(round(fy * h - nh / 2), 0), h - nh)
    return im.crop((0, y0, w, y0 + nh))


def image_set(src, ratio=None, focus=(0.5, 0.5), widths=(640, 1024, 1600, 2200), quality=80):
    """Return (list of (url_rel_to_site, width), (w, h)) for a cropped responsive set."""
    path = _resolve(src)
    key = f"{path}|{path.stat().st_mtime}|{ratio}|{focus}|{widths}|{quality}"
    if key in _img_cache:
        return _img_cache[key]
    digest = hashlib.md5(key.encode()).hexdigest()[:10]
    stem = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")[:40]
    im = None
    out = []
    crop_size = None
    for w in widths:
        fname = f"{stem}-{digest}-{w}.webp"
        dest = IMG_OUT / fname
        if dest.exists() and crop_size is not None:
            out.append((f"assets/img/r/{fname}", w))
            continue
        if im is None:
            im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
            im = _crop(im, ratio, focus)
            crop_size = im.size
        if w > crop_size[0] * 1.02 and out:
            break
        tw = min(w, crop_size[0])
        if not dest.exists():
            th = round(crop_size[1] * tw / crop_size[0])
            im.resize((tw, th), Image.LANCZOS).save(dest, "WEBP", quality=quality, method=6)
        out.append((f"assets/img/r/{fname}", tw))
        if tw < w:
            break
    if crop_size is None:  # all cached - need size
        im = ImageOps.exif_transpose(Image.open(path))
        crop_size = _crop(im, ratio, focus).size
    res = (out, crop_size)
    _img_cache[key] = res
    return res


# --------------------------------------------------------------------------- rendering helpers
class Page:
    def __init__(self, out, template, **ctx):
        self.out = out
        self.template = template
        self.ctx = ctx

    @property
    def root(self):
        depth = self.out.count("/")
        return "../" * depth


def make_env(page):
    env = Environment(
        loader=FileSystemLoader(str(SRC / "templates")),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    root = page.root

    def url(p=""):
        if p.startswith(("http", "mailto:", "tel:", "#")):
            return p
        return root + p

    def asset(p):
        return root + "assets/" + p

    def pic(src, alt="", ratio=None, focus=(0.5, 0.5), sizes="100vw", cls="", loading="lazy",
            widths=(640, 1024, 1600, 2200), priority=False, attrs="", defer=False):
        if isinstance(focus, dict):
            focus = (focus.get("x", 0.5), focus.get("y", 0.5))
        variants, (w, h) = image_set(src, ratio, tuple(focus), tuple(widths))
        srcset = ", ".join(f"{root}{u} {vw}w" for u, vw in variants)
        default = variants[min(len(variants) - 1, 1)][0]
        extra = ' fetchpriority="high"' if priority else ""
        load_attr = "eager" if priority else loading
        c = f' class="{cls}"' if cls else ""
        if defer:  # loaded by JS on first use (e.g. hidden mega menu images)
            blank = "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw=="
            return Markup(
                f'<img{c} src="{blank}" data-defer-src="{root}{default}" data-defer-srcset="{srcset}" sizes="{sizes}" '
                f'width="{w}" height="{h}" alt="{Markup.escape(alt)}" decoding="async" {attrs}>'
            )
        return Markup(
            f'<img{c} src="{root}{default}" srcset="{srcset}" sizes="{sizes}" width="{w}" height="{h}" '
            f'alt="{Markup.escape(alt)}" loading="{load_attr}" decoding="async"{extra} {attrs}>'
        )

    def source(src, media_query, ratio=None, focus=(0.5, 0.5), widths=(600, 900, 1200), sizes="100vw"):
        if isinstance(focus, dict):
            focus = (focus.get("x", 0.5), focus.get("y", 0.5))
        variants, _ = image_set(src, ratio, tuple(focus), tuple(widths))
        srcset = ", ".join(f"{root}{u} {vw}w" for u, vw in variants)
        return Markup(f'<source media="{media_query}" srcset="{srcset}" sizes="{sizes}">')

    def current(p):
        return "is-current" if page.out == p or (p != "index.html" and page.out.startswith(p.replace(".html", "/"))) else ""

    env.globals.update(url=url, asset=asset, pic=pic, source=source, current=current, page=page, root=root)
    env.filters["nbsp"] = lambda s: Markup(str(s).replace(" & ", "&nbsp;&amp; "))
    return env


def render(page, common):
    env = make_env(page)
    tpl = env.get_template(page.template)
    html = tpl.render(**common, **page.ctx)
    dest = OUT / page.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return dest


# --------------------------------------------------------------------------- site definition
def build():
    content = load("content.json", {})
    gallery = load("gallery.json", {"images": [], "recommendations": {}})
    region = load("einzugsgebiet.json", {})
    media = json.loads((SRC / "media.json").read_text(encoding="utf-8"))

    services = content.get("services", [])
    smart = content.get("smartgarden", {})
    smart_pages = smart.get("pages", [])
    for s in services:
        s["url"] = f"dienstleistungen/{s['slug']}.html"
        s["media"] = media["services"].get(s["slug"], {})
    for s in smart_pages:
        s["url"] = f"smart-garden/{s['slug']}.html"
        s["media"] = media["smart"].get(s["slug"], {})

    common = dict(
        c=content, services=services, smart=smart, smart_pages=smart_pages,
        media=media, gallery=gallery, region=region,
        company=dict(
            name="Gartengestaltung Geißler", legal="Gartengestaltung Geißler OHG",
            owners="Inh. Opolka & Weis", street="Elsavastraße 3", zip="63863", city="Eschau",
            phone="09374 / 2124", phone_href="tel:+4993742124", fax="09374 / 7309",
            email="info@gartengestaltung-geissler.de",
            maps="https://www.google.com/maps/search/?api=1&query=Elsavastra%C3%9Fe+3%2C+63863+Eschau",
        ),
        year=2026,
    )

    pages = [Page("index.html", "pages/home.html")]
    templates = SRC / "templates" / "pages"
    if (templates / "services.html").exists():
        pages.append(Page("dienstleistungen.html", "pages/services.html"))
    if (templates / "service.html").exists():
        for i, s in enumerate(services):
            nxt = services[(i + 1) % len(services)] if services else None
            pages.append(Page(s["url"], "pages/service.html", s=s, next_s=nxt, kind="service"))
    if (templates / "smartgarden.html").exists():
        pages.append(Page("smart-garden.html", "pages/smartgarden.html"))
    if (templates / "service.html").exists():
        for i, s in enumerate(smart_pages):
            nxt = smart_pages[(i + 1) % len(smart_pages)] if smart_pages else None
            smart_tpl = "pages/smart.html" if (templates / "smart.html").exists() else "pages/service.html"
            pages.append(Page(s["url"], smart_tpl, s=s, next_s=nxt, kind="smart", smart_all=smart_pages))
    for out, tpl in [("galerie.html", "gallery.html"), ("kontakt.html", "contact.html"),
                     ("ueber-uns.html", "about.html"), ("karriere.html", "career.html"),
                     ("impressum.html", "legal.html"), ("datenschutz.html", "legal.html")]:
        if (templates / tpl).exists():
            pages.append(Page(out, f"pages/{tpl}", legal_kind=out.replace(".html", "")))

    only = sys.argv[1:] if len(sys.argv) > 1 else None
    failed = []
    for p in pages:
        if only and not any(o in p.out for o in only):
            continue
        try:
            render(p, common)
            print("built", p.out)
        except Exception as exc:  # keep building the other pages
            failed.append(p.out)
            print("FAILED", p.out, "->", type(exc).__name__, exc)

    if not only:
        base_url = "https://www.gartengestaltung-geissler.de/"
        urls = "\n".join(
            f"  <url><loc>{base_url}{'' if p.out == 'index.html' else p.out}</loc></url>"
            for p in pages
        )
        (OUT / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "\n</urlset>\n",
            encoding="utf-8",
        )
        (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base_url}sitemap.xml\n", encoding="utf-8")
        print("wrote sitemap.xml, robots.txt")


if __name__ == "__main__":
    build()
