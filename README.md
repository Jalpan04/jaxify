# Jaxify Downloader

Jaxify Downloader is an automated, API-free Spotify playlist downloader accessible via a clean, minimalist local Web UI. It seamlessly orchestrates scraping, downloading, and high-quality metadata tagging, converting Spotify playlists into perfectly organized local music libraries.

## ✨ Features

- **No API Keys Required:** Uses Playwright to stealth-scrape playlist metadata and high-resolution cover art directly from the web.
- **Minimalist Web UI:** A lightweight Flask server provides a clean graphical interface with real-time SSE (Server-Sent Events) progress bars and operational logs.
- **Smart Folder Organization:** Automatically detects the exact playlist name and creates a dedicated folder, saving the playlist's master cover art inside.
- **Native High-Quality Audio:** Multi-threaded integration with `yt-dlp` extracts pure Opus audio streams directly from YouTube Music, completely bypassing lossy format transcoding.
- **Precision ID3 Tagging:** Uses exact index matching to tag each downloaded `.opus` file with the correct Title, Artist, Album, and embedded Cover Art using Mutagen.
- **Live Error Handling:** Real-time error box captures and displays dropped tracks, skipped downloads, or conversion failures during the process without crashing.

## 🚀 Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Jalpan04/jaxify.git
   cd jaxify
   ```

2. **Install Dependencies:**
   Ensure you have Python 3.8+ installed.
   ```bash
   pip install flask playwright yt-dlp mutagen requests
   ```

3. **Install Playwright Browsers:**
   Jaxify requires Chromium to scrape Spotify locally.
   ```bash
   playwright install chromium
   ```

4. **Install FFmpeg:**
   `yt-dlp` requires FFmpeg for audio extraction and muxing. Make sure `ffmpeg` is installed and added to your system's PATH.

## 💻 Usage

1. **Start the Web Server:**
   ```bash
   python app.py
   ```
2. **Open the UI:**
   Navigate to `http://127.0.0.1:5000` in your web browser.
3. **Download:**
   - Paste a public Spotify Playlist URL.
   - Select your target Save Location.
   - Click "Start Download" and watch the magic happen in real-time!

## ⚙️ How It Works (The 3-Step Pipeline)

1. **`step1_scrape.py`**: A headless Chromium browser opens the Spotify URL, auto-scrolls to load all tracks, and extracts exact artist, title, and cover art data into a local `tracklist.json` and query list.
2. **`step2_download.py`**: A multi-threaded worker spawns parallel `yt-dlp` instances. It prepends an exact track index number (`001 - ...`) to filenames to ensure zero fuzzy-matching errors.
3. **`step3_metadata.py`**: Reads the numbered files, perfectly maps them back to the scraped JSON metadata, embeds the high-res cover art, strips the index numbers, and leaves beautifully named `Song Title.opus` files ready for your music player.

## ⚠️ Disclaimer

This tool is created for educational purposes and personal backups only. Do not use this tool to download copyrighted material without permission.
