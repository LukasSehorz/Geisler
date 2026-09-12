import asyncio, json, os, re, urllib.request, hashlib
from playwright.async_api import async_playwright
BASE = "https://www.gartengestaltung-geissler.de"
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_research/geissler"
PAGES = ["/", "/dienstleistungen/", "/smartgarden/", "/smartgarden/m%C3%A4hroboter/", "/smartgarden/bew%C3%A4sserung/", "/smartgarden/lichtdesign/",
 "/galerie/", "/galerie/bepflanzungen/", "/galerie/belagsarbeiten/", "/galerie/teichanlagen-wasserelemente/", "/galerie/dachbegr%C3%BCnung-wasserspeicher/",
 "/galerie/hangsicherung-mauerbau/", "/galerie/sichtschutz-zaun/", "/galerie/treppenanlagen/", "/unsere-g%C3%A4rten/", "/kontakt/", "/kontakt/ansprechpartner/",
 "/stellenangebote/", "/about/"]
def full(u):
    # jimdo transf -> original
    u = re.sub(r"/transf/[^/]+/", "/transf/none/", u)
    return u
async def main():
    os.makedirs(OUT + "/img", exist_ok=True)
    manifest = {}
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width": 1440, "height": 900})
        for path in PAGES:
            slug = re.sub(r"[^a-z0-9]+", "_", urllib.parse.unquote(path).lower().replace("ä","ae").replace("ü","ue")).strip("_") or "home"
            try:
                await page.goto(BASE + path, wait_until="networkidle", timeout=60000)
            except Exception as e:
                print("ERR", path, e); continue
            for t in ["Alle akzeptieren", "Akzeptieren", "OK"]:
                try:
                    l = page.get_by_role("button", name=t)
                    if await l.count(): await l.first.click(timeout=1500); break
                except Exception: pass
            # scroll to trigger lazy
            h = await page.evaluate("document.body.scrollHeight")
            for y in range(0, h, 600):
                await page.evaluate(f"window.scrollTo(0,{y})"); await page.wait_for_timeout(150)
            await page.wait_for_timeout(800)
            text = await page.evaluate("document.body.innerText")
            open(f"{OUT}/{slug}.txt", "w").write(text)
            await page.screenshot(path=f"{OUT}/shot_{slug}.png", full_page=True)
            urls = await page.evaluate("""() => {
              const s = new Set();
              document.querySelectorAll('img').forEach(i => { if (i.currentSrc) s.add(i.currentSrc); if (i.src) s.add(i.src); const d=i.getAttribute('data-src'); if(d) s.add(d); });
              document.querySelectorAll('a[href]').forEach(a => { if (/\\.(jpe?g|png|webp)/i.test(a.href) || a.href.includes('image.jimcdn')) s.add(a.href); });
              document.querySelectorAll('*').forEach(e => { const bg = getComputedStyle(e).backgroundImage; const m = bg && bg.match(/url\\(["']?([^"')]+)/); if (m) s.add(m[1]); });
              return Array.from(s);
            }""")
            imgs = sorted({full(u) for u in urls if "jimcdn" in u and ("image" in u or "backgroundarea" in u)})
            manifest[slug] = imgs
            print(slug, len(imgs))
        await b.close()
    json.dump(manifest, open(f"{OUT}/manifest.json", "w"), indent=1)
    seen = {}
    for slug, imgs in manifest.items():
        for i, u in enumerate(imgs):
            if u in seen: continue
            m = re.search(r"/image/(i[0-9a-f]+)/|/backgroundarea/(i[0-9a-f]+)/|/(i[0-9a-f]{16})", u)
            iid = next((g for g in (m.groups() if m else []) if g), hashlib.md5(u.encode()).hexdigest()[:10])
            dest = f"{OUT}/img/{slug}__{iid}.jpg"
            try:
                data = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read()
                open(dest, "wb").write(data); seen[u] = dest
            except Exception as e:
                print("dl fail", u, e)
    json.dump(seen, open(f"{OUT}/downloaded.json", "w"), indent=1)
    print("downloaded", len(seen))
import urllib.parse
asyncio.run(main())
