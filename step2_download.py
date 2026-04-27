"""
Step 2: Download tracks from tracklist.txt using yt-dlp.
Reads one "Artist - Title" query per line from tracklist.txt.
Downloads highest quality audio as native .opus (251kbps VBR -- zero transcoding loss).
"""
import subprocess
import sys
import os
import concurrent.futures
import threading

# Thread-safe counters
succeeded = 0
failed = []
lock = threading.Lock()


def download_single_track(i: int, total: int, query: str, output_dir: str):
    global succeeded, failed
    
    print(f"[{i}/{total}] Starting: {query}")
    output_template = os.path.join(output_dir, f"{i:03d} - %(title)s.%(ext)s")

    command = [
        "yt-dlp",
        f"ytsearch1:{query} Audio", # Adding "Audio" helps avoid music videos with skits
        "-f", "ba",
        "-x",
        "--audio-format", "opus",
        "--audio-quality", "0",
        "--add-metadata",
        "--embed-thumbnail",
        "--no-playlist",
        "-o", output_template,
    ]

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 or ("Destination:" in result.stderr and ".opus" in result.stderr):
                with lock:
                    succeeded += 1
                print(f"  -> OK [{i}/{total}]: {query}")
                return
            else:
                if attempt == max_retries:
                    with lock:
                        failed.append(query)
                    print(f"  -> FAILED [{i}/{total}]: {result.stderr[-200:] if result.stderr else 'unknown error'}")
                else:
                    print(f"  -> RETRY {attempt}/{max_retries} [{i}/{total}]: {query}")
        except subprocess.TimeoutExpired:
            if attempt == max_retries:
                with lock:
                    failed.append(query)
                print(f"  -> TIMEOUT [{i}/{total}]: {query}")
        except Exception as e:
            if attempt == max_retries:
                with lock:
                    failed.append(query)
                print(f"  -> ERROR [{i}/{total}]: {e}")


def download_tracks(tracklist_file: str, output_dir: str):
    global succeeded, failed
    
    if not os.path.exists(tracklist_file):
        print(f"ERROR: {tracklist_file} not found. Run step1_scrape.py first.")
        sys.exit(1)

    with open(tracklist_file, "r", encoding="utf-8") as f:
        tracks = [line.strip() for line in f if line.strip()]

    if not tracks:
        print("ERROR: tracklist.txt is empty.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print(f"Downloading {len(tracks)} tracks into: {output_dir}")
    print(f"Format: Opus (~251kbps VBR) -- native YouTube quality, zero transcoding loss")
    print(f"Optimization: Multi-threaded (4 parallel downloads) with auto-retry.\n")

    succeeded = 0
    failed = []

    # Use ThreadPoolExecutor to download multiple tracks at once
    max_workers = 4
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, query in enumerate(tracks):
            futures.append(
                executor.submit(download_single_track, i + 1, len(tracks), query, output_dir)
            )
        
        # Wait for all to complete
        concurrent.futures.wait(futures)

    print(f"\n{'='*50}")
    print(f"DONE: {succeeded}/{len(tracks)} downloaded successfully")
    if failed:
        print(f"\nFailed tracks ({len(failed)}):")
        for t in failed:
            print(f"  - {t}")


if __name__ == "__main__":
    tracklist = "d:\\jaxify\\tracklist.txt"
    output = "d:\\jaxify\\music"
    download_tracks(tracklist, output)
