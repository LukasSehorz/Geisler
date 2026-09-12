import asyncio, json, os
from playwright.async_api import async_playwright
OUT = "/Users/jannikvomhofe/Desktop/Webdesign/Galabau Geissler/_research/ref/clean"
os.makedirs(OUT, exist_ok=True)
async def prep(page):
    await page.goto("https://www.relaisrossar.it/de", wait_until="networkidle", timeout=90000)
    await page.wait_for_timeout(2000)
    for sel in ["text=allow all", "text=Consenti tutti"]:
        try:
            l = page.locator(sel)
            if await l.count(): await l.first.click(timeout=2000); break
        except Exception: pass
    await page.wait_for_timeout(800)
    # close booking widget: find close button near top right
    await page.evaluate("""() => { document.querySelectorAll('[class*=booking],[class*=Booking]').forEach(e=>{ const r=e.getBoundingClientRect(); if(r.top<300 && r.width>500) e.style.display='none'; }); }""")
    await page.wait_for_timeout(500)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # 1) video recording of slow scroll
        ctx = await b.new_context(viewport={"width": 1920, "height": 1080}, record_video_dir=OUT+"/video", record_video_size={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await prep(page)
        await page.wait_for_timeout(3000)
        total = await page.evaluate("document.documentElement.scrollHeight")
        # hover over about section to show CTA cursor
        y = 0
        while y < 7600:
            await page.mouse.move(960, 600)
            await page.mouse.wheel(0, 60)
            await page.wait_for_timeout(70)
            y += 60
        await page.wait_for_timeout(1000)
        await ctx.close()
        # 2) element screenshots per section, after scrolling through (animations settled)
        ctx = await b.new_context(viewport={"width": 1920, "height": 1080})
        page = await ctx.new_page()
        await prep(page)
        for y in range(0, 13000, 300):
            await page.mouse.wheel(0, 300); await page.wait_for_timeout(120)
        await page.wait_for_timeout(1500)
        info = await page.evaluate("""() => {
          const q = s => Array.from(document.querySelectorAll(s));
          const box = e => { const r=e.getBoundingClientRect(); return {x:Math.round(r.left), y:Math.round(r.top+scrollY), w:Math.round(r.width), h:Math.round(r.height)} };
          const res = {};
          ['.header','.home__hero','.home__hero-content','.home__hero .title','.home__hero p','.home__hero video','.home__about','.home__about .images-double-text','.home__about .images-double-text__image','.home__about .images-double-text__content','.home__about h2','.home__about p','.home__degrees','.home__degrees img','.home__rooms','.home__rooms-preview__column','.home__rooms-preview__column .images','.home__rooms-preview__content','.home__rooms-preview__content .images','.home__rooms-preview__content .title','.home__corners-preview','.home__corners-preview__heading','.home__corners-preview__heading .title','.home__corners-preview__heading p','.home__corners-preview__featured-item','.images-double-text--stretch .images-double-text__image','.images-double-text--stretch .images-double-text__content','.images-text__media .images','.images-text__content','.heading--label','.heading--label [data-label]','.home__offers','footer','.cta'].forEach(s => { res[s] = q(s).slice(0,8).map(e => ({...box(e), fs:getComputedStyle(e).fontSize, pad:getComputedStyle(e).padding, mar:getComputedStyle(e).margin, gap:getComputedStyle(e).gap, br:getComputedStyle(e).borderRadius, bg:getComputedStyle(e).backgroundColor, gtc:getComputedStyle(e).gridTemplateColumns, disp:getComputedStyle(e).display, ai:getComputedStyle(e).alignItems, ar:getComputedStyle(e).aspectRatio})); });
          return res; }""")
        json.dump(info, open(OUT+"/boxes_1920.json","w"), indent=1)
        await page.evaluate("window.scrollTo(0,0)"); await page.wait_for_timeout(1500)
        await page.screenshot(path=OUT+"/hero.png")
        for i, sel in enumerate(['.header','.home__about','.home__degrees','.home__rooms','.home__corners-preview__heading','.home__corners-preview__featured-item:nth-child(1)','.home__corners-preview__featured-item:nth-child(2)','.home__corners-preview__featured-item:nth-child(3)','.home__corners-preview__featured-item:nth-child(4)','.home__offers','footer']):
            try:
                el = page.locator(sel).first
                await el.scroll_into_view_if_needed(); await page.wait_for_timeout(1800)
                await el.screenshot(path=f"{OUT}/sec_{i:02d}_{sel.strip('.').replace(' ','_').replace(':','').replace('(','').replace(')','')}.png")
            except Exception as e:
                print("fail", sel, e)
        # hover CTA state
        await page.locator('.home__about').first.scroll_into_view_if_needed(); await page.wait_for_timeout(1200)
        bb = await page.locator('.home__about').first.bounding_box()
        await page.mouse.move(bb['x']+bb['width']/2, bb['y']+bb['height']/2); await page.wait_for_timeout(1200)
        await page.screenshot(path=OUT+"/hover_about.png")
        # menu open
        await page.evaluate("window.scrollTo(0,0)"); await page.wait_for_timeout(800)
        try:
            burger = page.locator('.header [class*=burger], .header [class*=menu-toggle], .header [class*=toggler]').last
            await burger.click(timeout=3000); await page.wait_for_timeout(1500)
            await page.screenshot(path=OUT+"/menu_open.png")
        except Exception as e: print("menu fail", e)
        # scrolled header state
        await page.keyboard.press("Escape")
        await page.evaluate("window.scrollTo(0,1600)"); await page.wait_for_timeout(1500)
        await page.screenshot(path=OUT+"/scrolled_header.png")
        await b.close()
    print("ok")
asyncio.run(main())
