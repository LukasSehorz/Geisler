#!/usr/bin/env python3
"""Technical QA over every built page.

Checks per page and viewport: HTTP status of all internal links/assets, console + page errors,
broken images (naturalWidth 0 after lazy-load scroll), horizontal overflow, missing alt,
duplicate ids, empty links. Writes _review/qa.md and prints a summary.
usage: python3 _tools/qa.py [page-filter ...]
"""
import asyncio
import json
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BASE = "http://localhost:8765/"
VIEWPORTS = [(1920, 1080), (1440, 900), (1024, 768), (390, 844)]


def pages():
    out = []
    for p in sorted(SITE.rglob("*.html")):
        rel = p.relative_to(SITE).as_posix()
        if rel.startswith(("assets/",)):
            continue
        out.append(rel)
    flt = sys.argv[1:]
    return [p for p in out if not flt or any(f in p for f in flt)]


def status(url, cache={}):
    if url in cache:
        return cache[url]
    try:
        req = urllib.request.Request(url, method="GET")
        code = urllib.request.urlopen(req, timeout=15).status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # noqa
        code = str(e)[:60]
    cache[url] = code
    return code


JS = r"""
async () => {
  const H = document.documentElement.scrollHeight;
  for (let y = 0; y < H; y += Math.round(innerHeight * 0.8)) {
    if (window.__lenis) window.__lenis.scrollTo(y, { immediate: true }); else window.scrollTo(0, y);
    await new Promise(r => setTimeout(r, 120));
  }
  await new Promise(r => setTimeout(r, 800));
  const imgs = [...document.images];
  const broken = imgs.filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).map(i => i.currentSrc || i.src);
  const noAlt = imgs.filter(i => !i.hasAttribute('alt')).map(i => i.src);
  const ids = {}; document.querySelectorAll('[id]').forEach(e => ids[e.id] = (ids[e.id] || 0) + 1);
  const dupIds = Object.entries(ids).filter(([k, v]) => v > 1).map(([k]) => k);
  const emptyLinks = [...document.querySelectorAll('a')].filter(a => !a.textContent.trim() && !a.getAttribute('aria-label') && !a.querySelector('img[alt]:not([alt=""])')).map(a => a.getAttribute('href'));
  const links = [...document.querySelectorAll('a[href]')].map(a => a.href);
  const assets = [...document.querySelectorAll('img[src], source[src], video[src], video[poster], link[href], script[src]')].map(e => e.src || e.href || e.poster).filter(Boolean);
  const overflow = document.documentElement.scrollWidth - innerWidth;
  const wide = overflow > 1 ? [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 5).map(e => e.tagName.toLowerCase() + '.' + (e.className && e.className.baseVal === undefined ? String(e.className).split(' ').join('.') : '')) : [];
  return { broken, noAlt, dupIds, emptyLinks, links, assets, overflow, wide, title: document.title };
}
"""


async def main():
    report = []
    totals = {"errors": 0, "broken_links": 0, "broken_images": 0, "overflow": 0}
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for rel in pages():
            url = BASE + rel
            page_notes = []
            for w, h in VIEWPORTS:
                ctx = await browser.new_context(viewport={"width": w, "height": h})
                pg = await ctx.new_page()
                errors = []
                pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                pg.on("pageerror", lambda e: errors.append(f"PAGEERROR {e}"))
                try:
                    await pg.goto(url, wait_until="load", timeout=60000)
                    await pg.wait_for_timeout(1500)
                    r = await pg.evaluate(JS)
                except Exception as e:  # noqa
                    page_notes.append(f"- {w}px: LOAD FAILED {e}")
                    await ctx.close()
                    continue
                if errors:
                    totals["errors"] += len(errors)
                    page_notes.append(f"- {w}px console errors: " + "; ".join(errors[:6]))
                if r["broken"]:
                    totals["broken_images"] += len(r["broken"])
                    page_notes.append(f"- {w}px broken images: " + ", ".join(r["broken"][:6]))
                if r["overflow"] > 1:
                    totals["overflow"] += 1
                    page_notes.append(f"- {w}px horizontal overflow {r['overflow']}px, e.g. {r['wide']}")
                if w == 1920:
                    if r["noAlt"]:
                        page_notes.append(f"- images without alt: {len(r['noAlt'])}")
                    if r["dupIds"]:
                        page_notes.append(f"- duplicate ids: {r['dupIds']}")
                    if r["emptyLinks"]:
                        page_notes.append(f"- links without accessible name: {r['emptyLinks'][:6]}")
                    for link in sorted(set(r["links"] + r["assets"])):
                        u = urlparse(link)
                        if u.netloc != urlparse(BASE).netloc:
                            continue
                        code = status(link.split("#")[0])
                        if code != 200:
                            totals["broken_links"] += 1
                            page_notes.append(f"- broken {code}: {link}")
                await ctx.close()
            report.append(f"## {rel}\n" + ("\n".join(page_notes) if page_notes else "- OK"))
            print(rel, "OK" if not page_notes else f"{len(page_notes)} notes")
        await browser.close()
    out = ROOT / "_review" / "qa.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("# Technical QA\n\n" + json.dumps(totals) + "\n\n" + "\n\n".join(report) + "\n", encoding="utf-8")
    print("TOTALS", totals, "->", out)


asyncio.run(main())
