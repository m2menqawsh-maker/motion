import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import os

async def dump_html():
    query = "sunset"
    url = f"https://pixabay.com/music/search/{urllib.parse.quote(query)}/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        content = await page.content()
        with open("dump.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_html())
