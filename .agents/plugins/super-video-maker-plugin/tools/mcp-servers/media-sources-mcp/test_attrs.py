import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import re
import json

async def scrape_pixabay_attrs():
    query = "sunset"
    url = f"https://pixabay.com/music/search/{urllib.parse.quote(query)}/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.goto(url, wait_until="networkidle")
        
        # Look for elements with data attributes that might be JSON
        elements = await page.query_selector_all('*')
        
        print(f"Total elements: {len(elements)}")
        for i, el in enumerate(elements):
            try:
                # get all attributes is not natively supported by query_selector easily in playwright, 
                # so we evaluate JS to get all attributes
                attrs = await el.evaluate("""(element) => {
                    const attrs = {};
                    for (let i = 0; i < element.attributes.length; i++) {
                        attrs[element.attributes[i].name] = element.attributes[i].value;
                    }
                    return attrs;
                }""")
                for name, value in attrs.items():
                    if 'mp3' in value or 'audio' in value:
                        if name not in ['class', 'id', 'href', 'src']:
                            print(f"Found suspicious attribute: {name} = {value[:200]}")
            except:
                pass
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_pixabay_attrs())
