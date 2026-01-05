import requests
import time
import re
from src.api import get_api_base, get_api_token

# Test anime
test_anime = ['attack on titan', 'demon slayer', 'jujutsu kaisen']

for search_term in test_anime:
    # Get anime from API
    r = requests.post(
        get_api_base() + 'anime/load_anime_list_v2.php',
        data={
            'UserId': '0',
            'Language': 'English',
            'FilterType': 'SEARCH',
            'FilterData': search_term,
            'Type': 'SERIES',
            'From': '0',
            'Token': get_api_token()
        },
        timeout=10
    )
    
    data = r.json()[0]
    print(f"\n{'='*60}")
    print(f"Anime: {data['EN_Title']}")
    print(f"API Trailer: {data.get('Trailer')}")
    print(f"API YTTrailer: {data.get('YTTrailer')}")
    print(f"MAL ID: {data.get('MalId')}")
    
    # Get trailer from Jikan
    mal_id = data.get('MalId')
    if mal_id and mal_id != '0':
        time.sleep(1)  # Rate limiting
        r2 = requests.get(f'https://api.jikan.moe/v4/anime/{mal_id}', timeout=10)
        jikan = r2.json()
        trailer = jikan.get('data', {}).get('trailer', {})
        embed_url = trailer.get('embed_url', '')
        
        print(f"Jikan Embed URL: {embed_url}")
        
        if embed_url:
            # Extract YouTube ID from embed URL
            match = re.search(r'/embed/([a-zA-Z0-9_-]+)', embed_url)
            if match:
                yt_id = match.group(1)
                full_url = f'https://www.youtube.com/watch?v={yt_id}'
                print(f"✓ YouTube ID: {yt_id}")
                print(f"✓ Full URL: {full_url}")
            else:
                print("✗ Could not extract YouTube ID")
        else:
            print("✗ No trailer available")
