import sys
import time
import os
import requests
from time import sleep
from tqdm import tqdm
from http.client import IncompleteRead


def download_with_progress(session, url: str, filename: str):
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        start = time.time()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                elapsed = time.time() - start
                speed = downloaded / (1024*1024) / elapsed if elapsed > 0 else 0
                percent = (downloaded / total) * 100 if total else 0
                eta = (total - downloaded) / (speed*1024*1024) if speed > 0 else 0
                sys.stdout.write(
                    f"\r{filename} {percent:.2f}% "
                    f"{downloaded/1024/1024:.2f}MB/{total/1024/1024:.2f}MB "
                    f"{speed:.2f}MB/s ETA {eta:.1f}s"
                )
                sys.stdout.flush()
    print("\n✅ Download complete:", filename)


def advanced_download_with_progress(download_info, download_directory="./"):
    """
    Advanced download function with POST support, resume capability, and retry logic.
    Takes download_info dict from resolve_download_info function.
    """
    if not download_info or not download_info.get('url'):
        print("❌ Invalid download information provided")
        return False

    # Use extracted filename or fallback to generic name
    if download_info.get('filename'):
        filename = download_info['filename']
    else:
        filename = "episode.mp4"
    
    # Set the full file path
    full_file_path = os.path.join(download_directory, filename)
    
    # Create session and set cookies
    session = requests.Session()
    for name, value in download_info.get('cookies', {}).items():
        session.cookies.set(name, value)

    download_url = download_info['url']
    form_data = download_info.get('form_data', {})
    headers = download_info.get('headers', {})

    print(f"📥 Starting download: {filename}")
    print(f"🔗 Download URL: {download_url}")
    
    # Check if a partial file exists and resume download if possible
    resume_header = {}
    mode = 'wb'  # Write mode for new download
    if os.path.exists(full_file_path):
        existing_size = os.path.getsize(full_file_path)
        if existing_size > 0:
            resume_header = {'Range': f"bytes={existing_size}-"}
            mode = 'ab'  # Append mode for partial download
            print(f"📄 Resuming download from {existing_size} bytes")

    retries = 999  # Maximum number of retries for internet issues
    retry_delay = 10  # Time (in seconds) to wait before retrying
    downloaded = False

    while not downloaded and retries > 0:
        try:
            # Combine headers
            request_headers = {**headers, **resume_header}
            
            with session.post(download_url, data=form_data, headers=request_headers, stream=True, timeout=120) as response:
                response.raise_for_status()

                remaining_size = int(response.headers.get('content-length', 0))
                current_size = os.path.getsize(full_file_path) if os.path.exists(full_file_path) else 0
                
                # Calculate total size (current + remaining for resume, or just remaining for new download)
                if mode == 'ab':  # Resume mode
                    total_size = current_size + remaining_size
                else:  # New download
                    total_size = remaining_size
                
                # Initialize progress bar with speed and ETA
                progress = tqdm(
                    total=total_size if total_size > 0 else None,
                    unit='B',
                    unit_scale=True,
                    unit_divisor=1024,
                    initial=current_size,
                    desc=os.path.basename(filename),
                    ncols=100,  # Wider to accommodate speed and ETA
                    miniters=1,  # Update every chunk for smooth display
                    smoothing=0.1,  # Smoothing factor for speed calculation
                    bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
                )

                with open(full_file_path, mode) as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                            progress.update(len(chunk))
                
                progress.close()
                downloaded = True  # Download completed successfully
                print(f"✅ Downloaded successfully: {full_file_path}")
                return True

        except (requests.exceptions.RequestException, requests.exceptions.ChunkedEncodingError) as e:
            retries -= 1
            print(f"⚠️ Network error: {e}. Retrying in {retry_delay} seconds... ({retries} retries left)")
            sleep(retry_delay)

        except IncompleteRead as e:
            print(f"⚠️ Incomplete download: {e}. Retrying...")
            retries -= 1
            sleep(retry_delay)

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            retries -= 1
            sleep(retry_delay)

    if not downloaded:
        print(f"❌ Failed to download after multiple retries: {filename}")
        return False


