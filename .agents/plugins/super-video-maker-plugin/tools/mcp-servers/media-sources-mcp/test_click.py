import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import json

async def scrape_pixabay_audio_by_clicking():
    query = "sunset"
    url = f"https://pixabay.com/music/search/{urllib.parse.quote(query)}/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        found_mp3s = []
        
        async def handle_response(response):
            if ".mp3" in response.url or "audio" in response.url:
                if response.status == 200:
                    print("Found audio URL:", response.url)
                    found_mp3s.append(response.url)
                    
        page.on("response", handle_response)
        
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        print("Looking for play buttons...")
        # Pixabay usually has play buttons with an icon. Let's just click the first button that might be a play button.
        # Alternatively, we can find elements with class containing 'play'
        play_buttons = await page.query_selector_all('button')
        for btn in play_buttons:
            class_name = await btn.get_attribute('class')
            if class_name and ('play' in class_name.lower() or 'button' in class_name.lower()):
                try:
                    await btn.click(timeout=1000)
                    await page.wait_for_timeout(1000)
                    if found_mp3s:
                        break
                except:
                    pass
        
        print(f"Total MP3s found: {len(found_mp3s)}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_pixabay_audio_by_clicking())
