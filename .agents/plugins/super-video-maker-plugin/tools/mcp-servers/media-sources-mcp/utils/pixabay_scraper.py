import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import logging

logger = logging.getLogger(__name__)

async def search_pixabay_audio(query: str, max_results: int = 10, media_type: str = "music"):
    """
    Scrape Pixabay music/sound-effects search results using Playwright.
    Prioritizes extracting window.__BOOTSTRAP__ state. Falls back to DOM parsing.
    Returns clear errors if no results are found.
    """
    url = f"https://pixabay.com/{media_type}/search/{urllib.parse.quote(query)}/"
    
    results = []
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = await context.new_page()
            
            logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # Try 1: Extract Bootstrap JSON
            bootstrap_data = await page.evaluate('''() => {
                try {
                    // Make a deep clone to avoid serialization issues
                    return JSON.parse(JSON.stringify(window.__BOOTSTRAP__.page.results));
                } catch(e) {
                    return null;
                }
            }''')
            
            if bootstrap_data and isinstance(bootstrap_data, list) and len(bootstrap_data) > 0:
                logger.info(f"Found {len(bootstrap_data)} results via __BOOTSTRAP__")
                for item in bootstrap_data[:max_results]:
                    # Extract fields
                    track_id = str(item.get("id", ""))
                    title = item.get("name", "") or item.get("title", "") or "Unknown Track"
                    duration = item.get("duration", 0)
                    
                    user = item.get("user", {})
                    author = user.get("username", "") or user.get("firstName", "Unknown")
                    
                    href = item.get("href", "")
                    page_url = f"https://pixabay.com{href}" if href and href.startswith('/') else href
                    
                    sources = item.get("sources", {})
                    direct_url = sources.get("src")
                    
                    results.append({
                        "id": f"pixabay_{track_id}",
                        "title": title,
                        "duration": duration,
                        "author": author,
                        "page_url": page_url,
                        "direct_url": direct_url,
                        "source": "pixabay"
                    })
            else:
                # Try 2: DOM fallback
                logger.info("Bootstrap JSON not found or empty, attempting DOM fallback")
                
                track_elements = await page.query_selector_all('div[class*="track"], div[class*="item"]')
                
                if not track_elements:
                    raise ValueError("No tracks found on Pixabay (neither in JSON nor DOM).")
                
                for i, el in enumerate(track_elements[:max_results]):
                    title = await el.text_content()
                    title = title.strip() if title else f"Pixabay Track {i+1}"
                    
                    # Try to find link inside element
                    link_el = await el.query_selector('a[href*="/music/"]')
                    href = await link_el.get_attribute('href') if link_el else ""
                    page_url = f"https://pixabay.com{href}" if href and href.startswith('/') else ""
                    
                    results.append({
                        "id": f"pixabay_{i}",
                        "title": title[:50],
                        "duration": 0,
                        "author": "Unknown",
                        "page_url": page_url,
                        "direct_url": None, # Direct URL not available via DOM fallback
                        "source": "pixabay"
                    })
            
            await browser.close()
            
            if not results:
                raise ValueError("Scraper returned 0 results.")
            
    except Exception as e:
        logger.error(f"Playwright scraping failed: {e}")
        raise RuntimeError(f"Failed to fetch Pixabay audio: {str(e)}")
        
    return results
