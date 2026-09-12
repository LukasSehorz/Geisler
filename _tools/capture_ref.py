import asyncio, json, os, sys
from playwright.async_api import async_playwright
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_research/ref"
URL = "https://www.relaisrossar.it/de"
JS = r"""
() => {
  const out = [];
  const sel = 'h1,h2,h3,h4,h5,h6,p,a,button,span,li,img,video,header,nav,section,footer,div[class]';
  const els = Array.from(document.querySelectorAll(sel));
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const cs = getComputedStyle(el);
    const txt = (el.childNodes.length && Array.from(el.childNodes).filter(n=>n.nodeType===3).map(n=>n.textContent.trim()).join(' ').trim()) || '';
    if (['DIV','SECTION','SPAN','LI'].includes(el.tagName) && !txt && !['SECTION'].includes(el.tagName) && r.height < 150) continue;
    out.push({tag: el.tagName, cls: el.className && el.className.toString().slice(0,120), id: el.id,
      text: txt.slice(0,120), src: el.currentSrc || el.src || '',
      x: Math.round(r.left), y: Math.round(r.top + window.scrollY), w: Math.round(r.width), h: Math.round(r.height),
      ff: cs.fontFamily, fs: cs.fontSize, fw: cs.fontWeight, lh: cs.lineHeight, ls: cs.letterSpacing, tt: cs.textTransform,
      color: cs.color, bg: cs.backgroundColor, bgi: cs.backgroundImage.slice(0,200), ta: cs.textAlign,
      pos: cs.position, z: cs.zIndex, trans: cs.transition.slice(0,120), anim: cs.animationName, of: cs.objectFit, op: cs.opacity, tf: cs.transform});
  }
  return out;
}
"""
async def run(width, height, tag):
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": width, "height": height}, device_scale_factor=1, locale="de-DE")
        page = await ctx.new_page()
        css_urls = []
        async def on_resp(resp):
            u = resp.url
            ct = resp.headers.get("content-type", "")
            if "css" in ct or u.split("?")[0].endswith(".css") or u.split("?")[0].endswith(".js") or "font" in ct or u.split("?")[0].endswith((".woff2",".woff",".ttf",".otf")):
                try:
                    body = await resp.body()
                    name = u.split("?")[0].rstrip("/").split("/")[-1] or "index"
                    d = os.path.join(OUT, "assets")
                    os.makedirs(d, exist_ok=True)
                    open(os.path.join(d, name), "wb").write(body)
                    css_urls.append(u)
                except Exception:
                    pass
        page.on("response", on_resp)
        await page.goto(URL, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(2500)
        # dismiss cookie banner
        for t in ["Alle Cookies zulassen", "Consenti tutti i cookie", "Accept all", "Alle akzeptieren", "Allow all cookies", "Accetta"]:
            try:
                loc = page.get_by_text(t, exact=False)
                if await loc.count():
                    await loc.first.click(timeout=2000); break
            except Exception:
                pass
        await page.wait_for_timeout(1500)
        if tag == "1920":
            open(os.path.join(OUT, "page.html"), "w").write(await page.content())
        await page.screenshot(path=os.path.join(OUT, f"{tag}_00_hero.png"))
        total = await page.evaluate("document.documentElement.scrollHeight")
        y = 0; i = 1
        step = int(height * 0.5)
        while y < total:
            y += step
            await page.mouse.wheel(0, step)
            await page.wait_for_timeout(900)
            await page.screenshot(path=os.path.join(OUT, f"{tag}_{i:02d}_y{y}.png"))
            i += 1
            total = await page.evaluate("document.documentElement.scrollHeight")
        await page.wait_for_timeout(1000)
        await page.evaluate("window.scrollTo(0,0)")
        await page.wait_for_timeout(1000)
        data = await page.evaluate(JS)
        json.dump(data, open(os.path.join(OUT, f"styles_{tag}.json"), "w"), indent=1, ensure_ascii=False)
        await page.screenshot(path=os.path.join(OUT, f"{tag}_full.png"), full_page=True)
        fonts = await page.evaluate("Array.from(document.fonts).map(f=>[f.family,f.weight,f.style,f.status])")
        json.dump({"fonts": fonts, "assets": css_urls, "scrollHeight": total}, open(os.path.join(OUT, f"meta_{tag}.json"), "w"), indent=1)
        print(tag, "done, height", total, "screens", i)
        await b.close()
async def main():
    await asyncio.gather(run(1920, 1080, "1920"), run(1440, 900, "1440"), run(390, 844, "m390"))
asyncio.run(main())
