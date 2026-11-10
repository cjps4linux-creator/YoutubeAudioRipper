#!/usr/bin/env python3
"""
YouTube Audio Ripper - Android/Termux Edition
Tiny HTTP server + yt-dlp + FLAC conversion
"""

import http.server
import json
import re
import subprocess
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent.resolve()
MUSIC_DIR = Path.home() / "storage" / "shared" / "Music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

COOKIES_FILE = APP_DIR / "cookies.txt"
NODE_AVAILABLE = None  # cached check
HTML_UI_PATH = APP_DIR / "static" / "index.html"


def _load_html() -> str:
    if HTML_UI_PATH.exists():
        return HTML_UI_PATH.read_text(encoding="utf-8")
    return HTML_UI_FALLBACK


# ── Job tracking ───────────────────────────────────────────────────────
_jobs = {}
_lock = threading.Lock()


def _check_node():
    global NODE_AVAILABLE
    if NODE_AVAILABLE is None:
        try:
            subprocess.run(["node", "--version"], capture_output=True, timeout=3)
            NODE_AVAILABLE = True
        except Exception:
            NODE_AVAILABLE = False
    return NODE_AVAILABLE


# ── yt-dlp runner ─────────────────────────────────────────────────────
def _run_ytdlp(url: str, job_id: str, fmt: str = "flac", quality: str = "best"):
    """Run yt-dlp, convert to target format, update job progress."""
    job = _jobs[job_id]
    job["status"] = "running"
    job["started_at"] = datetime.now().isoformat()

    temp_dir = APP_DIR / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    for f in temp_dir.glob(f"ripper_{job_id}.*"):
        f.unlink(missing_ok=True)

    outtmpl = str(temp_dir / f"ripper_{job_id}.%(ext)s")

    job["_log"]("▶ Fetching metadata...")
    job["_log"](f"  Format: {fmt} | Quality: {quality}")

    # Use yt-dlp Python API (proven pattern from Windows app)
    import yt_dlp
    title = "Unknown"
    downloaded_file = None

    # First try: bestaudio/best
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
    }

    if COOKIES_FILE.exists():
        ydl_opts["cookiefile"] = str(COOKIES_FILE)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Unknown")[:120]
    except Exception as e:
        # Fallback: retry with generic best format
        job["_log"](f"  Retry with fallback format: {str(e)[:80]}")
        try:
            ydl_opts["format"] = "best"
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Unknown")[:120]
        except Exception as e2:
            job["status"] = "error"
            job["status_text"] = "Download failed"
            job["_log"](f"❌ yt-dlp error: {str(e2)[:120]}")
            return

    job["_log"](f"  Title: {title}")

    # Find downloaded file
    candidates = list(temp_dir.glob(f"ripper_{job_id}.*"))
    if candidates:
        downloaded_file = candidates[0]

    if downloaded_file is None or not downloaded_file.exists():
        job["status"] = "error"
        job["status_text"] = "Downloaded file not found"
        job["_log"]("❌ No output file found in temp dir")
        return

    job["_log"](f"✅ Downloaded: {downloaded_file.name}")
    job["progress"] = 0.6

    # Convert
    ext = fmt.lower()
    safe_title = re.sub(r'[<>:\"/\\|?*]', '', title.strip())[:80] or f"track_{job_id}"
    output_file = MUSIC_DIR / f"{safe_title}.{ext}"

    counter = 1
    while output_file.exists():
        output_file = MUSIC_DIR / f"{safe_title}_{counter}.{ext}"
        counter += 1

    job["status_text"] = f"Converting to {ext.upper()}..."
    job["progress"] = 0.7
    job["_log"](f"▶ Converting to {ext.upper()}...")

    if ext == "mp3":
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(downloaded_file),
            "-q:a", "0", "-c:a", "libmp3lame", "-ar", "44100",
            str(output_file),
        ]
    elif ext == "m4a":
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(downloaded_file),
            "-q:a", "0", "-c:a", "aac", "-b:a", "256k",
            str(output_file),
        ]
    else:
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(downloaded_file),
            "-q:a", "0", "-c:a", "flac", "-ar", "44100",
            str(output_file),
        ]

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)

    # Cleanup temp
    downloaded_file.unlink(missing_ok=True)
    for f in temp_dir.glob(f"ripper_{job_id}.*"):
        f.unlink(missing_ok=True)

    if result.returncode != 0:
        job["status"] = "error"
        job["status_text"] = "FFmpeg conversion failed"
        job["_log"](f"❌ FFmpeg error: {result.stderr[:200]}")
        return

    size_mb = output_file.stat().st_size / (1024 * 1024)
    job["progress"] = 1.0
    job["status"] = "done"
    job["status_text"] = "Complete"
    job["output_file"] = str(output_file)
    job["_log"](f"✅ Saved: {output_file.name} ({size_mb:.1f} MB)")


# ── Job API helpers ────────────────────────────────────────────────────
def _make_job(url: str, fmt: str = "flac", quality: str = "best"):
    job_id = f"{int(time.time() * 1000)}_{threading.get_native_id()}"
    logs = []

    def _log(msg):
        logs.append({"t": datetime.now().isoformat(), "m": msg})

    job = {
        "job_id": job_id,
        "url": url,
        "format": fmt,
        "quality": quality,
        "status": "queued",
        "status_text": "Queued",
        "progress": 0.0,
        "logs": logs,
        "_log": _log,
        "output_file": None,
        "started_at": None,
        "finished_at": None,
    }
    with _lock:
        _jobs[job_id] = job
    return job_id


def _start_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return
    t = threading.Thread(
        target=_run_ytdlp,
        args=(job["url"], job_id, job["format"], job["quality"]),
        daemon=True,
    )
    t.start()


# ── HTML UI ────────────────────────────────────────────────────────────
HTML_UI_FALLBACK = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>YouTube Audio Ripper</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #0f0f14;
  --surface: #1a1a24;
  --surface2: #22222e;
  --border: #2a2a38;
  --text: #e4e4f0;
  --muted: #8888a0;
  --accent: #00d4aa;
  --accent2: #00b894;
  --danger: #ff5555;
}
html, body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 15px;
  min-height: 100vh;
  overflow-x: hidden;
}
.container { max-width: 680px; margin: 0 auto; padding: 20px 16px 40px; }
.header { text-align: center; padding: 10px 0 20px; }
.header h1 { font-size: 1.5em; font-weight: 700; letter-spacing: -0.3px; }
.header .sub { color: var(--muted); font-size: 0.85em; margin-top: 2px; }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 14px;
}
label { display: block; font-size: 0.78em; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.url-area {
  width: 100%;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text);
  font-family: "SF Mono", Menlo, monospace;
  font-size: 0.85em;
  padding: 12px 14px;
  resize: vertical;
  min-height: 70px;
  outline: none;
  transition: border-color 0.2s;
}
.url-area:focus { border-color: var(--accent); }
.controls { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 12px; }
.controls select {
  width: 100%;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  font-size: 0.9em;
  padding: 10px 12px;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}
.btn {
  display: block;
  width: 100%;
  padding: 15px;
  border: none;
  border-radius: 12px;
  font-size: 1.05em;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: 0.2px;
  transition: all 0.2s;
  margin-top: 14px;
}
.btn-primary {
  background: var(--accent);
  color: #0a0a0f;
}
.btn-primary:hover { background: var(--accent2); }
.btn-primary:disabled {
  background: #333;
  color: #666;
  cursor: not-allowed;
}
.progress-wrap { margin-top: 14px; }
.progress-sample {
  width: 100%;
  height: 8px;
  background: var(--surface2);
  border-radius: 4px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 4px;
  width: 0%;
  transition: width 0.3s;
}
.status-line {
  display: flex;
  justify-content: space-between;
  font-size: 0.82em;
  color: var(--muted);
  margin-top: 6px;
}
.log-area {
  background: #0a0a10;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  font-family: "SF Mono", Menlo, monospace;
  font-size: 0.75em;
  color: #aaaacc;
  max-height: 180px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin-top: 10px;
  display: none;
}
.log-area.show { display: block; }
.section-title {
  font-size: 1em;
  font-weight: 700;
  margin: 20px 0 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--surface2);
  border-radius: 8px;
  margin-bottom: 6px;
  border: 1px solid transparent;
}
.file-item:active { border-color: var(--accent); }
.file-icon { font-size: 1.4em; flex-shrink: 0; }
.file-info { flex: 1; min-width: 0; }
.file-name {
  font-size: 0.88em;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-size { font-size: 0.75em; color: var(--muted); }
.file-actions { display: flex; gap: 6px; flex-shrink: 0; }
.icon-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1em;
  transition: all 0.15s;
}
.icon-btn:hover { background: var(--accent); color: #0a0a0f; }
.icon-btn.danger:hover { background: var(--danger); color: #fff; }
.empty-state {
  text-align: center;
  padding: 24px;
  color: var(--muted);
  font-size: 0.9em;
}
.toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: #222;
  color: #fff;
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 0.85em;
  z-index: 999;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}
.toast.show { opacity: 1; }
@media (max-width: 400px) {
  .container { padding: 12px 10px 30px; }
  .controls { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>YouTube Audio Ripper</h1>
    <div class="sub">Download &rarr; FLAC / MP3 / M4A</div>
  </div>
  <div class="card">
    <label>YouTube URL</label>
    <textarea id="urlInput" class="url-area" placeholder="Paste YouTube URL here..."></textarea>
    <div class="controls">
      <div>
        <label>Format</label>
        <select id="formatSelect">
          <option value="flac" selected>FLAC (Lossless)</option>
          <option value="mp3">MP3 (320kbps)</option>
          <option value="m4a">M4A (AAC)</option>
        </select>
      </div>
      <div>
        <label>Quality</label>
        <select id="qualitySelect">
          <option value="best" selected>Best Available</option>
          <option value="worst">Smallest File</option>
        </select>
      </div>
    </div>
    <button id="ripBtn" class="btn btn-primary">DOWNLOAD AUDIO</button>
    <div class="progress-wrap" id="progressWrap" style="display:none">
      <div class="progress-sample"><div class="progress-fill" id="progressFill"></div></div>
      <div class="status-line">
        <span id="statusText">Ready</span>
        <span id="progressPct">0%</span>
      </div>
    </div>
    <div class="log-area" id="logArea"></div>
  </div>
  <div class="section-title">Downloaded Files</div>
  <div id="filesList"></div>
</div>
<div class="toast" id="toast"></div>
<script>
const $ = (id) => document.getElementById(id);
const api = window.location.origin;
function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}
function fmtBytes(b) {
  if (b < 1024) return b + " B";
  if (b < 1048576) return (b/1024).toFixed(1) + " KB";
  return (b/1048576).toFixed(1) + " MB";
}
function renderFiles() {
  fetch(api + "/files").then(r => r.json()).then(data => {
    const el = $("filesList");
    if (!data.files.length) {
      el.innerHTML = '<div class="empty-state">No downloads yet. Paste a URL above to start.</div>';
      return;
    }
    el.innerHTML = data.files.map(f => `
      <div class="file-item">
        <div class="file-icon">&#9835;</div>
        <div class="file-info">
          <div class="file-name" title="${f.name.replace(/"/g, '&quot;')}">${f.name}</div>
          <div class="file-size">${fmtBytes(f.size)}</div>
        </div>
        <div class="file-actions">
          <a href="${f.url}" download class="icon-btn" title="Save">&#128190;</a>
          <a href="${f.url}" target="_blank" class="icon-btn" title="Play">&#9654;</a>
          <button class="icon-btn danger" onclick="deleteFile('${f.name}')" title="Delete">&#128465;</button>
        </div>
      </div>
    `).join("");
  });
}
function deleteFile(name) {
  if (!confirm("Delete " + name + "?")) return;
  fetch(api + "/delete/" + encodeURIComponent(name), {method: "POST"})
    .then(r => r.json()).then(d => {
      if (d.deleted) { toast("Deleted"); renderFiles(); }
      else toast("Error deleting");
    });
}
let currentJob = null;
let eventSource = null;
function startRip() {
  const url = $("urlInput").value.trim();
  const fmt = $("formatSelect").value;
  if (!url) { toast("Paste a URL first"); return; }
  if (currentJob && eventSource) { eventSource.close(); }
  $("ripBtn").disabled = true;
  $("ripBtn").textContent = "Processing...";
  $("progressWrap").style.display = "block";
  $("logArea").classList.add("show");
  $("logArea").textContent = "";
  fetch(api + "/rip", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({url, format: fmt, quality: $("qualitySelect").value}),
  }).then(r => r.json()).then(data => {
    if (data.error) { toast(data.error); resetBtn(); return; }
    currentJob = data.job_id;
    pollProgress(data.job_id);
  }).catch(() => { toast("Connection error"); resetBtn(); });
}
function pollProgress(jobId) {
  eventSource = new EventSource(api + "/progress/" + jobId);
  eventSource.onmessage = (e) => {
    const d = JSON.parse(e.data);
    $("progressFill").style.width = (d.progress * 100) + "%";
    $("progressPct").textContent = Math.round(d.progress * 100) + "%";
    $("statusText").textContent = d.status_text;
    const logEl = $("logArea");
    if (d.logs && d.logs.length > ((logEl.textContent || "").split("\n").length - 1)) {
      for (let i = (logEl.textContent || "").split("\n").length - 1; i < d.logs.length; i++) {
        const line = document.createElement("div");
        line.textContent = d.logs[i].m;
        logEl.appendChild(line);
      }
      logEl.scrollTop = logEl.scrollHeight;
    }
    if (d.status === "done" || d.status === "error") {
      eventSource.close();
      resetBtn();
      if (d.status === "done") { toast("Done!"); renderFiles(); }
      else { toast("Failed"); }
    }
  };
  eventSource.onerror = () => { eventSource.close(); resetBtn(); };
}
function resetBtn() {
  $("ripBtn").disabled = false;
  $("ripBtn").textContent = "DOWNLOAD AUDIO";
  currentJob = null;
}
$("ripBtn").addEventListener("click", startRip);
renderFiles();
setInterval(renderFiles, 15000);
</script>
</body>
</html>"""


# ── HTTP Handlers ───────────────────────────────────────────────────────
class RipperHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://localhost:8080")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str):
        try:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            self._send_html(_load_html())
            return

        if path == "/health":
            self._send_json({"ok": True, "music_dir": str(MUSIC_DIR)})
            return

        if path == "/files":
            files = []
            for f in sorted(MUSIC_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file() and f.suffix.lower() in (".flac", ".mp3", ".m4a"):
                    files.append({
                        "name": f.name,
                        "size": f.stat().st_size,
                        "url": f"/download/{urllib.parse.quote(f.name)}",
                    })
            self._send_json({"files": files})
            return

        if path.startswith("/download/"):
            fname = urllib.parse.unquote(path[len("/download/"):])
            # Path traversal protection: only allow basename
            if "/" in fname or "\\" in fname or ".." in fname:
                self.send_error(400, "Invalid filename")
                return
            fpath = MUSIC_DIR / fname
            if fpath.exists() and fpath.is_file():
                ct = "audio/flac" if fpath.suffix == ".flac" else "audio/mpeg" if fpath.suffix == ".mp3" else "audio/mp4"
                self._serve_file(fpath, ct)
                return
            self.send_error(404, "File not found")
            return

        if path.startswith("/progress/"):
            job_id = path[len("/progress/"):]
            job = _jobs.get(job_id)
            if not job:
                self._send_json({"error": "job not found"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "http://localhost:8080")
            self.end_headers()

            try:
                while True:
                    with _lock:
                        logs = list(job["logs"])
                    payload = {
                        "job_id": job_id,
                        "status": job["status"],
                        "status_text": job["status_text"],
                        "progress": job["progress"],
                        "logs": logs,
                        "output_file": job.get("output_file"),
                    }
                    data = f"data: {json.dumps(payload)}\n\n".encode()
                    self.wfile.write(data)
                    self.wfile.flush()
                    if job["status"] in ("done", "error"):
                        break
                    time.sleep(0.5)
            except (ConnectionResetError, BrokenPipeError):
                pass
            return

        self.send_error(404, "Not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            data = {}

        if path == "/rip":
            url = data.get("url", "").strip()
            fmt = data.get("format", "flac")
            if not url:
                self._send_json({"error": "url required"}, 400)
                return
            if "youtube.com" not in url and "youtu.be" not in url:
                self._send_json({"error": "invalid youtube url"}, 400)
                return
            job_id = _make_job(url, fmt, data.get("quality", "best"))
            _start_job(job_id)
            self._send_json({"job_id": job_id})
            return

        if path.startswith("/delete/"):
            fname = urllib.parse.unquote(path[len("/delete/"):])
            # Path traversal protection
            if "/" in fname or "\\" in fname or ".." in fname:
                self._send_json({"error": "invalid filename"}, 400)
                return
            fpath = MUSIC_DIR / fname
            if fpath.exists():
                fpath.unlink()
                self._send_json({"deleted": fname})
            else:
                self._send_json({"error": "not found"}, 404)
            return

        self.send_error(404, "Not found")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://localhost:8080")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


# ── Main ────────────────────────────────────────────────────────────────
def main():
    port = 8080
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), RipperHandler)
    print("YouTube Audio Ripper")
    print(f"   Open in browser: http://localhost:{port}")
    print(f"   Music folder:    {MUSIC_DIR}")
    print(f"   Cookies:         {'Found' if COOKIES_FILE.exists() else 'Not found (optional)'}")
    print(f"   Node.js:         {'Yes' if _check_node() else 'No (some downloads may fail)'}")
    print("   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
