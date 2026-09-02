import asyncio
import sys
import io

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')

from server import (
    pixabay_search_images,
    pexels_search_videos,
    freesound_search,
    download_asset,
    change_asset_status
)

async def main():
    print("--- 1. Testing Pixabay Search Images ('sunset') ---")
    pixabay_res = await pixabay_search_images("sunset", per_page=3)
    if pixabay_res:
        first_pixabay = pixabay_res[0]
        print(f"Pixabay Result: ID={first_pixabay.get('id')}, URL={first_pixabay.get('largeImageURL')}")
    else:
        print("No Pixabay results found.")

    print("\n--- 2. Testing Pexels Search Videos ('sunset') ---")
    pexels_res = await pexels_search_videos("sunset", per_page=1)
    if pexels_res:
        first_pexels = pexels_res[0]
        print(f"Pexels Result: ID={first_pexels.get('id')}, URL={first_pexels.get('url')}")
    else:
        print("No Pexels results found.")

    print("\n--- 3. Testing Freesound Search ('sunset') ---")
    freesound_res = await freesound_search("sunset", page=1, page_size=1)
    if freesound_res:
        first_fs = freesound_res[0]
        print(f"Freesound Result: ID={first_fs.get('id')}, Name={first_fs.get('name')}")
    else:
        print("No Freesound results found.")

    if pixabay_res:
        print("\n--- 4. Testing Download Asset (Pixabay Image) ---")
        img_url = first_pixabay.get('largeImageURL')
        img_id = str(first_pixabay.get('id'))
        
        # Download
        downloaded_path = await download_asset(
            url=img_url, 
            asset_type="image", 
            source="pixabay", 
            asset_id=img_id
        )
        print(f"Downloaded successfully to: {downloaded_path}")
        
        print("\n--- 5. Testing Change Asset Status (incoming -> processing) ---")
        new_path = change_asset_status(
            file_path=downloaded_path,
            from_status="incoming",
            to_status="processing",
            asset_type="image"
        )
        print(f"Moved successfully to: {new_path}")

if __name__ == "__main__":
    asyncio.run(main())
