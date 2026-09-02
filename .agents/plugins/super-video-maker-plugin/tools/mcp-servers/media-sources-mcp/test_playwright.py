import asyncio
from playwright.async_api import async_playwright
import json
import urllib.parse
import os

async def test_pixabay_music():
    query = "sunset"
    url = f"https://pixabay.com/music/search/{urllib.parse.quote(query)}/"
    
    async with async_playwright() as p:
        # Launch headed to avoid some simple bot detections
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded")
        
        # Wait a bit
        await page.wait_for_timeout(5000)
        
        title = await page.title()
        print(f"Page Title: {title}")
        
        # Take screenshot
        await page.screenshot(path="screenshot.png")
        print("Screenshot saved to screenshot.png")
        
        # Look for script tags containing 'audio' or 'mp3'
        scripts = await page.query_selector_all('script')
        for s in scripts:
            content = await s.text_content()
            if content and ('mp3' in content or 'audioUrl' in content or 'downloadUrl' in content):
                print("Found a script tag containing mp3 or downloadUrl!")
                print(content[:500])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_pixabay_music())
