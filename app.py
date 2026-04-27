import os
import sys
import queue
import threading
import subprocess
import json
from flask import Flask, render_template_string, request, jsonify, Response

app = Flask(__name__)
event_queue = queue.Queue()

# HTML & CSS Template (Premium Dark Mode + Glassmorphism)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Jaxify Downloader</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; }
        .group { margin-bottom: 15px; }
        input[type="text"] { width: 100%; padding: 8px; margin-top: 5px; box-sizing: border-box; }
        button { padding: 8px 15px; cursor: pointer; }
        #progressArea { display: none; margin-top: 20px; }
        progress { width: 100%; height: 20px; }
        #terminal { width: 100%; height: 200px; margin-top: 10px; padding: 10px; font-family: monospace; font-size: 12px; background: #f4f4f4; border: 1px solid #ccc; overflow-y: scroll; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h2>Jaxify Downloader</h2>
    
    <div class="group">
        <label>Spotify Playlist URL:</label>
        <input type="text" id="urlInput" placeholder="https://open.spotify.com/playlist/...">
    </div>

    <div class="group">
        <label>Save Location:</label>
        <div style="display: flex; gap: 10px;">
            <input type="text" id="pathInput" value="D:\\jaxify" readonly>
            <button onclick="browseFolder()">Browse...</button>
        </div>
    </div>

    <button id="downloadBtn" onclick="startDownload()">Start Download</button>

    <div id="progressArea">
        <div style="display: flex; justify-content: space-between;">
            <span id="statusText">Starting...</span>
            <span id="percentText">0%</span>
        </div>
        <progress id="progressBar" value="0" max="100"></progress>
        <div id="terminal"></div>
        <div id="errorArea" style="display: none; margin-top: 15px; padding: 10px; background: #ffe6e6; border: 1px solid #ffcccc; color: #cc0000; font-family: sans-serif; font-size: 13px; border-radius: 4px;">
            <strong>Errors Encountered:</strong>
            <ul id="errorList" style="margin: 5px 0 0 0; padding-left: 20px;"></ul>
        </div>
    </div>

    <script>
        async function browseFolder() {
            try {
                const res = await fetch('/browse');
                const data = await res.json();
                if (data.folder) document.getElementById('pathInput').value = data.folder;
            } catch (err) { console.error(err); }
        }

        function appendLog(msg) {
            const term = document.getElementById('terminal');
            term.textContent += msg + "\\n";
            term.scrollTop = term.scrollHeight;
        }

        function appendError(msg) {
            document.getElementById('errorArea').style.display = 'block';
            const ul = document.getElementById('errorList');
            const li = document.createElement('li');
            li.textContent = msg;
            ul.appendChild(li);
        }

        async function startDownload() {
            const url = document.getElementById('urlInput').value.trim();
            const path = document.getElementById('pathInput').value.trim();
            if(!url) return alert("Enter URL");

            document.getElementById('downloadBtn').disabled = true;
            document.getElementById('progressArea').style.display = 'block';
            document.getElementById('terminal').textContent = '';
            document.getElementById('progressBar').value = 0;
            document.getElementById('errorArea').style.display = 'none';
            document.getElementById('errorList').innerHTML = '';
            
            appendLog("Starting...");

            try {
                await fetch('/start', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ url, path })
                });
                
                const evtSource = new EventSource('/stream');
                evtSource.onmessage = function(e) {
                    const data = JSON.parse(e.data);
                    
                    if(data.error) appendError(data.error);
                    if(data.log) appendLog(data.log);
                    if(data.status) document.getElementById('statusText').innerText = data.status;
                    if(data.progress !== undefined && data.progress !== null) {
                        document.getElementById('progressBar').value = data.progress;
                        document.getElementById('percentText').innerText = data.progress + '%';
                    }
                    if(data.done) {
                        evtSource.close();
                        document.getElementById('downloadBtn').disabled = false;
                        document.getElementById('percentText').innerText = "100%";
                        document.getElementById('statusText').innerText = "Done";
                    }
                };
            } catch (err) {
                appendLog("Error: " + err.message);
                document.getElementById('downloadBtn').disabled = false;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/browse')
def browse():
    import tkinter as tk
    from tkinter import filedialog
    # Create invisible window to host dialog
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Select Save Location")
    root.destroy()
    return jsonify({"folder": folder_path})

def worker(url, base_path):
    def log(msg, status=None, progress=None, done=False):
        event_queue.put({"log": msg, "status": status, "progress": progress, "done": done})

    try:
        log("STEP 1: Scraping Playlist Metadata...", status="Scraping Spotify", progress=5)
        
        # We will use subprocess to avoid Playwright threading issues
        import sys
        python_exe = sys.executable
        
        # Create a tiny script to run step 1
        script1 = f"""
import sys
import os
sys.path.append(os.path.dirname(r'{base_path}'))
import step1_scrape
tracks = step1_scrape.scrape_playlist(r'{url}', output_dir=r'{base_path}')
if not tracks:
    sys.exit(1)
"""
        
        log("Starting scraper process...")
        p1 = subprocess.Popen([python_exe, "-c", script1], cwd="d:\\jaxify", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        
        for line in p1.stdout:
            log(line.strip())
            
        p1.wait()
        if p1.returncode != 0:
            log("Failed to extract tracks. Check URL.", status="Error", progress=0, done=True)
            return

        log("Successfully scraped tracks.", status="Setting up Playlist Folder", progress=20)
        
        # Read the JSON to get the playlist name and cover
        json_path = os.path.join(base_path, "tracklist.json")
        txt_path = os.path.join(base_path, "tracklist.txt")
        new_dir = base_path
        
        if os.path.exists(json_path):
            try:
                import json, re, shutil, requests
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Sanitize playlist name for folder creation
                p_name = data.get("playlist_name", "Spotify Playlist")
                safe_name = re.sub(r'[\\/*?:"<>|]', "", p_name).strip()
                if not safe_name:
                    safe_name = "Spotify Playlist"
                
                # Create the playlist folder
                new_dir = os.path.join(base_path, safe_name)
                os.makedirs(new_dir, exist_ok=True)
                
                # Move files
                new_json = os.path.join(new_dir, "tracklist.json")
                new_txt = os.path.join(new_dir, "tracklist.txt")
                if os.path.exists(new_json): os.remove(new_json)
                if os.path.exists(new_txt): os.remove(new_txt)
                shutil.move(json_path, new_json)
                shutil.move(txt_path, new_txt)
                
                # Download playlist cover
                cover_url = data.get("playlist_cover_url", "")
                if cover_url:
                    log("Downloading playlist cover...", status="Downloading Cover", progress=25)
                    try:
                        r = requests.get(cover_url, timeout=10)
                        if r.status_code == 200:
                            with open(os.path.join(new_dir, "cover.jpg"), "wb") as f:
                                f.write(r.content)
                    except Exception as e:
                        log(f"Warning: Failed to download playlist cover: {e}")
            except Exception as e:
                log(f"Warning: Could not create playlist folder: {e}")

        # Step 2
        log("STEP 2: Multi-Threaded Audio Download...", status="Downloading Audio", progress=30)
        script2 = f"""
import sys
import os
sys.path.append(r'd:\\jaxify')
import step2_download
tracklist_txt = os.path.join(r'{new_dir}', "tracklist.txt")
step2_download.download_tracks(tracklist_txt, r'{new_dir}')
"""
        p2 = subprocess.Popen([python_exe, "-c", script2], cwd="d:\\jaxify", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        import re
        for line in p2.stdout:
            line_str = line.strip()
            if "-> FAILED" in line_str or "ERROR:" in line_str:
                event_queue.put({"error": line_str})
                
            # Calculate dynamic progress for downloads: scales from 30% to 80%
            m = re.search(r'\[(\d+)/(\d+)\]', line_str)
            if m:
                cur, tot = int(m.group(1)), int(m.group(2))
                if tot > 0:
                    prog = 30 + int((cur / tot) * 50)
                    log(line_str, status="Downloading Audio", progress=prog)
                else:
                    log(line_str)
            else:
                log(line_str)
        p2.wait()

        log("Downloads complete. Starting metadata tagging...", status="Applying Metadata", progress=80)

        # Step 3
        script3 = f"""
import sys
import os
sys.path.append(r'd:\\jaxify')
import step3_metadata
step3_metadata.run(base_dir=r'{new_dir}')
"""
        p3 = subprocess.Popen([python_exe, "-c", script3], cwd="d:\\jaxify", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
        for line in p3.stdout:
            line_str = line.strip()
            if "Warning:" in line_str or "ERROR:" in line_str:
                event_queue.put({"error": line_str})
                
            # Calculate dynamic progress for tagging: scales from 80% to 99%
            m = re.search(r'\[(\d+)/(\d+)\]', line_str)
            if m:
                cur, tot = int(m.group(1)), int(m.group(2))
                if tot > 0:
                    prog = 80 + int((cur / tot) * 19)
                    log(line_str, status="Applying Metadata", progress=prog)
                else:
                    log(line_str)
            else:
                log(line_str)
        p3.wait()

        log("✅ ALL DONE! Your music is ready.", status="Complete", progress=100, done=True)

    except Exception as e:
        log(f"ERROR: {str(e)}", status="Failed", progress=0, done=True)

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    url = data.get('url')
    path = data.get('path')
    
    # Clear the queue
    while not event_queue.empty():
        event_queue.get()
        
    # Start worker
    t = threading.Thread(target=worker, args=(url, path))
    t.start()
    return jsonify({"success": True})

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            evt = event_queue.get()
            yield f"data: {json.dumps(evt)}\n\n"
            if evt.get("done"):
                break
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == '__main__':
    print("=========================================================")
    print("  Jaxify Web UI Server Running!")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("=========================================================")
    app.run(host='127.0.0.1', port=5000)
