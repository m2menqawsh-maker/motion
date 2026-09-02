import httpx
import asyncio
import json

async def test():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://pixabay.com/',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    async with httpx.AsyncClient() as client:
        r = await client.get('https://pixabay.com/music/search/sunset/', headers=headers)
        print("Status:", r.status_code)
        try:
            data = r.json()
            print("Keys:", data.keys())
            if "results" in data or "data" in data or type(data) is list:
                print("Got JSON data!")
                print(str(data)[:300])
        except:
            print("Not JSON. Snippet:", r.text[:200])

asyncio.run(test())
