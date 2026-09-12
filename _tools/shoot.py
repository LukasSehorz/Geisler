#!/usr/bin/env python3
"""Scroll-through screenshots of a local page (Lenis-friendly).
usage: shoot.py <url> <outdir> [width height step maxshots]"""
import asyncio, sys, os
from playwright.async_api import async_playwright
url, out = sys.argv[1], sys.argv[2]
W = int(sys.argv[3]) if len(sys.argv) > 3 else 1920
H = int(sys.argv[4]) if len(sys.argv) > 4 else 1080
STEP = int(sys.argv[5]) if len(sys.argv) > 5 else 540
MAX = int(sys.argv[6]) if len(sys.argv) > 6 else 60
os.makedirs(out, exist_ok=True)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--autoplay-policy=no-user-gesture-required"])
        ctx = await b.new_context(viewport={"width": W, "height": H}, device_scale_factor=1)
        page = await ctx.new_page()
        logs = []
        page.on("console", lambda m: logs.append(f"{m.type}: {m.text}"))
        page.on("pageerror", lambda e: logs.append(f"PAGEERROR: {e}"))
        await page.goto(url, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(3200)
        await page.screenshot(path=f"{out}/00_top.png")
        total = await page.evaluate("document.documentElement.scrollHeight")
        y, i = 0, 1
        while y < total - H and i < MAX:
            for _ in range(6):
                await page.mouse.wheel(0, STEP / 6); await page.wait_for_timeout(35)
            y += STEP
            await page.wait_for_timeout(1100)
            await page.screenshot(path=f"{out}/{i:02d}_y{y}.png"); i += 1
            total = await page.evaluate("document.documentElement.scrollHeight")
        print("height", total, "shots", i)
        for l in logs: print(l)
        await b.close()
asyncio.run(main())
