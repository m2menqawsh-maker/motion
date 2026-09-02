import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import re

async def test_pixabay_regex():
    query = "sunset"
    url = f"https://pixabay.com/music/search/{urllib.parse.quote(query)}/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        
        # Wait a bit
        await page.wait_for_timeout(3000)
        
        content = await page.content()
        
        # Look for any url in the page content
        mp3s = re.findall(r'https?://[^"\'\s]+\.mp3', content)
        print(f"Found {len(mp3s)} mp3 links")
        for m in mp3s[:5]:
            print(m)
            
        json_blobs = re.findall(r'{[^}]*mp3[^}]*}', content)
        print(f"Found {len(json_blobs)} JSON blobs containing 'mp3'")
        
        # Let's find any .mp3 or similar in page text or attributes
        elements = await page.query_selector_all('div')
        print(f"Total div elements: {len(elements)}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_pixabay_regex())
