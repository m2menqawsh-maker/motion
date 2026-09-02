import httpx
import asyncio
import re
import json

async def test():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    async with httpx.AsyncClient() as client:
        r = await client.get('https://pixabay.com/music/search/sunset/', headers=headers)
        html = r.text
        
        # Look for the JSON data injected in a script tag
        # Pixabay usually uses something like <script>window.__INITIAL_DATA__ = ...</script>
        # or <script id="__NEXT_DATA__" type="application/json">...</script>
        
        match = re.search(r'application/json.*?>(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                print("Found JSON script tag!")
                print(str(data)[:500])
            except Exception as e:
                print("Failed to parse JSON:", e)
        else:
            print("No NEXT_DATA found.")
            
        # Try another common pattern
        match2 = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
        if match2:
            print("Found INITIAL_STATE!")
            
asyncio.run(test())
