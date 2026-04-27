"""
Step 3: Rename downloaded files and embed rich metadata.

Reads tracklist.json (from step1) and the downloaded audio files (from step2).
For each track:
  1. Matches the downloaded file to the correct track using fuzzy title matching.
  2. Renames the file to a clean "Artist - Title.opus" format.
  3. Embeds metadata tags: title, artist, album, track number, cover art.
  4. Downloads and embeds the high-res Spotify album cover art.

Requires: mutagen, requests
"""
import json
import os
import sys
import re
import requests

try:
    from mutagen.oggopus import OggOpus
    from mutagen.flac import Picture
except ImportError:
    print("ERROR: mutagen not installed. Run: pip install mutagen")
    sys.exit(1)

try:
    from rapidfuzz import fuzz
except ImportError:
    # Fallback: simple substring matching
    fuzz = None



def sanitize_filename(name: str) -> str:
    """Remove characters that are illegal in Windows filenames."""
    # Replace illegal chars with nothing
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Collapse multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    # Trim to reasonable length
    if len(name) > 200:
        name = name[:200]
    return name


def download_cover(url: str, save_path: str) -> bool:
    """Download album cover art from Spotify CDN."""
    if not url:
        return False
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and len(r.content) > 1000:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


def match_file_to_track(filename: str, tracks: list) -> dict | None:
    """
    Match a downloaded file to the correct track using the exact track index prefix (e.g., '001 - ').
    """
    import re
    match = re.match(r'^(\d{3}) - ', filename)
    if match:
        index = int(match.group(1))
        if 1 <= index <= len(tracks):
            return tracks[index - 1]
    
    return None

def embed_metadata(filepath: str, track: dict, cover_path: str | None):
    """Embed metadata tags into an .opus file using mutagen."""
    try:
        audio = OggOpus(filepath)
    except Exception as e:
        print(f"    Could not open {filepath}: {e}")
        return False

    # Clear existing tags
    audio.delete()

    # Set tags
    audio["title"] = track["title"]
    audio["artist"] = ", ".join(track["artists"])
    audio["album"] = track.get("album", "")
    audio["tracknumber"] = str(track.get("track_number", ""))
    audio["date"] = ""  # We don't have year from scraping
    audio["comment"] = track.get("spotify_track_url", "")

    # Embed cover art if available
    if cover_path and os.path.exists(cover_path):
        try:
            with open(cover_path, "rb") as img_file:
                img_data = img_file.read()

            pic = Picture()
            pic.type = 3  # Front cover
            pic.mime = "image/jpeg"
            pic.desc = "Cover"
            pic.data = img_data

            # For Ogg Opus, cover art is stored as base64 in METADATA_BLOCK_PICTURE
            import base64
            audio["metadata_block_picture"] = [
                base64.b64encode(pic.write()).decode("ascii")
            ]
        except Exception as e:
            print(f"    Warning: could not embed cover art: {e}")

    audio.save()
    return True


def run(base_dir: str = "d:\\jaxify"):
    # Force utf-8 stdout for Windows
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    MUSIC_DIR = base_dir
    METADATA_FILE = os.path.join(base_dir, "tracklist.json")
    COVERS_DIR = os.path.join(base_dir, "covers")

    # Load metadata
    if not os.path.exists(METADATA_FILE):
        print(f"ERROR: {METADATA_FILE} not found. Run step1_scrape.py first.")
        sys.exit(1)

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    tracks = data["tracks"]
    print(f"Loaded metadata for {len(tracks)} tracks from playlist: {data['playlist_name']}")

    # Find downloaded files
    if not os.path.exists(MUSIC_DIR):
        print(f"ERROR: {MUSIC_DIR} not found. Run step2_download.py first.")
        sys.exit(1)

    audio_files = [
        f for f in os.listdir(MUSIC_DIR)
        if f.endswith((".opus", ".m4a", ".ogg", ".webm"))
    ]

    if not audio_files:
        print(f"ERROR: No audio files found in {MUSIC_DIR}")
        sys.exit(1)

    print(f"Found {len(audio_files)} audio files in {MUSIC_DIR}")

    # Create covers directory
    os.makedirs(COVERS_DIR, exist_ok=True)

    # Process each file
    matched = 0
    unmatched = []

    for i, filename in enumerate(audio_files, 1):
        filepath = os.path.join(MUSIC_DIR, filename)
        # Handle unicode print errors on Windows CMD
        safe_filename = filename.encode('ascii', 'replace').decode('ascii')
        print(f"\n[{i}/{len(audio_files)}] Processing: {safe_filename}")

        # Match to track metadata
        track = match_file_to_track(filename, tracks)
        if not track:
            print(f"  -> Could not match to any track. Skipping.")
            unmatched.append(filename)
            continue

        artists_str = ", ".join(track["artists"])
        print(f"  Matched to: {artists_str} - {track['title']} (Album: {track['album']})")

        # Download cover art
        cover_path = None
        if track.get("cover_url"):
            cover_filename = sanitize_filename(f"{artists_str} - {track['title']}.jpg")
            cover_path = os.path.join(COVERS_DIR, cover_filename)
            if not os.path.exists(cover_path):
                # Attempt to download
                # Fallback to the original URL scraped from the dom if the high-res hack fails
                original_url = track["cover_url"].replace("ab67616d0000b273", "ab67616d00004851")
                if download_cover(track["cover_url"], cover_path):
                    print(f"  Downloaded cover art")
                elif download_cover(original_url, cover_path):
                    print(f"  Downloaded cover art (fallback resolution)")
                else:
                    print(f"  Warning: could not download cover art from {original_url}")
                    cover_path = None
            else:
                print(f"  Cover art already cached")

        # Embed metadata
        if filepath.endswith(".opus"):
            if embed_metadata(filepath, track, cover_path):
                print(f"  Embedded metadata tags")
            else:
                print(f"  Warning: could not embed metadata")
        else:
            print(f"  Skipping metadata embed (not .opus format)")

        # Rename file to clean format: "Title.ext"
        ext = os.path.splitext(filename)[1]
        new_name = sanitize_filename(f"{track['title']}{ext}")
        new_path = os.path.join(MUSIC_DIR, new_name)

        if new_path != filepath:
            # Handle conflicts
            if os.path.exists(new_path):
                print(f"  File already exists: {new_name}")
            else:
                os.rename(filepath, new_path)
                print(f"  Renamed to: {new_name}")
        else:
            print(f"  Filename already correct")

        matched += 1

    # Summary
    print(f"\n{'='*60}")
    print(f"DONE: {matched}/{len(audio_files)} files tagged and renamed")
    if unmatched:
        print(f"\nUnmatched files ({len(unmatched)}):")
        for f in unmatched:
            safe_f = f.encode('ascii', 'replace').decode('ascii')
            print(f"  - {safe_f}")

    # Cleanup temporary files and covers folder
    import shutil
    try:
        if os.path.exists(COVERS_DIR):
            shutil.rmtree(COVERS_DIR)
        if os.path.exists(METADATA_FILE):
            os.remove(METADATA_FILE)
        txt_file = os.path.join(base_dir, "tracklist.txt")
        if os.path.exists(txt_file):
            os.remove(txt_file)
        print("\nCleanup complete: Removed temporary metadata and covers.")
    except Exception as e:
        print(f"\nWarning during cleanup: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        run()
