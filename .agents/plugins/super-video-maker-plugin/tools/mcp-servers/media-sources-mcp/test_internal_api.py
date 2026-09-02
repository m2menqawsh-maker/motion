import httpx
import asyncio

async def test():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    }
    async with httpx.AsyncClient() as client:
        r = await client.get('https://pixabay.com/api/audio/v1/search?q=sunset', headers=headers)
        print("Status:", r.status_code)
        print(r.text[:300])

asyncio.run(test())
