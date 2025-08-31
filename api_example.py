"""
Example client for the Anime Batch Downloader API
Run the API server first: python main.py
Then run this script to test the API endpoints
"""

import requests
import time
import json

# API base URL
BASE_URL = "http://localhost:8000"

def search_anime(query: str):
    """Search for anime"""
    response = requests.post(f"{BASE_URL}/search", json={"query": query})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Search failed: {response.text}")
        return None

def get_episodes(anime_session: str):
    """Get episodes for an anime"""
    response = requests.post(f"{BASE_URL}/episodes", json={"anime_session": anime_session})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Get episodes failed: {response.text}")
        return None

def get_qualities(anime_session: str, episode_session: str):
    """Get available qualities for an episode"""
    response = requests.post(f"{BASE_URL}/qualities", json={
        "anime_session": anime_session,
        "episode_session": episode_session
    })
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Get qualities failed: {response.text}")
        return None

def start_download(anime_session: str, episodes: list, quality: str = "720", language: str = "eng"):
    """Start downloading episodes"""
    response = requests.post(f"{BASE_URL}/download", json={
        "anime_session": anime_session,
        "episodes": episodes,
        "quality": quality,
        "language": language,
        "download_directory": "./"
    })
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Download failed: {response.text}")
        return None

def check_download_status(task_id: str):
    """Check download task status"""
    response = requests.get(f"{BASE_URL}/download/{task_id}")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Status check failed: {response.text}")
        return None

def list_downloads():
    """List all download tasks"""
    response = requests.get(f"{BASE_URL}/downloads")
    if response.status_code == 200:
        return response.json()
    else:
        print(f"List downloads failed: {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    print("🔎 Searching for anime...")
    
    # Search for anime
    query = input("Enter anime name: ").strip()
    results = search_anime(query)
    
    if not results:
        print("No results found")
        exit()
    
    print("\nSearch results:")
    for i, anime in enumerate(results, 1):
        print(f"{i:2d}. {anime['title']} [type: {anime['type']}, eps: {anime['episodes']}, id: {anime['id']}]")
    
    # Select anime
    try:
        idx = int(input("\nSelect number: ")) - 1
        selected = results[idx]
    except (ValueError, IndexError):
        print("Invalid selection")
        exit()
    
    # Get episodes
    print(f"\n📺 Getting episodes for: {selected['title']}...")
    episodes = get_episodes(selected['session'])
    
    if not episodes:
        print("No episodes found")
        exit()
    
    print(f"✅ Found {len(episodes)} episodes")
    
    # Get qualities for first episode
    first_ep = episodes[0]
    print(f"\n🔎 Checking qualities for Episode {first_ep['episode']}...")
    qualities = get_qualities(selected['session'], first_ep['session'])
    
    if qualities:
        print("Available qualities:", list(qualities['available_qualities'].keys()))
        
        # Select quality and language
        quality = input("Enter quality [720]: ").strip() or "720"
        available_langs = qualities['available_qualities'].get(quality, [])
        
        if available_langs:
            print(f"Available languages: {', '.join(available_langs)}")
            language = input(f"Enter language [{available_langs[0]}]: ").strip() or available_langs[0]
        else:
            language = "eng"
    
    # Select episodes to download
    selection = input("\nEnter episode selection (all, 1-5, 1,3,5): ").strip().lower()
    
    if selection == "all":
        episode_numbers = [ep['episode'] for ep in episodes]
    elif "-" in selection:
        start, end = map(int, selection.split("-"))
        episode_numbers = [ep['episode'] for ep in episodes if start <= ep['episode'] <= end]
    else:
        episode_numbers = [int(x) for x in selection.split(",") if x.isdigit()]
    
    print(f"\n📥 Starting download for {len(episode_numbers)} episodes...")
    
    # Start download
    download_result = start_download(
        anime_session=selected['session'],
        episodes=episode_numbers,
        quality=quality,
        language=language
    )
    
    if download_result:
        task_id = download_result['task_id']
        print(f"✅ Download started! Task ID: {task_id}")
        
        # Monitor progress
        print("\n📊 Monitoring download progress...")
        while True:
            status = check_download_status(task_id)
            if status:
                print(f"\rStatus: {status['status']} | Progress: {status['progress']:.1f}% | Episode: {status.get('current_episode', 'N/A')}", end="", flush=True)
                
                if status['status'] in ['completed', 'failed']:
                    print()  # New line
                    if status['status'] == 'completed':
                        print("🎉 All downloads completed!")
                    else:
                        print(f"❌ Download failed: {status.get('error_message', 'Unknown error')}")
                    break
            
            time.sleep(2)  # Check every 2 seconds
    else:
        print("❌ Failed to start download")
