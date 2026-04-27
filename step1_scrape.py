"""
Step 1: Scrape rich metadata from a Spotify playlist URL.
Uses Playwright to render the page like a real browser.

Outputs:
  - tracklist.json  (rich metadata: title, artists, album, cover art, duration, track#)
  - tracklist.txt   (simple "Artist - Title" list for step2_download.py)

ONLY scrapes real playlist tracks -- ignores Spotify's "Recommended" section.
"""
import sys
import time
import json
import re

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    print("Run: pip install playwright && python -m playwright install chromium")
    sys.exit(1)


def scrape_playlist(playlist_url: str, output_dir: str = "d:\\jaxify"):
    print(f"Scraping playlist: {playlist_url}")
    tracks = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/125.0.0.0 Safari/537.36"
        )

        print("Loading page...")
        page.goto(playlist_url, wait_until="networkidle", timeout=30000)

        # Dismiss cookie banner if present
        try:
            page.click('button:has-text("Accept")', timeout=3000)
            time.sleep(1)
        except Exception:
            pass

        # Wait for the tracklist container
        try:
            page.wait_for_selector('[data-testid="playlist-tracklist"]', timeout=15000)
        except Exception:
            print("ERROR: Could not find the playlist tracklist on the page.")
            print("Make sure the playlist is public and the URL is correct.")
            page.screenshot(path=f"{output_dir}\\debug_screenshot.png")
            print(f"Saved debug screenshot to {output_dir}\\debug_screenshot.png")
            browser.close()
            return []

        # Get expected track count
        expected_count = None
        try:
            count_el = page.locator('span:has-text("song")').first
            if count_el.count() > 0:
                count_text = count_el.inner_text().strip()
                expected_count = int(count_text.split()[0])
                print(f"Playlist says: {count_text}")
        except Exception:
            pass

        # Get playlist name and cover
        playlist_name = "Unknown Playlist"
        playlist_cover_url = ""
        try:
            # Try to get it from the document title first
            doc_title = page.title()
            if doc_title and " - playlist by " in doc_title:
                playlist_name = doc_title.split(" - playlist by ")[0].strip()
            elif doc_title and " | Spotify" in doc_title:
                playlist_name = doc_title.split(" | Spotify")[0].strip()
            else:
                # The h1 on the page is the playlist name
                h1 = page.locator("h1").first
                if h1.count() > 0:
                    playlist_name = h1.inner_text().strip()
            
            print(f"Playlist name: {playlist_name}")
            
            # The playlist cover
            img = page.locator('img[data-testid="entity-image"]').first
            if img.count() > 0:
                playlist_cover_url = img.get_attribute("src") or ""
        except Exception:
            pass

        # Scroll and extract simultaneously to handle DOM virtualization
        print("Scrolling and extracting tracks...")
        seen_urls = set()
        previous_count = 0
        stale_rounds = 0

        # Use PageDown to scroll incrementally so we don't skip tracks that unload
        for _ in range(200):
            container = page.locator('[data-testid="playlist-tracklist"]')
            rows = container.locator('div[data-testid="tracklist-row"]')
            total_in_view = rows.count()

            for i in range(total_in_view):
                try:
                    row = rows.nth(i)
                    track = {}

                    # Track title
                    title_el = row.locator('a[href*="/track/"]').first
                    if title_el.count() == 0:
                        continue
                    track_url = "https://open.spotify.com" + title_el.get_attribute("href")
                    
                    if track_url in seen_urls:
                        continue

                    track["title"] = title_el.inner_text().strip()
                    track["spotify_track_url"] = track_url

                    # Artist(s)
                    artist_els = row.locator('a[href*="/artist/"]')
                    if artist_els.count() == 0:
                        continue
                    track["artists"] = [
                        artist_els.nth(j).inner_text().strip()
                        for j in range(artist_els.count())
                    ]

                    # Album
                    album_els = row.locator('a[href*="/album/"]')
                    if album_els.count() > 0:
                        track["album"] = album_els.first.inner_text().strip()
                    else:
                        track["album"] = ""

                    # Cover art URL (album thumbnail)
                    img_els = row.locator("img")
                    if img_els.count() > 0:
                        cover_url = img_els.first.get_attribute("src")
                        # Upgrade to highest resolution
                        if cover_url and "ab67616d" in cover_url:
                            cover_url = cover_url.replace("00004851", "0000b273")
                            cover_url = cover_url.replace("00001e02", "0000b273")
                        track["cover_url"] = cover_url
                    else:
                        track["cover_url"] = ""

                    # Duration and track number from full row text
                    row_text = row.inner_text().strip()
                    dur_match = re.search(r"(\d+:\d{2})$", row_text)
                    track["duration"] = dur_match.group(1) if dur_match else ""

                    num_match = re.match(r"^(\d+)\n", row_text)
                    track["track_number"] = int(num_match.group(1)) if num_match else len(tracks) + 1

                    # Build the search query for yt-dlp
                    artists_str = ", ".join(track["artists"])
                    track["search_query"] = f"{artists_str} - {track['title']}"

                    seen_urls.add(track_url)
                    tracks.append(track)
                    print(f"  [{len(tracks)}] {track['search_query']}")

                except Exception:
                    continue

            # Check if we have all expected tracks
            if expected_count and len(tracks) >= expected_count:
                break

            # Check if stuck
            if len(tracks) == previous_count:
                stale_rounds += 1
                if stale_rounds >= 8:
                    break
            else:
                stale_rounds = 0
                previous_count = len(tracks)

            # Scroll the last visible row into view to trigger lazy loading
            if total_in_view > 0:
                try:
                    rows.nth(total_in_view - 1).scroll_into_view_if_needed()
                except Exception:
                    pass

            time.sleep(1.0)

        print(f"\nFound total {len(tracks)} tracks.")

    # Save outputs
    if tracks:
        # Rich JSON metadata
        output_data = {
            "playlist_name": playlist_name,
            "playlist_cover_url": playlist_cover_url,
            "playlist_url": playlist_url,
            "total_tracks": len(tracks),
            "tracks": tracks,
        }
        json_path = f"{output_dir}\\tracklist.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved rich metadata to {json_path}")

        # Simple text list for step2
        txt_path = f"{output_dir}\\tracklist.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for t in tracks:
                f.write(t["search_query"] + "\n")
        print(f"Saved search queries to {txt_path}")
    else:
        print("\nNo tracks found.")

    return tracks


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter Spotify Playlist URL: ").strip()

    scrape_playlist(url)
