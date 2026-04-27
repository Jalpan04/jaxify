"""
Master Script: Spotify Playlist Downloader

Runs the complete 3-step pipeline automatically:
  1. Scrape metadata (Playwright)
  2. Download native Opus audio (yt-dlp, multi-threaded)
  3. Embed metadata, high-res covers, and rename (Mutagen)
"""
import sys
import os

# Import the 3 steps
try:
    import step1_scrape
    import step2_download
    import step3_metadata
except ImportError as e:
    print(f"ERROR: Could not import one of the step scripts. {e}")
    sys.exit(1)


def main():
    print(r"""
=========================================================
  🎵  JAXIFY: Spotify Playlist Downloader (God Mode) 🎵  
=========================================================
""")

    if len(sys.argv) > 1:
        playlist_url = sys.argv[1]
    else:
        playlist_url = input("Enter Spotify Playlist URL: ").strip()

    if not playlist_url:
        print("ERROR: URL cannot be empty.")
        sys.exit(1)

    output_dir = "d:\\jaxify"
    music_dir = os.path.join(output_dir, "music")
    tracklist_txt = os.path.join(output_dir, "tracklist.txt")

    print("\n" + "="*50)
    print("STEP 1: Scraping Playlist Metadata (Bypassing API limits)")
    print("="*50)
    tracks = step1_scrape.scrape_playlist(playlist_url, output_dir=output_dir)
    
    if not tracks:
        print("\nPipeline failed at Step 1: No tracks extracted.")
        sys.exit(1)

    print("\n" + "="*50)
    print("STEP 2: Multi-Threaded Audio Download (Native Opus quality)")
    print("="*50)
    step2_download.download_tracks(tracklist_txt, music_dir)

    print("\n" + "="*50)
    print("STEP 3: Tagging Metadata & High-Res Album Art")
    print("="*50)
    step3_metadata.run()

    print("\n=========================================================")
    print(f"✅ ALL DONE! Your music is ready in: {music_dir}")
    print("=========================================================\n")


if __name__ == "__main__":
    main()
