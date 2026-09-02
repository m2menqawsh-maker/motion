import asyncio
import os
from dotenv import load_dotenv
from server import mcp, pixabay_search_images, pexels_search_videos, freesound_search, pixabay_search_audio, download_asset, change_asset_status

load_dotenv()

async def run_tests():
    print("1. API Keys loaded:", bool(os.environ.get("PIXABAY_API_KEY")), bool(os.environ.get("PEXELS_API_KEY")), bool(os.environ.get("FREESOUND_API_KEY")))
    
    print("\n2. Testing pixabay_search_images...")
    images = await pixabay_search_images("sunset", per_page=3)
    if images:
        print(f"Success! Found image: {images[0].get('id')} - {images[0].get('pageURL')}")
        
    print("\n3. Testing pexels_search_videos...")
    videos = await pexels_search_videos("sunset", per_page=3)
    if videos:
        print(f"Success! Found video: {videos[0].get('id')} - {videos[0].get('url')}")
        
    print("\n4. Testing freesound_search...")
    sounds = await freesound_search("sunset", page_size=1)
    if sounds and "results" in sounds and sounds["results"]:
        print(f"Success! Found sound: {sounds['results'][0].get('id')} - {sounds['results'][0].get('name')}")
        
    print("\n4b. Testing pixabay_search_audio (Playwright)...")
    pix_audio = await pixabay_search_audio("sunset", max_results=2)
    if pix_audio:
        print(f"Success! Found audio: {pix_audio[0]}")
        
    print("\n5. Testing download_asset on Pixabay Image...")
    if images:
        image_url = images[0].get('webformatURL')
        image_id = str(images[0].get('id'))
        print(f"Downloading {image_url}...")
        downloaded_path = await download_asset(image_url, "image", "pixabay", image_id)
        print(f"Downloaded to: {downloaded_path}")
        
        print("\n6. Testing change_asset_status...")
        new_path = change_asset_status(downloaded_path, "incoming", "processing", "image")
        print(f"Moved from {downloaded_path} to {new_path}")
        
        # Verify it exists
        if os.path.exists(new_path):
            print("File successfully moved and verified!")
        else:
            print("ERROR: File not found at new location.")

if __name__ == "__main__":
    asyncio.run(run_tests())
