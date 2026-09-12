import asyncio, json, os
from playwright.async_api import async_playwright
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_research/ref/sub"
os.makedirs(OUT, exist_ok=True)
PAGES = {"pool": "/de/corners/pool", "marchen": "/de/marchen", "zimmer": "/de/zimmer-und-suite", "kontakte": "/de/kontakte", "kingsuite": "/de/zimmer/king-suite"}
async def one(b, slug, path):
    ctx = await b.new_context(viewport={"width": 1920, "height": 1080})
    page = await ctx.new_page()
    await page.goto("https://www.relaisrossar.it" + path, wait_until="networkidle", timeout=90000)
    await page.wait_for_timeout(1500)
    try:
        l = page.locator("text=allow all")
        if await l.count(): await l.first.click(timeout=2000)
    except Exception: pass
    await page.evaluate("""() => { document.querySelectorAll('[class*=booking]').forEach(e=>{ const r=e.getBoundingClientRect(); if(r.top<300 && r.width>500) e.style.display='none'; }); }""")
    await page.wait_for_timeout(2500)
    await page.screenshot(path=f"{OUT}/{slug}_00.png")
    H = await page.evaluate("document.documentElement.scrollHeight")
    y = 0; i = 1
    while y + 1080 < H + 1080 and i < 16:
        for _ in range(9):
            await page.mouse.wheel(0, 100); await page.wait_for_timeout(60)
        y += 900
        await page.wait_for_timeout(1400)
        await page.screenshot(path=f"{OUT}/{slug}_{i:02d}.png"); i += 1
        H = await page.evaluate("document.documentElement.scrollHeight")
    html = await page.evaluate("document.querySelector('main') ? document.querySelector('main').outerHTML : ''")
    import re
    html = re.sub(r'<svg.*?</svg>', '<svg/>', html, flags=re.S)
    html = re.sub(r'\s(srcset|sizes)="[^"]*"', '', html)
    html = re.sub(r'<div style="position:relative;display:inline-block;"[^>]*>', '', html)
    open(f"{OUT}/{slug}.html", "w").write(html)
    print(slug, H, i)
    await ctx.close()
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        await asyncio.gather(*[one(b, s, pth) for s, pth in PAGES.items()])
        await b.close()
asyncio.run(main())
