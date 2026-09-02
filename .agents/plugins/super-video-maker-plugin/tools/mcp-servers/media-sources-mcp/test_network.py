import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import json

async def test_pixabay_network():
    query = "sunset"
    url = f"https://pixabay.com/music/search/{urllib.parse.quote(query)}/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        found_data = []
        
        async def handle_response(response):
            if "api/audio/v1" in response.url or "graphql" in response.url or "search" in response.url:
                if response.request.resource_type in ["xhr", "fetch"]:
                    print(f"Intercepted API response: {response.url}")
                    try:
                        json_data = await response.json()
                        print("Keys:", json_data.keys())
                        found_data.append(json_data)
                    except:
                        pass
        
        page.on("response", handle_response)
        
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        
        print(f"Found {len(found_data)} potential API responses")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_pixabay_network())
