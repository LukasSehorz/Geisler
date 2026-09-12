"""Rasterise an SVG with Playwright/Chromium using the site's self-hosted fonts.

Run with the system python3 (playwright installed there):
    python3 render.py <in.svg> <out.png> <width> <height> [scale]
"""
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
FONTS_CSS = ROOT / "site" / "assets" / "fonts" / "fonts.css"

# faces the map actually uses (must all load, otherwise we abort)
FACES = [
    '400 32px "Hanken Grotesk"', '500 32px "Hanken Grotesk"',
    'italic 400 64px "Newsreader"', 'italic 300 64px "Newsreader"',
]


def main():
    svg_path = pathlib.Path(sys.argv[1]).resolve()
    out_abs = pathlib.Path(sys.argv[2]).resolve()
    w, h = int(sys.argv[3]), int(sys.argv[4])
    scale = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
    svg = svg_path.read_text(encoding="utf-8")
    # the SVG's @font-face urls are relative to site/assets/img/map/ -> make them absolute here
    # (its src lists fall back between variable and per-weight file names)
    fonts_uri = FONTS_CSS.parent.as_uri()
    svg, n = re.subn(r"url\('\.\./\.\./fonts/", f"url('{fonts_uri}/", svg)
    if n == 0:
        print("  ! no relative font urls found in the SVG")
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{FONTS_CSS.as_uri()}">
<style>html,body{{margin:0;padding:0;background:#f7f6f5;overflow:hidden}}
svg{{display:block;width:{w}px;height:{h}px}}</style></head><body>{svg}</body></html>"""
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_abs.parent / (out_abs.stem.replace("@", "_") + "_render.html")
    tmp.write_text(html, encoding="utf-8")
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
            page.on("requestfailed", lambda r: print("  ! request failed:", r.url, r.failure))
            page.on("console", lambda m: print("  console:", m.type, m.text) if m.type in ("error", "warning") else None)
            page.goto(tmp.as_uri())
            result = page.evaluate(
                """async (faces) => {
                    const out = {ok: [], failed: []};
                    for (const f of faces) {
                        try {
                            const r = await document.fonts.load(f);
                            (r.length ? out.ok : out.failed).push(f + (r.length ? '' : ' (no match)'));
                        } catch (e) { out.failed.push(f + ' -> ' + e); }
                    }
                    await document.fonts.ready;
                    out.loaded = [...document.fonts].filter(x => x.status === 'loaded')
                        .map(x => `${x.family} ${x.style} ${x.weight}`);
                    out.errored = [...document.fonts].filter(x => x.status === 'error')
                        .map(x => `${x.family} ${x.style} ${x.weight}`);
                    return out;
                }""", FACES)
            print("  fonts loaded:", ", ".join(sorted(set(result["loaded"]))))
            if result["errored"]:
                print("  (ignored: faces that failed but have a loaded fallback:", result["errored"], ")")
            needed = {("Hanken Grotesk", "normal"), ("Newsreader", "italic")}
            have = {(fam, st) for fam, st in needed
                    if any(l.startswith(f"{fam} {st} ") for l in result["loaded"])}
            needed_ok = needed <= have
            if not needed_ok:
                print("  ! required fonts did not load:", needed - have, result["failed"])
                b.close()
                sys.exit(2)
            page.wait_for_timeout(150)
            page.screenshot(path=str(out_abs), clip={"x": 0, "y": 0, "width": w, "height": h})
            b.close()
    finally:
        if tmp.exists():
            tmp.unlink()


if __name__ == "__main__":
    main()
