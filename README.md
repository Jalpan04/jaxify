# Jaxify Downloader

Jaxify Downloader is a high-performance, automated Spotify playlist downloader that operates entirely without official Spotify API keys. It utilizes Playwright for metadata scraping, yt-dlp for high-quality audio extraction, and Mutagen for precision ID3/Vorbis metadata tagging. The system is managed through a lightweight Flask-based Web UI that provides real-time status updates and progress tracking.

## Core Features

- API-Free Operation: Uses automated browser interaction via Playwright to extract playlist details, bypassing the need for Spotify Developer tokens or rate limits.
- Precise Metadata Tagging: Employs a strict track-index matching system (001, 002, etc.) to ensure that every downloaded file is tagged with the exact Title, Artist, Album, and Cover Art scraped from the original playlist.
- Native Opus Audio: Configured to download 251kbps Opus streams directly from YouTube Music servers, ensuring zero transcoding loss and superior audio quality compared to standard MP3 conversions.
- Dynamic File Organization: Automatically parses the playlist name to create dedicated directories and saves the high-resolution playlist cover as cover.jpg within the folder.
- Real-Time Monitoring: Features a Server-Sent Events (SSE) powered web interface that displays a live console log, exact progress percentages, and a dedicated error reporting window.

## System Prerequisites

Before running Jaxify, ensure the following components are installed on your system:

- Python 3.8 or higher
- FFmpeg: Required by yt-dlp for audio muxing and processing. Ensure 'ffmpeg' is accessible in your system's PATH.
- Playwright: Required for the scraping engine.
- Internet Connection: Required for scraping and high-speed audio downloading.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Jalpan04/jaxify.git
   cd jaxify
   ```

2. Install the required Python packages:
   ```bash
   pip install flask playwright yt-dlp mutagen requests rapidfuzz
   ```

3. Initialize the Playwright browser engine:
   ```bash
   playwright install chromium
   ```

## Technical Architecture

The application operates as a sequential three-step pipeline orchestrated by the Flask backend:

### Step 1: Scraper (step1_scrape.py)
This module launches a headless Chromium instance to navigate the Spotify playlist URL. It automatically scrolls the page to ensure all track rows are loaded in the DOM. It extracts:
- Track Title and Artists
- Album Name
- High-resolution Album Cover URL
- Playlist Name and Playlist Cover

### Step 2: Downloader (step2_download.py)
Utilizing a multi-threaded thread pool (4 concurrent workers), this module searches YouTube Music for each track. To maintain 100% accuracy, it prepends the track's index to the filename (e.g., 005 - Song Title.opus). This prevents matching errors caused by variations in YouTube video titles.

### Step 3: Metadata Tagger (step3_metadata.py)
This final module maps the downloaded files back to the JSON metadata generated in Step 1 using the index prefix. It performs the following operations:
- Downloads and caches album cover art.
- Embeds metadata tags (Title, Artist, Album, Track Number, URL) into the Opus file.
- Injects the cover art image into the file headers.
- Cleans up the directory by removing the index prefix and temporary files, leaving only the polished audio files.

## Running the Application

1. Launch the server:
   ```bash
   python app.py
   ```
2. Access the interface:
   Open your browser and navigate to http://127.0.0.1:5000
3. Configuration:
   - Enter the public Spotify Playlist URL.
   - Choose your target save directory using the folder picker.
   - Click "Start Download" to begin the process.

## Error Handling

The application includes a robust error detection system. Any issues encountered—such as failed YouTube searches, conversion errors, or missing metadata—are captured in real-time and displayed in a red Error Window at the bottom of the Web UI. This ensures that the overall process continues even if individual tracks encounter issues.

## Disclaimer

This software is intended for personal backup and educational purposes only. Users are responsible for complying with local laws and the terms of service of the platforms involved.
