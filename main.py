from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import os
import uuid
import json
from datetime import datetime

# Check if running on Vercel
IS_VERCEL = os.getenv("VERCEL_ENV") == "production"

from session_mgr import SessionManager
from api_client import search_anime, get_all_episodes
from scraper import scrape_download_links, scrape_m3u8_links, scrape_multiple_episodes_m3u8, save_m3u8_results
from resolver import resolve_download_info
from transfer import advanced_download_with_progress

app = FastAPI(
    title="Anime Batch Downloader API",
    description="API service for downloading anime episodes from AnimePagehe",
    version="1.0.0"
)

# Global session manager - initialized lazily to avoid startup issues
sm = None

def get_session_manager():
    """Get or create session manager"""
    global sm
    if sm is None:
        sm = SessionManager()
    return sm

# In-memory storage for download tasks (in production, use Redis or database)
download_tasks = {}

class SearchRequest(BaseModel):
    query: str

class SearchResult(BaseModel):
    title: str
    type: str
    episodes: int
    id: int
    session: str
    status: Optional[str] = None
    season: Optional[str] = None
    year: Optional[int] = None
    score: Optional[float] = None
    poster: Optional[str] = None

class EpisodesRequest(BaseModel):
    anime_session: str

class Episode(BaseModel):
    episode: int
    session: str

class QualityRequest(BaseModel):
    anime_session: str
    episode_session: str

class DownloadRequest(BaseModel):
    anime_session: str
    episodes: List[int]  # List of episode numbers
    quality: str = "720"
    language: str = "eng"
    download_directory: str = "./"

class DownloadRequestM3U8(BaseModel):
    m3u8_file: str  # Path to the JSON file containing m3u8 links
    episodes: Optional[List[int]] = None  # Optional: specific episodes to download
    download_directory: str = "./"

class DownloadTask(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: float
    current_episode: Optional[int] = None
    total_episodes: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "Anime Batch Downloader API", "version": "1.0.0"}

@app.post("/search", response_model=List[SearchResult])
async def search_anime_endpoint(request: SearchRequest):
    """Search for anime by name"""
    try:
        # Get session manager in a thread-safe way
        session_manager = get_session_manager()
        results = search_anime(session_manager, request.query)
        if not results:
            raise HTTPException(status_code=404, detail="No anime found for your search query. Try different keywords.")
        
        return [SearchResult(**result) for result in results]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Search endpoint error: {error_details}")
        
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            raise HTTPException(
                status_code=503, 
                detail="AnimePagehe service is temporarily unavailable. Please try again later or check your internet connection."
            )
        elif "animepahe.ru" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="Cannot connect to AnimePagehe. The service may be down or your connection may be blocked."
            )
        else:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.post("/episodes", response_model=List[Episode])
async def get_episodes_endpoint(request: EpisodesRequest):
    """Get all episodes for a specific anime"""
    try:
        session_manager = get_session_manager()
        episodes = get_all_episodes(session_manager, request.anime_session)
        if not episodes:
            raise HTTPException(status_code=404, detail="No episodes found")
        
        return [Episode(**ep) for ep in episodes]
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Episodes endpoint error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to get episodes: {str(e)}")

@app.post("/qualities")
async def get_qualities_endpoint(request: QualityRequest):
    """Get available qualities and languages for a specific episode"""
    try:
        print(f"🔍 Fetching qualities for anime: {request.anime_session}, episode: {request.episode_session}")
        
        links = scrape_download_links(request.anime_session, request.episode_session)
        if not links:
            raise HTTPException(
                status_code=404, 
                detail="No download links found for this episode. The episode may not be available or the site structure may have changed."
            )
        
        # Parse qualities and languages
        qualities = {}
        for key in links.keys():
            if "_" in key:
                quality, language = key.split("_", 1)
                if quality not in qualities:
                    qualities[quality] = []
                if language not in qualities[quality]:
                    qualities[quality].append(language)
        
        print(f"✅ Found {len(links)} download links with {len(qualities)} quality options")
        return {
            "available_qualities": qualities,
            "raw_links": links
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Qualities endpoint error: {error_details}")
        
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="The episode page took too long to load. This may be due to high traffic or site issues. Please try again later."
            )
        elif "selenium" in error_msg.lower() or "webdriver" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Browser automation failed. The site structure may have changed or there may be technical issues."
            )
        elif "animepahe.ru" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Cannot access AnimePagehe episode page. The service may be temporarily unavailable."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get episode qualities: {str(e)}"
            )

@app.post("/m3u8-links")
async def get_m3u8_links_endpoint(request: EpisodesRequest, quality: str = "720", language: str = "eng"):
    """Get .m3u8 links for all episodes of an anime after clicking 'Click to load'"""
    try:
        print(f"🎬 Getting .m3u8 links for anime: {request.anime_session}, quality: {quality}p, language: {language}")

        # Get all episodes first
        session_manager = get_session_manager()
        episodes = get_all_episodes(session_manager, request.anime_session)
        if not episodes:
            raise HTTPException(status_code=404, detail="No episodes found")

        # Extract episode sessions
        episode_sessions = [ep["session"] for ep in episodes]

        # Scrape m3u8 links for all episodes
        m3u8_results = scrape_multiple_episodes_m3u8(
            request.anime_session,
            episode_sessions,
            quality=quality,
            language=language
        )

        if not m3u8_results:
            raise HTTPException(
                status_code=404,
                detail="No .m3u8 links found. The episodes may not be available or the site structure may have changed."
            )

        # Save results to JSON file
        filename = f"m3u8_links_{request.anime_session}_{quality}p_{language}.json"
        save_m3u8_results(m3u8_results, filename)

        print(f"✅ Successfully extracted {len(m3u8_results)} .m3u8 links")
        return {
            "anime_session": request.anime_session,
            "quality": quality,
            "language": language,
            "total_episodes": len(episodes),
            "m3u8_links_found": len(m3u8_results),
            "m3u8_data": m3u8_results,
            "json_file": filename
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ M3U8 links endpoint error: {error_details}")

        # Provide more user-friendly error messages
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="The episode pages took too long to load. This may be due to high traffic or site issues. Please try again later."
            )
        elif "selenium" in error_msg.lower() or "webdriver" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Browser automation failed. The site structure may have changed or there may be technical issues."
            )
        elif "animepahe.ru" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Cannot access AnimePagehe episode pages. The service may be temporarily unavailable."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get .m3u8 links: {str(e)}"
            )

@app.post("/m3u8-single")
async def get_single_m3u8_link_endpoint(request: QualityRequest, quality: str = "720", language: str = "eng"):
    """Get .m3u8 link for a single episode"""
    try:
        print(f"🎬 Getting .m3u8 link for anime: {request.anime_session}, episode: {request.episode_session}, quality: {quality}p, language: {language}")

        # Scrape m3u8 link for the episode
        m3u8_data = scrape_m3u8_links(
            request.anime_session,
            request.episode_session,
            quality=quality,
            language=language
        )

        if not m3u8_data:
            raise HTTPException(
                status_code=404,
                detail="No .m3u8 link found for this episode. The episode may not be available or the site structure may have changed."
            )

        print(f"✅ Successfully extracted .m3u8 link")
        return {
            "anime_session": request.anime_session,
            "episode_session": request.episode_session,
            "quality": quality,
            "language": language,
            "m3u8_data": m3u8_data
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Single M3U8 link endpoint error: {error_details}")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to get .m3u8 link: {str(e)}"
        )

@app.get("/m3u8-files")
async def list_m3u8_files():
    """List all saved .m3u8 JSON files"""
    try:
        files = [f for f in os.listdir('.') if f.startswith('m3u8_links_') and f.endswith('.json')]
        return {"m3u8_files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")

@app.get("/m3u8-files/{filename}")
async def get_m3u8_file(filename: str):
    """Get contents of a specific .m3u8 JSON file"""
    try:
        if not filename.startswith('m3u8_links_') or not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Invalid filename format")

        if not os.path.exists(filename):
            raise HTTPException(status_code=404, detail="File not found")

        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return {
            "filename": filename,
            "data": data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")

@app.post("/download")
async def start_download_endpoint(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start downloading episodes"""
    try:
        if IS_VERCEL:
            # On Vercel, return immediate response with limitation notice
            return {
                "message": "Download functionality is limited on Vercel due to serverless constraints.",
                "suggestion": "Use the /download-m3u8 endpoint for M3U8 downloads, or deploy to a dedicated server for full functionality.",
                "vercel": True
            }

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Get episodes for the anime
        session_manager = get_session_manager()
        all_episodes = get_all_episodes(session_manager, request.anime_session)
        selected_episodes = [ep for ep in all_episodes if ep["episode"] in request.episodes]

        if not selected_episodes:
            raise HTTPException(status_code=404, detail="No matching episodes found")

        # Create download task
        task = DownloadTask(
            task_id=task_id,
            status="pending",
            progress=0.0,
            total_episodes=len(selected_episodes),
            created_at=datetime.now()
        )
        download_tasks[task_id] = task

        # Start download in background
        background_tasks.add_task(
            download_episodes_background,
            task_id,
            request.anime_session,
            selected_episodes,
            request.quality,
            request.language,
            request.download_directory
        )

        return {"task_id": task_id, "message": f"Download started for {len(selected_episodes)} episodes"}

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Download endpoint error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to start download: {str(e)}")

@app.post("/download-m3u8")
async def start_m3u8_download_endpoint(request: DownloadRequestM3U8, background_tasks: BackgroundTasks):
    """Start downloading episodes using .m3u8 links from JSON file"""
    try:
        if IS_VERCEL:
            # On Vercel, provide information about limitations but still allow the operation
            # since M3U8 processing can be done within time limits for small batches
            print("⚠️ Running on Vercel - M3U8 downloads may be limited by execution time")

        # Validate m3u8 file exists
        if not os.path.exists(request.m3u8_file):
            raise HTTPException(status_code=404, detail=f"M3U8 file '{request.m3u8_file}' not found")

        # Load m3u8 data from file
        with open(request.m3u8_file, 'r', encoding='utf-8') as f:
            m3u8_data = json.load(f)

        if not m3u8_data:
            raise HTTPException(status_code=400, detail="M3U8 file is empty or invalid")

        # Determine which episodes to download
        episodes_to_download = request.episodes
        if episodes_to_download is None:
            # Download all episodes from the file
            episodes_to_download = [int(ep) for ep in m3u8_data.keys()]

        # Validate episodes exist in the file
        missing_episodes = []
        valid_episodes = []
        for ep_num in episodes_to_download:
            if str(ep_num) in m3u8_data:
                valid_episodes.append(ep_num)
            else:
                missing_episodes.append(ep_num)

        if missing_episodes:
            print(f"⚠️ Episodes {missing_episodes} not found in M3U8 file, skipping")

        if not valid_episodes:
            raise HTTPException(status_code=400, detail="No valid episodes found in M3U8 file")

        # On Vercel, limit the number of episodes to prevent timeout
        if IS_VERCEL and len(valid_episodes) > 2:
            print(f"⚠️ Limiting to 2 episodes on Vercel to prevent timeout (requested: {len(valid_episodes)})")
            valid_episodes = valid_episodes[:2]

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Create download task
        task = DownloadTask(
            task_id=task_id,
            status="pending",
            progress=0.0,
            total_episodes=len(valid_episodes),
            created_at=datetime.now()
        )
        download_tasks[task_id] = task

        # For Vercel, we might want to handle downloads differently
        if IS_VERCEL:
            # On Vercel, we could return the task info and let client poll for status
            # But for now, we'll still try background processing
            background_tasks.add_task(
                download_episodes_m3u8_background,
                task_id,
                m3u8_data,
                valid_episodes,
                request.download_directory
            )
        else:
            # Normal background processing for dedicated servers
            background_tasks.add_task(
                download_episodes_m3u8_background,
                task_id,
                m3u8_data,
                valid_episodes,
                request.download_directory
            )

        response_message = f"M3U8 download started for {len(valid_episodes)} episodes"
        if IS_VERCEL:
            response_message += " (Vercel deployment - limited by serverless constraints)"

        return {
            "task_id": task_id,
            "message": response_message,
            "vercel": IS_VERCEL,
            "episode_limit": 2 if IS_VERCEL else None
        }

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ M3U8 download endpoint error: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to start M3U8 download: {str(e)}")

@app.get("/download/{task_id}")
async def get_download_status(task_id: str):
    """Get download task status and progress"""
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Download task not found")
    
    return download_tasks[task_id]

@app.get("/downloads")
async def list_download_tasks():
    """List all download tasks"""
    return {"tasks": list(download_tasks.values())}

@app.delete("/download/{task_id}")
async def cancel_download_task(task_id: str):
    """Cancel a download task (if possible)"""
    if task_id not in download_tasks:
        raise HTTPException(status_code=404, detail="Download task not found")
    
    task = download_tasks[task_id]
    if task.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel {task.status} task")
    
    task.status = "cancelled"
    return {"message": "Download task cancelled"}

async def download_episodes_background(
    task_id: str,
    anime_session: str,
    episodes: List[Dict[str, Any]],
    quality: str,
    language: str,
    download_directory: str
):
    """Background task to download episodes"""
    task = download_tasks[task_id]
    task.status = "running"
    
    try:
        for i, episode in enumerate(episodes):
            task.current_episode = episode["episode"]
            task.progress = (i / len(episodes)) * 100
            
            print(f"🎬 Processing Episode {episode['episode']}")
            
            # Get download links with retry for browser conflicts
            links = {}
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    links = scrape_download_links(anime_session, episode["session"])
                    if links:
                        break
                    else:
                        print(f"⚠️ No links found on attempt {attempt + 1}/{max_attempts}")
                except Exception as e:
                    print(f"⚠️ Scraping failed on attempt {attempt + 1}/{max_attempts}: {e}")
                    if "user data directory" in str(e).lower() or "session not created" in str(e).lower():
                        print("🔧 Browser conflict detected, retrying with delay...")
                        import time
                        time.sleep(2 ** attempt)  # Exponential backoff
                    if attempt == max_attempts - 1:
                        print(f"❌ Failed to get download links for episode {episode['episode']} after {max_attempts} attempts")
                        continue
            
            raw_url = links.get(f"{quality}_{language}")
            
            if not raw_url:
                print(f"⚠️ {quality}p {language.upper()} not available for episode {episode['episode']}")
                continue
            
            # Resolve download info
            download_info = resolve_download_info(raw_url)
            if not download_info:
                print(f"⚠️ Could not resolve download info for episode {episode['episode']}")
                continue
            
            # Set filename if not extracted
            if not download_info.get('filename'):
                download_info['filename'] = f"Episode_{episode['episode']}"
            
            # Download episode
            success = advanced_download_with_progress(download_info, download_directory)
            if not success:
                print(f"❌ Failed to download episode {episode['episode']}")
        
        # Mark task as completed
        task.status = "completed"
        task.progress = 100.0
        task.completed_at = datetime.now()
        print(f"✅ All episodes downloaded for task {task_id}")
        
    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        print(f"❌ Download task {task_id} failed: {e}")

async def download_episodes_m3u8_background(
    task_id: str,
    m3u8_data: Dict[str, Dict[str, Any]],
    episodes: List[int],
    download_directory: str
):
    """Background task to download episodes using .m3u8 links"""
    import requests
    import m3u8
    from Crypto.Cipher import AES
    import subprocess
    import tempfile
    import shutil

    task = download_tasks[task_id]
    task.status = "running"

    try:
        # Ensure download directory exists
        os.makedirs(download_directory, exist_ok=True)

        for i, episode_num in enumerate(episodes):
            task.current_episode = episode_num
            episode_key = str(episode_num)

            if episode_key not in m3u8_data:
                print(f"⚠️ Episode {episode_num} not found in M3U8 data, skipping")
                continue

            episode_info = m3u8_data[episode_key]
            m3u8_url = episode_info.get("m3u8_url")

            if not m3u8_url:
                print(f"⚠️ No M3U8 URL found for episode {episode_num}, skipping")
                continue

            print(f"🎬 Processing Episode {episode_num} - {m3u8_url}")

            try:
                # Step 1: Fetch the m3u8 playlist
                print(f"📥 Fetching M3U8 playlist for episode {episode_num}...")
                playlist = m3u8.load(m3u8_url)
                print(f"✅ Playlist loaded with {len(playlist.segments)} segments")

                # Step 2: Get the key URI and download the key
                key = None
                if playlist.keys and len(playlist.keys) > 0 and playlist.keys[0] is not None:
                    key_uri = playlist.keys[0].uri
                    if key_uri is not None:
                        key_url = key_uri if key_uri.startswith("http") else os.path.join(os.path.dirname(m3u8_url), key_uri)
                        key = requests.get(key_url).content
                        print(f"🔑 Downloaded decryption key ({len(key)} bytes)")

                # Step 3: Prepare AES decryptor
                cipher = None
                if key is not None:
                    cipher = AES.new(key, AES.MODE_CBC, iv=key)  # IV might differ, check playlist
                    print("🔐 AES cipher ready for decryption")

                # Step 4: Download and decrypt segments
                raw_file = os.path.join(download_directory, f"episode_{episode_num}_raw.ts")
                final_file = os.path.join(download_directory, f"episode_{episode_num}_final.mp4")

                print(f"📦 Downloading and decrypting segments to {raw_file}...")
                with open(raw_file, "wb") as f:
                    for seg_idx, segment in enumerate(playlist.segments):
                        seg_url = segment.uri if segment.uri.startswith("http") else os.path.join(os.path.dirname(m3u8_url), segment.uri)
                        seg_data = requests.get(seg_url).content

                        # Decrypt only if cipher is available
                        if cipher is not None:
                            decrypted = cipher.decrypt(seg_data)
                        else:
                            decrypted = seg_data  # Use raw data if no encryption

                        f.write(decrypted)

                        # Update progress for this segment
                        segment_progress = (seg_idx + 1) / len(playlist.segments)
                        episode_progress = (i / len(episodes)) + (segment_progress / len(episodes))
                        task.progress = episode_progress * 100

                        if seg_idx % 10 == 0:  # Update every 10 segments
                            print(f"📊 Episode {episode_num}: Segment {seg_idx + 1}/{len(playlist.segments)} downloaded")

                print(f"✅ Download complete for episode {episode_num}. Raw file saved as {raw_file}")

                # Step 5: Re-encode with ffmpeg into clean MP4
                print(f"🎞️ Re-encoding episode {episode_num} to MP4...")
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", raw_file,
                    "-c:v", "libx264", "-c:a", "aac",
                    "-preset", "fast", "-crf", "23",
                    final_file
                ]

                result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
                print(f"✅ Re-encoding done for episode {episode_num}. Final video saved as {final_file}")

                # Clean up raw file
                if os.path.exists(raw_file):
                    os.remove(raw_file)
                    print(f"🧹 Cleaned up raw file: {raw_file}")

                # Update progress
                task.progress = ((i + 1) / len(episodes)) * 100
                print(f"🎉 Episode {episode_num} completed successfully")

            except Exception as e:
                print(f"❌ Failed to process episode {episode_num}: {e}")
                # Continue with next episode instead of failing the whole task
                continue

        # Mark task as completed
        task.status = "completed"
        task.progress = 100.0
        task.completed_at = datetime.now()
        print(f"✅ All M3U8 episodes downloaded and processed for task {task_id}")

    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        print(f"❌ M3U8 download task {task_id} failed: {e}")

# Vercel serverless function handler
def handler(request, context=None):
    """
    Vercel serverless function handler.
    This function is called by Vercel when the serverless function is invoked.
    """
    from mangum import Mangum

    # Create ASGI handler for Vercel
    asgi_handler = Mangum(app)

    # Handle the request
    return asgi_handler(request, context)

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
