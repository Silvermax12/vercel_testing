import requests
from Crypto.Cipher import AES
import m3u8
import os
import subprocess

# Test URL (your .m3u8 link)
m3u8_url = "https://vault-02.padorupado.ru/stream/02/16/65d5ebb83dde5171651b6c877c2010bd2a76880e5919a7c7e515d6389897787e/uwu.m3u8"

# Output files
raw_file = "raw_output.ts"   # temporary decrypted file
final_file = "output.mp4"    # final playable mp4

# Step 1: Fetch the m3u8 playlist
playlist = m3u8.load(m3u8_url)
print("Playlist loaded.")

# Step 2: Get the key URI and download the key
if playlist.keys and len(playlist.keys) > 0 and playlist.keys[0] is not None:
    key_uri = playlist.keys[0].uri
    if key_uri is not None:
        key_url = key_uri if key_uri.startswith("http") else os.path.join(os.path.dirname(m3u8_url), key_uri)
        key = requests.get(key_url).content
        print("Key downloaded:", key.hex())
    else:
        print("Key URI is None, cannot download key")
        key = None
else:
    print("No keys found in playlist")
    key = None

# Step 3: Prepare AES decryptor
if key is not None:
    cipher = AES.new(key, AES.MODE_CBC, iv=key)  # NOTE: IV might differ, check playlist for EXT-X-KEY IV field
    print("AES cipher ready.")
else:
    cipher = None
    print("No key available, cannot create cipher.")

# Step 4: Download and decrypt segments into raw .ts file
with open(raw_file, "wb") as f:
    for i, segment in enumerate(playlist.segments):
        seg_url = segment.uri if segment.uri.startswith("http") else os.path.join(os.path.dirname(m3u8_url), segment.uri)
        seg_data = requests.get(seg_url).content

        # Decrypt only if cipher is available
        if cipher is not None:
            decrypted = cipher.decrypt(seg_data)
        else:
            decrypted = seg_data  # Use raw data if no encryption

        f.write(decrypted)
        print(f"Segment {i+1}/{len(playlist.segments)} done.")

print("✅ Download complete. Raw file saved as", raw_file)

# Step 5: Re-encode with ffmpeg into clean MP4
print("🎞️ Re-encoding to MP4...")
try:
    subprocess.run([
        "ffmpeg", "-y", "-i", raw_file,
        "-c:v", "libx264", "-c:a", "aac",
        final_file
    ], check=True)
    print("✅ Re-encoding done. Final video saved as", final_file)
except subprocess.CalledProcessError as e:
    print("❌ Error during re-encoding:", e)
