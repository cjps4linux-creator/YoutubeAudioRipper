#!/usr/bin/env python3
"""
YouTube Audio Ripper - Production-Grade UX-Enhanced Version (Phase 8)
Paste a YouTube link, get a FLAC named after the track. Local GUI, no account needed.

Phase 1 — Stabilise: class name fix, logging module, FFmpeg pre-flight check,
URL validation regex, sanitised filenames, CI test isolation, path traversal
protection.

Phase 2 — Harden: cookies-from-browser support, resume partial downloads,
deduplication registry, metadata embedding, retry with exponential backoff.

Phase 3 — Polish: settings/preferences UI, per-file batch progress,
file management (rename/delete/open/play), auto-updater, PyInstaller spec,
installer roadmap.

Phase 4 — Scale: parallel downloads (thread pool), playlist support,
cover art extraction, bandwidth limiting, proxy support.

Phase 5 — Release & Distribution: unit tests, GitHub Actions CI,
Inno Setup installer script, system tray support.

Phase 6 — Testing & CI: integration tests, performance benchmark,
coverage reporting, standalone rip_single_url() helper.

Phase 7 — UX Enhancements: download history UI, dark/light theme toggle,
keyboard shortcuts, portable mode, auto-updater client, enhanced tray.

Phase 8 — Documentation & Operations: user manual, troubleshooting guide,
release notes template, code signing docs, auto-download updates,
cross-platform CI builds.
"""

import concurrent.futures
import csv
import datetime as _dt
import json
import logging
import logging.handlers
import os
import platform
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

import customtkinter as ctk
from tkinter import simpledialog, messagebox

# ── Configuration ──────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent.resolve()
SETTINGS_FILE = APP_DIR / "settings.json"
LOG_FILE = APP_DIR / "youtube_ripper.log"
DOWNLOADS_REGISTRY = APP_DIR / "downloads.json"
DEFAULT_OUTPUT_DIR = APP_DIR / "ripped_music"

MAX_URL_LENGTH = 2048
MAX_URLS_PER_BATCH = 50
MAX_DOWNLOAD_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_WORKERS = 3

# ── Portable mode ──────────────────────────────────────────────────────
# If a file named ``portable`` (no extension) exists next to the EXE/script,
# all state (settings, registry, history, logs) is written to the app
# directory instead of AppData. This allows running from a USB stick.
PORTABLE_FILE = APP_DIR / "portable"
PORTABLE_MODE = PORTABLE_FILE.exists()

if PORTABLE_MODE:
    # All state lives next to the executable
    SETTINGS_FILE = APP_DIR / "settings.json"
    LOG_FILE = APP_DIR / "youtube_ripper.log"
    DOWNLOADS_REGISTRY = APP_DIR / "downloads.json"
    HISTORY_FILE = APP_DIR / "download_history.json"
else:
    SETTINGS_FILE = APP_DIR / "settings.json"
    LOG_FILE = APP_DIR / "youtube_ripper.log"
    DOWNLOADS_REGISTRY = APP_DIR / "downloads.json"
    HISTORY_FILE = APP_DIR / "download_history.json"

GITHUB_REPO = "cjps4linux-creator/youtube-audio-ripper"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "2.3.0"

YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]{11}(?:[?&].*)?$",
    re.IGNORECASE,
)

PLAYLIST_URL_RE = re.compile(
    r"^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+(?:[?&].*)?$",
    re.IGNORECASE,
)

SUPPORTED_FORMATS = ["FLAC", "MP3", "M4A"]
SUPPORTED_BROWSERS = [
    "None",
    "Chrome",
    "Firefox",
    "Edge",
    "Safari",
    "Opera",
    "Brave",
]

DEFAULT_SETTINGS = {
    "output_dir": str(DEFAULT_OUTPUT_DIR),
    "default_format": "FLAC",
    "cookies_browser": "None",
    "ai_sensitivity_threshold": 0.7,
    "max_workers": DEFAULT_MAX_WORKERS,
    "bandwidth_kbps": 0,  # 0 = unlimited
    "proxy_url": "",
    "embed_cover_art": True,
    "playlist_mode": False,
    "theme": "dark",  # "dark", "light", "system"
    "show_history_panel": False,
    "check_updates_on_startup": True,
    "skip_update_version": "",  # version to skip
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ── Logging ────────────────────────────────────────────────────────────
logger = logging.getLogger("youtube_ripper")
logger.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
logger.addHandler(_console_handler)

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logger.addHandler(_file_handler)


# ── Pre-flight checks ──────────────────────────────────────────────────
def _check_ffmpeg() -> bool:
    """Return True if ffmpeg is available on PATH or bundled next to the EXE."""
    # 1. Check PATH first
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # 2. Check bundled ffmpeg.exe next to the executable (PyInstaller dist folder)
    try:
        exe_dir = Path(sys.executable).resolve().parent
        bundled = exe_dir / "ffmpeg.exe"
        if bundled.exists():
            result = subprocess.run(
                [str(bundled), "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    # 3. Check _MEIPASS (PyInstaller onefile temp extraction dir)
    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass) / "ffmpeg.exe"
            if bundled.exists():
                result = subprocess.run(
                    [str(bundled), "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    return False


def _check_yt_dlp() -> bool:
    """Return True if yt-dlp Python package is importable."""
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


# ── Validation helpers ─────────────────────────────────────────────────
def validate_youtube_url(url: str) -> tuple[bool, str | None]:
    """Validate a single YouTube URL. Returns (is_valid, error_or_none)."""
    if not url or not url.strip():
        return False, "URL is empty."
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        return False, f"URL too long ({len(url)} chars, max {MAX_URL_LENGTH})."
    if not YOUTUBE_URL_RE.match(url):
        return False, "Not a valid YouTube video URL."
    return True, None


def validate_urls(urls: list[str]) -> tuple[list[str], list[str]]:
    """Validate a list of URLs. Returns (valid_urls, error_messages)."""
    if len(urls) > MAX_URLS_PER_BATCH:
        return [], [f"Too many URLs ({len(urls)}, max {MAX_URLS_PER_BATCH})."]
    valid: list[str] = []
    errors: list[str] = []
    for url in urls:
        ok, err = validate_youtube_url(url)
        if ok:
            valid.append(url)
        else:
            errors.append(err or "Invalid URL.")
    return valid, errors


def sanitize_filename(title: str) -> str:
    """Convert YouTube title to a safe filesystem filename."""
    if not title:
        return "Unknown_Track"
    invalid = '<>:\"/\\|?*'
    for char in invalid:
        title = title.replace(char, "")
    title = re.sub(r"\s+", " ", title).strip()
    title = title[:80]
    return title if title else "Unknown_Track"


# ── Settings ───────────────────────────────────────────────────────────
def load_settings() -> dict:
    """Load settings from settings.json, falling back to defaults."""
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    """Persist settings to settings.json."""
    try:
        SETTINGS_FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not save settings: %s", exc)


# ── Downloads registry (deduplication) ─────────────────────────────────
def load_registry() -> dict[str, str]:
    """Load the URL -> filename registry from disk."""
    try:
        data = json.loads(DOWNLOADS_REGISTRY.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {}


def save_registry(registry: dict[str, str]) -> None:
    """Persist the URL -> filename registry to disk."""
    try:
        DOWNLOADS_REGISTRY.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not save downloads registry: %s", exc)


def is_already_downloaded(url: str, registry: dict[str, str]) -> str | None:
    """Return existing filename if URL was already downloaded and file exists."""
    filename = registry.get(url)
    if filename:
        existing_path = Path(load_settings().get("output_dir", str(DEFAULT_OUTPUT_DIR))) / filename
        if existing_path.exists():
            return filename
    return None


# ── Download history ───────────────────────────────────────────────────


def load_history() -> list[dict]:
    """Load the download history list from disk."""
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return []


def save_history(history: list[dict]) -> None:
    """Persist the download history to disk (keeps last 500 entries)."""
    try:
        # Keep only the most recent 500 entries
        trimmed = history[-500:]
        HISTORY_FILE.write_text(
            json.dumps(trimmed, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not save download history: %s", exc)


def add_history_entry(url: str, title: str, filename: str, format: str, size_mb: float) -> None:
    """Append a completed download to the history."""
    history = load_history()
    entry = {
        "url": url,
        "title": title,
        "filename": filename,
        "format": format,
        "size_mb": round(size_mb, 2),
        "downloaded_at": _dt.datetime.now().isoformat(),
    }
    history.append(entry)
    save_history(history)


def export_history_csv(path: Path) -> None:
    """Export download history to a CSV file."""
    history = load_history()
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["downloaded_at", "title", "url", "filename", "format", "size_mb"],
        )
        writer.writeheader()
        for entry in history:
            writer.writerow(entry)


# ── Retry with exponential backoff ─────────────────────────────────────
def retry_download(func, *args, max_retries: int = MAX_DOWNLOAD_RETRIES,
                   base_delay: float = RETRY_BASE_DELAY, **kwargs):
    """Execute func with exponential backoff retries. Delays: base, base*2, base*4..."""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    "Download attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt, max_retries, exc, delay,
                )
                time.sleep(delay)
            else:
                logger.error("Download failed after %d attempts: %s", max_retries, exc)
    raise last_error  # type: ignore[misc]


# ── Auto-updater ───────────────────────────────────────────────────────
def check_for_updates() -> dict | None:
    """Check GitHub releases for a newer version. Returns release info or None."""
    try:
        req = urllib.request.Request(
            GITHUB_API_LATEST,
            headers={"User-Agent": "youtube-audio-ripper-updater"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "").lstrip("v")
        if not tag:
            return None
        cur = [int(x) for x in CURRENT_VERSION.split(".")]
        new = [int(x) for x in tag.split(".")]
        if new > cur:
            return {
                "version": tag,
                "url": data.get("html_url", ""),
                "body": data.get("body", ""),
            }
    except Exception as exc:
        logger.warning("Auto-update check failed: %s", exc)
    return None


# ── Standalone download helper (for integration tests + CLI use) ───────


def rip_single_url(url: str, output_dir: Path, format: str = "FLAC") -> dict:
    """Download, convert, and embed metadata + cover art for a single URL.

    Returns a dict:
        {"ok": bool, "file": Path|None, "error": str|None, "size_mb": float}
    """
    import yt_dlp

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Deduplication check ───────────────────────────────────────────
    registry = load_registry()
    existing = is_already_downloaded(url, registry)
    if existing:
        return {"ok": True, "file": output_dir / existing, "error": None, "size_mb": 0.0,
                "skipped": True}

    temp_dir = Path(tempfile.gettempdir())
    tid = threading.get_ident()
    temp_file = temp_dir / f"ripper_standalone_{tid}.%(ext)s"
    thumbnail_file = temp_dir / f"ripper_standalone_thumb_{tid}.%(ext)s"

    for f in temp_dir.glob(f"ripper_standalone_{tid}.*"):
        f.unlink(missing_ok=True)
    for f in temp_dir.glob(f"ripper_standalone_thumb_{tid}.*"):
        f.unlink(missing_ok=True)

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(temp_file),
        "quiet": True,
        "no_warnings": True,
        "continuedl": True,
        "noplaylist": True,
    }

    def _do_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "Unknown")
            artist = info.get("artist") or info.get("uploader") or "Unknown Artist"
            album = info.get("album") or ""
            track = info.get("track") or ""
            thumbnail = info.get("thumbnail") or ""
            return info, title, artist, album, track, thumbnail

    try:
        info, title, artist, album, track, thumbnail_url = retry_download(_do_download)
    except Exception as exc:
        logger.error("Download failed for %s: %s", url, exc)
        return {"ok": False, "file": None, "error": str(exc), "size_mb": 0.0}

    downloaded = None
    for f in temp_dir.glob(f"ripper_standalone_{tid}.*"):
        if f.exists():
            downloaded = f
            break
    if not downloaded:
        return {"ok": False, "file": None, "error": "No output file found", "size_mb": 0.0}

    thumbnail_path = None
    for f in temp_dir.glob(f"ripper_standalone_thumb_{tid}.*"):
        if f.exists():
            thumbnail_path = f
            break

    safe_title = sanitize_filename(title)
    output_file = output_dir / f"{safe_title}.{format.lower()}"

    counter = 1
    original_output = output_file
    while output_file.exists():
        output_file = output_dir / f"{original_output.stem}_{counter}.{format.lower()}"
        counter += 1

    ffmpeg_cmd = ["ffmpeg", "-y", "-i", str(downloaded)]
    thumb_input = None
    if thumbnail_path and thumbnail_path.exists():
        thumb_input = str(thumbnail_path)
        ffmpeg_cmd.extend(["-i", thumb_input])

    if format == "FLAC":
        ffmpeg_cmd.extend(["-q:a", "0", "-c:a", "flac", "-ar", "44100"])
    elif format == "MP3":
        ffmpeg_cmd.extend(["-q:a", "0", "-c:a", "libmp3lame", "-ar", "44100"])
    elif format == "M4A":
        ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "256k", "-ar", "44100"])

    ffmpeg_cmd.extend(["-metadata", f"title={title}", "-metadata", f"artist={artist}"])
    if album:
        ffmpeg_cmd.extend(["-metadata", f"album={album}"])
    if track:
        ffmpeg_cmd.extend(["-metadata", f"track={track}"])

    if thumb_input:
        ffmpeg_cmd.extend(["-map", "0", "-map", "1", "-c", "copy", "-c:v", "mjpeg",
                           "-disposition:v:0", "attached_pic"])

    ffmpeg_cmd.append(str(output_file))

    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"ok": False, "file": None, "error": result.stderr[:500], "size_mb": 0.0}

    downloaded.unlink(missing_ok=True)
    if thumb_input:
        Path(thumb_input).unlink(missing_ok=True)

    registry[url] = output_file.name
    save_registry(registry)

    size_mb = output_file.stat().st_size / (1024 * 1024)
    add_history_entry(url, title, output_file.name, format, size_mb)
    logger.info("Saved %s (%.1f MB) from %s", output_file.name, size_mb, url)
    return {"ok": True, "file": output_file, "error": None, "size_mb": size_mb}


def _fetch_playlist_entries(playlist_url: str) -> list[dict]:
    """Fetch playlist video entries without downloading.

    Returns a list of dicts with keys: index, title, url, id.
    """
    import yt_dlp

    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    entries = info.get("entries", []) or []
    results = []
    for i, entry in enumerate(entries):
        if not entry:
            continue
        vid = entry.get("id", "")
        results.append({
            "index": i,
            "title": entry.get("title", f"Video {i+1}"),
            "url": entry.get("url", f"https://www.youtube.com/watch?v={vid}"),
            "id": vid,
        })
    return results


# ── Playlist dialog ────────────────────────────────────────────────────
class PlaylistDialog(simpledialog.Dialog):
    """Modal dialog listing playlist videos for selection."""

    def __init__(self, parent, title, entries):
        self.entries = entries  # list of (index, title, url)
        self.selected = []
        super().__init__(parent, title)

    def body(self, master):
        self.result = None
        ctk.CTkLabel(
            master, text="Select videos to download:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(master, height=300, width=560)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.checks = {}
        for idx, title, url in self.entries:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(
                self.scroll, text=f"{idx + 1}. {title[:70]}",
                variable=var, font=ctk.CTkFont(size=10),
            )
            cb.pack(anchor="w", padx=5, pady=2)
            self.checks[idx] = (var, url)

        btn_frame = ctk.CTkFrame(master, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(btn_frame, text="Select All", command=self._select_all).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Select None", command=self._select_none).pack(side="left", padx=5)
        return master

    def _select_all(self):
        for var, _ in self.checks.values():
            var.set(True)

    def _select_none(self):
        for var, _ in self.checks.values():
            var.set(False)

    def apply(self):
        self.selected = [url for var, url in self.checks.values() if var.get()]


# ── Application ────────────────────────────────────────────────────────
class YouTubeRipperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Audio Ripper")
        self.geometry("900x820")

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 900) // 2
        y = (self.winfo_screenheight() - 820) // 2
        self.geometry(f"+{x}+{y}")

        self.settings = load_settings()
        self.downloads_registry = load_registry()
        self.download_history = load_history()
        self.processing = False
        self.current_job = 0
        self.total_jobs = 0
        self.completed_jobs = 0
        self._stop_requested = False
        self._tray_icon = None
        self._build_ui()

        # Apply saved theme
        theme = self.settings.get("theme", "dark")
        ctk.set_appearance_mode(theme)

        # Show history panel if setting enabled
        if self.settings.get("show_history_panel", False):
            self.after(200, self._toggle_history_panel)

        # Keyboard shortcuts
        self.bind_all("<Control-v>", lambda e: self._paste_urls())
        self.bind_all("<Control-Return>", lambda e: self._start_rip())
        self.bind_all("<Control-s>", lambda e: self._save_settings())
        self.bind_all("<Control-o>", lambda e: self._browse_output_dir())
        self.bind_all("<Escape>", lambda e: self._request_stop() if self.processing else None)
        self.bind_all("<Control-h>", lambda e: self._toggle_history_panel())
        self.bind_all("<F1>", lambda e: self._show_about())

        # Show portable mode notice if applicable
        if PORTABLE_MODE:
            self._gui_log("💾 Portable mode detected — all state stored locally")

        # Run pre-flight + update check after UI is built
        self.after(100, self._pre_flight_check)
        if self.settings.get("check_updates_on_startup", True):
            skip_ver = self.settings.get("skip_update_version", "")
            self.after(1500, lambda: self._check_updates_prompt(skip_ver))
        else:
            self.after(1500, self._check_updates)

    # ── UI Construction ──────────────────────────────────────────────
    def _build_ui(self):
        # Main frame with scrollable content
        self.main = ctk.CTkScrollableFrame(self)
        self.main.pack(fill="both", expand=True, padx=20, pady=20)

        # ── Header ─────────────────────────────────────────────────
        ctk.CTkLabel(
            self.main, text="🎵 YouTube Audio Ripper",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(0, 5))
        ctk.CTkLabel(
            self.main, text=f"v{CURRENT_VERSION}  •  Download → FLAC/MP3/M4A with metadata & cover art",
            font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(pady=(0, 15))

        # ── URL Input ──────────────────────────────────────────────
        ctk.CTkLabel(
            self.main, text="YouTube URLs (one per line):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", pady=(0, 5))

        self.url_text = ctk.CTkTextbox(
            self.main, height=80,
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.url_text.pack(fill="x", pady=(0, 10))
        self.url_text.insert(
            "0.0", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        self.hint_label = ctk.CTkLabel(
            self.main,
            text="Paste one or more YouTube video URLs (one per line). Max 50 per batch.",
            font=ctk.CTkFont(size=9), text_color="gray",
        )
        self.hint_label.pack(anchor="w", pady=(0, 10))

        # ── Options Row 1 ──────────────────────────────────────────
        opts1 = ctk.CTkFrame(self.main, fg_color="transparent")
        opts1.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(opts1, text="Format:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.format_var = ctk.StringVar(value=self.settings.get("default_format", "FLAC"))
        self.format_dropdown = ctk.CTkOptionMenu(
            opts1, values=SUPPORTED_FORMATS, variable=self.format_var,
            width=110, font=ctk.CTkFont(size=11),
        )
        self.format_dropdown.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(opts1, text="Auth:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.browser_var = ctk.StringVar(value=self.settings.get("cookies_browser", "None"))
        self.browser_dropdown = ctk.CTkOptionMenu(
            opts1, values=SUPPORTED_BROWSERS, variable=self.browser_var,
            width=110, font=ctk.CTkFont(size=11),
        )
        self.browser_dropdown.pack(side="left", padx=(0, 20))

        self.playlist_var = ctk.BooleanVar(value=self.settings.get("playlist_mode", False))
        self.playlist_checkbox = ctk.CTkCheckBox(
            opts1, text="Playlist mode", variable=self.playlist_var,
            font=ctk.CTkFont(size=11),
        )
        self.playlist_checkbox.pack(side="left")

        # ── Options Row 2 ──────────────────────────────────────────
        opts2 = ctk.CTkFrame(self.main, fg_color="transparent")
        opts2.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(opts2, text="Max concurrent:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.workers_var = ctk.StringVar(value=str(self.settings.get("max_workers", DEFAULT_MAX_WORKERS)))
        self.workers_entry = ctk.CTkEntry(opts2, textvariable=self.workers_var, width=60, font=ctk.CTkFont(size=11))
        self.workers_entry.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(opts2, text="Bandwidth cap (KB/s):", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.bandwidth_var = ctk.StringVar(value=str(self.settings.get("bandwidth_kbps", 0)))
        self.bandwidth_entry = ctk.CTkEntry(opts2, textvariable=self.bandwidth_var, width=70, font=ctk.CTkFont(size=11))
        self.bandwidth_entry.pack(side="left", padx=(0, 20))

        ctk.CTkLabel(opts2, text="Proxy:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 6))
        self.proxy_var = ctk.StringVar(value=self.settings.get("proxy_url", ""))
        self.proxy_entry = ctk.CTkEntry(opts2, textvariable=self.proxy_var, width=160, font=ctk.CTkFont(size=11),
                                        placeholder_text="http://host:port or socks5://host:port")
        self.proxy_entry.pack(side="left")

        self.cover_art_var = ctk.BooleanVar(value=self.settings.get("embed_cover_art", True))
        self.cover_art_checkbox = ctk.CTkCheckBox(
            opts2, text="Embed cover art", variable=self.cover_art_var,
            font=ctk.CTkFont(size=11),
        )
        self.cover_art_checkbox.pack(side="left", padx=(20, 0))

        # ── Start / Stop Buttons ───────────────────────────────────
        btn_row = ctk.CTkFrame(self.main, fg_color="transparent")
        btn_row.pack(fill="x", pady=10)

        self.start_btn = ctk.CTkButton(
            btn_row, text="🎵 START RIPPING 🎵",
            font=ctk.CTkFont(size=18, weight="bold"),
            height=50, fg_color="green", hover_color="darkgreen",
            command=self._start_rip,
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = ctk.CTkButton(
            btn_row, text="⏹ STOP",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50, fg_color="red", hover_color="darkred",
            command=self._request_stop,
            state="disabled",
        )
        self.stop_btn.pack(side="left")

        # ── Batch Progress ─────────────────────────────────────────
        self.batch_frame = ctk.CTkFrame(self.main)
        self.batch_frame.pack(fill="x", pady=(0, 10))
        self.batch_frame.pack_forget()

        self.batch_label = ctk.CTkLabel(
            self.batch_frame, text="Batch Progress", font=ctk.CTkFont(size=12, weight="bold")
        )
        self.batch_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.file_progress = ctk.CTkProgressBar(self.batch_frame)
        self.file_progress.pack(fill="x", padx=10, pady=(0, 5))
        self.file_progress.set(0)

        self.file_label = ctk.CTkLabel(
            self.batch_frame, text="Idle", font=ctk.CTkFont(size=10)
        )
        self.file_label.pack(anchor="w", padx=10, pady=(0, 5))

        self.batch_progress = ctk.CTkProgressBar(self.batch_frame)
        self.batch_progress.pack(fill="x", padx=10, pady=(0, 10))
        self.batch_progress.set(0)

        # ── Settings ───────────────────────────────────────────────
        self.settings_frame = ctk.CTkFrame(self.main)
        self.settings_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            self.settings_frame, text="Settings / Preferences",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        out_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(out_row, text="Output Directory:", width=140).pack(side="left")
        self.output_dir_var = ctk.StringVar(value=self.settings.get("output_dir", str(DEFAULT_OUTPUT_DIR)))
        self.output_dir_entry = ctk.CTkEntry(out_row, textvariable=self.output_dir_var, width=320)
        self.output_dir_entry.pack(side="left", padx=(10, 10), fill="x", expand=True)
        ctk.CTkButton(out_row, text="Browse", width=70, command=self._browse_output_dir).pack(side="left")

        ai_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        ai_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(ai_row, text="AI Sensitivity Threshold:", width=140).pack(side="left")
        self.ai_slider = ctk.CTkSlider(
            ai_row, from_=0.1, to=1.0, number_of_steps=9,
            command=lambda v: self.ai_value_label.configure(text=f"{v:.1f}"),
        )
        self.ai_slider.pack(side="left", padx=(10, 10), fill="x", expand=True)
        self.ai_slider.set(self.settings.get("ai_sensitivity_threshold", 0.7))
        self.ai_value_label = ctk.CTkLabel(ai_row, text=f"{self.settings.get('ai_sensitivity_threshold', 0.7):.1f}", width=40)
        self.ai_value_label.pack(side="left")

        theme_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        theme_row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(theme_row, text="Appearance Theme:", width=140).pack(side="left")
        self.theme_var = ctk.StringVar(value=self.settings.get("theme", "dark"))
        self.theme_dropdown = ctk.CTkOptionMenu(
            theme_row, values=["dark", "light", "system"], variable=self.theme_var,
            width=110, font=ctk.CTkFont(size=11), command=lambda v: self._apply_theme(),
        )
        self.theme_dropdown.pack(side="left", padx=(10, 0))

        history_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        history_row.pack(fill="x", padx=10, pady=5)
        self.history_panel_var = ctk.BooleanVar(value=self.settings.get("show_history_panel", False))
        self.history_panel_checkbox = ctk.CTkCheckBox(
            history_row, text="Show download history panel on startup",
            variable=self.history_panel_var, font=ctk.CTkFont(size=11),
        )
        self.history_panel_checkbox.pack(side="left")

        updates_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        updates_row.pack(fill="x", padx=10, pady=5)
        self.updates_var = ctk.BooleanVar(value=self.settings.get("check_updates_on_startup", True))
        self.updates_checkbox = ctk.CTkCheckBox(
            updates_row, text="Check for updates on startup",
            variable=self.updates_var, font=ctk.CTkFont(size=11),
        )
        self.updates_checkbox.pack(side="left")

        if PORTABLE_MODE:
            portable_row = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
            portable_row.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(
                portable_row,
                text="💾 Portable mode: all state stored next to the executable",
                font=ctk.CTkFont(size=10), text_color="orange",
            ).pack(side="left")

        ctk.CTkButton(
            self.settings_frame, text="Save Settings", command=self._save_settings,
            width=120,
        ).pack(anchor="e", padx=10, pady=(5, 10))

        # ── Log ────────────────────────────────────────────────────
        ctk.CTkLabel(
            self.main, text="Log:", font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", pady=(10, 5))
        self.log = ctk.CTkTextbox(
            self.main, height=150,
            font=ctk.CTkFont(family="Consolas", size=10), state="disabled",
        )
        self.log.pack(fill="both", expand=True, pady=(0, 10))

        # ── File Management ────────────────────────────────────────
        self.file_mgmt_frame = ctk.CTkFrame(self.main)
        self.file_mgmt_frame.pack(fill="x", pady=(0, 10))
        self.file_mgmt_frame.pack_forget()

        ctk.CTkLabel(
            self.file_mgmt_frame, text="Downloaded Files",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.file_listbox = ctk.CTkScrollableFrame(self.file_mgmt_frame, height=140)
        self.file_listbox.pack(fill="x", padx=10, pady=(0, 10))

        self.refresh_files_btn = ctk.CTkButton(
            self.file_mgmt_frame, text="🔄 Refresh File List", command=self._refresh_file_list,
            width=180,
        )
        self.refresh_files_btn.pack(anchor="e", padx=10, pady=(0, 10))

    # ── Logging ────────────────────────────────────────────────────────
    def _gui_log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log(self, msg: str, level: str = "info"):
        getattr(logger, level)(msg)
        self.after(0, self._gui_log, msg)

    # ── Settings actions ─────────────────────────────────────────────
    def _browse_output_dir(self):
        from tkinter import filedialog
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get())
        if directory:
            self.output_dir_var.set(directory)

    def _save_settings(self):
        self.settings["output_dir"] = self.output_dir_var.get()
        self.settings["default_format"] = self.format_var.get()
        self.settings["cookies_browser"] = self.browser_var.get()
        self.settings["ai_sensitivity_threshold"] = round(float(self.ai_slider.get()), 1)
        self.settings["max_workers"] = int(self.workers_var.get() or DEFAULT_MAX_WORKERS)
        self.settings["bandwidth_kbps"] = int(self.bandwidth_var.get() or 0)
        self.settings["proxy_url"] = self.proxy_var.get()
        self.settings["embed_cover_art"] = self.cover_art_var.get()
        self.settings["playlist_mode"] = self.playlist_var.get()
        self.settings["theme"] = self.theme_var.get()
        self.settings["show_history_panel"] = self.history_panel_var.get()
        self.settings["check_updates_on_startup"] = self.updates_var.get()
        save_settings(self.settings)
        Path(self.settings["output_dir"]).mkdir(parents=True, exist_ok=True)
        self._gui_log("✅ Settings saved")
        logger.info("Settings saved: %s", self.settings)

    # ── Keyboard shortcuts & clipboard ─────────────────────────────────
    def _paste_urls(self):
        """Paste clipboard contents into the URL text box."""
        try:
            clipboard = self.clipboard_get()
            if clipboard.strip():
                self.url_text.insert("insert", clipboard + "\n")
                self._gui_log("📋 Pasted URLs from clipboard")
        except Exception as exc:
            self._gui_log(f"❌ Could not paste from clipboard: {exc}")

    # ── Download history panel ─────────────────────────────────────────
    def _toggle_history_panel(self):
        """Show or hide the download history panel."""
        if hasattr(self, "history_frame") and self.history_frame.winfo_exists():
            if self.history_frame.winfo_viewable():
                self.history_frame.pack_forget()
                self.history_panel_var.set(False)
            else:
                self.history_frame.pack(fill="x", pady=(0, 10))
                self.history_panel_var.set(True)
                self._refresh_history()
        else:
            self._build_history_panel()
            self.history_frame.pack(fill="x", pady=(0, 10))
            self.history_panel_var.set(True)
            self._refresh_history()

    def _build_history_panel(self):
        """Build the download history UI panel."""
        self.history_frame = ctk.CTkFrame(self.main)

        ctk.CTkLabel(
            self.history_frame,
            text="📜 Download History",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # History scrollable area
        self.history_list = ctk.CTkScrollableFrame(self.history_frame, height=200)
        self.history_list.pack(fill="x", padx=10, pady=(0, 10))

        # History action buttons
        btn_row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            btn_row, text="🔄 Re-download Selected", width=140,
            command=self._redownload_selected_history,
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_row, text="📤 Export CSV", width=100,
            command=self._export_history,
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_row, text="🗑️ Clear History", width=100, fg_color="red",
            hover_color="darkred", command=self._clear_history,
        ).pack(side="left")

        self._refresh_history()

    def _refresh_history(self):
        """Refresh the history display from self.download_history."""
        if not hasattr(self, "history_list"):
            return
        for widget in self.history_list.winfo_children():
            widget.destroy()

        if not self.download_history:
            ctk.CTkLabel(
                self.history_list,
                text="No downloads yet.",
                font=ctk.CTkFont(size=10),
                text_color="gray",
            ).pack(anchor="w", padx=5, pady=5)
            return

        # Show most recent first
        for entry in reversed(self.download_history[-50:]):
            row = ctk.CTkFrame(self.history_frame, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)

            ts = entry.get("downloaded_at", "")[:16].replace("T", " ")
            title = entry.get("title", "Unknown")
            size_mb = entry.get("size_mb", 0)
            fmt = entry.get("format", "FLAC")

            info_label = ctk.CTkLabel(
                row,
                text=f"{ts}  •  {title[:50]}  ({fmt}, {size_mb:.1f} MB)",
                font=ctk.CTkFont(size=10),
                anchor="w",
            )
            info_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

            ctk.CTkButton(
                row, text="Re-download", width=80,
                command=lambda u=entry.get("url", ""): self._redownload_from_history(u),
            ).pack(side="left", padx=2)

    def _redownload_from_history(self, url: str):
        """Re-download a URL from history."""
        if not url:
            return
        self.url_text.delete("0.0", "end")
        self.url_text.insert("0.0", url)
        self._gui_log(f"📋 Loaded URL from history: {url[:60]}…")
        self._start_rip()

    def _redownload_selected_history(self):
        """Re-download the most recent history entry."""
        if self.download_history:
            last = self.download_history[-1]
            self._redownload_from_history(last.get("url", ""))

    def _export_history(self):
        """Export download history to a CSV file."""
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export download history",
        )
        if path:
            try:
                export_history_csv(Path(path))
                self._gui_log(f"📤 History exported to {path}")
            except Exception as exc:
                self._gui_log(f"❌ Export failed: {exc}")

    def _clear_history(self):
        """Clear all download history."""
        if messagebox.askyesno("Clear History", "Delete all download history entries?"):
            self.download_history = []
            save_history([])
            self._refresh_history()
            self._gui_log("🗑️ History cleared")

    # ── Theme ──────────────────────────────────────────────────────────
    def _apply_theme(self):
        """Apply the selected appearance theme."""
        theme = self.theme_var.get()
        ctk.set_appearance_mode(theme)
        self._gui_log(f"🎨 Theme switched to {theme}")

    # ── Auto-updater prompt ────────────────────────────────────────────
    def _check_updates_prompt(self, skip_version: str = ""):
        """Check for updates and show a dialog if a new version is available."""
        release = check_for_updates()
        if not release:
            logger.info("No update available")
            return
        new_ver = release["version"]
        if new_ver == skip_version:
            return

        asset_name = self._update_asset_name(new_ver)
        download_url = self._find_asset_url(release, asset_name)

        msg = (
            f"🆕 Update available: v{new_ver} (current v{CURRENT_VERSION})\n\n"
            f"{release.get('body', '')[:300]}...\n\n"
        )
        if download_url:
            msg += f"Download asset: {asset_name}\n\n"
        msg += "Choose an option:"

        result = messagebox.askquestion(
            "Update Available",
            msg,
            icon="question",
            type=messagebox.YESNOCANCEL,
        )
        # askquestion returns 'yes', 'no', or 'cancel'
        if result == "yes":
            if download_url:
                self._download_and_install_update(new_ver, download_url)
            else:
                webbrowser.open(release.get("url", ""))
        elif result == "no":
            webbrowser.open(release.get("url", ""))
        # cancel = skip this version (do nothing)

    def _update_asset_name(self, version: str) -> str | None:
        """Return the expected release asset filename for this platform."""
        system = platform.system()
        if system == "Windows":
            return f"YouTube-Audio-Ripper-v{version}-win64.zip"
        if system == "Darwin":
            return f"YouTube-Audio-Ripper-v{version}-macos.tar.gz"
        if system == "Linux":
            return f"YouTube-Audio-Ripper-v{version}-linux.tar.gz"
        return None

    def _find_asset_url(self, release: dict, asset_name: str | None) -> str | None:
        """Find the download URL for a specific asset in a release."""
        if not asset_name:
            return None
        assets = release.get("assets", [])
        for asset in assets:
            if asset.get("name") == asset_name:
                return asset.get("browser_download_url")
        return None

    def _download_and_install_update(self, version: str, url: str):
        """Download the update asset and replace the running executable."""
        system = platform.system()

        if system == "Windows":
            self._download_and_install_windows(version, url)
        elif system == "Darwin":
            self._gui_log("🍎 macOS auto-install not yet supported — opening download page")
            webbrowser.open(url)
        elif system == "Linux":
            self._gui_log("🐧 Linux auto-install not yet supported — opening download page")
            webbrowser.open(url)
        else:
            self._gui_log(f"❓ Unsupported platform: {system}")
            webbrowser.open(url)

    def _download_and_install_windows(self, version: str, url: str):
        """Windows-specific: download zip, extract, replace EXE via helper batch."""
        import tkinter.filedialog as fd

        # Ask where to save the downloaded update
        save_path = fd.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP archive", "*.zip")],
            initialfile=f"YouTube-Audio-Ripper-v{version}-win64.zip",
            title="Save update package",
        )
        if not save_path:
            return

        self._gui_log(f"⬇️ Downloading update v{version}…")

        def _do_update():
            try:
                # Download
                req = urllib.request.Request(url, headers={"User-Agent": "youtube-audio-ripper-updater"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                Path(save_path).write_bytes(data)
                self.after(0, self._gui_log, f"✅ Downloaded: {save_path}")

                # Extract
                extract_dir = Path(save_path).with_suffix("")
                extract_dir.mkdir(exist_ok=True)
                with zipfile.ZipFile(save_path, "r") as zf:
                    zf.extractall(extract_dir)
                self.after(0, self._gui_log, "✅ Extracted update package")

                # Find the new EXE inside the extracted folder
                new_exe = None
                for f in extract_dir.rglob("*.exe"):
                    if "YouTube Audio Ripper" in f.name:
                        new_exe = f
                        break
                if not new_exe:
                    self.after(0, self._gui_log, "❌ Could not find EXE in update package")
                    return

                # Create a helper batch script that replaces the running EXE
                current_exe = Path(sys.executable)
                batch_script = extract_dir / "apply_update.bat"
                batch_content = f"""@echo off
timeout /t 2 /nobreak >nul
del /f /q "{current_exe}"
copy /y "{new_exe}" "{current_exe}"
start "" "{current_exe}"
del /f /q "{batch_script}"
rmdir /s /q "{extract_dir}"
"""
                batch_script.write_text(batch_content, encoding="utf-8")

                self.after(0, self._gui_log, "🔄 Applying update — app will restart…")
                # Launch the helper batch and exit
                subprocess.Popen(
                    [str(batch_script)],
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                )
                self.after(1000, self.quit)
            except Exception as exc:
                logger.exception("Auto-update failed")
                err_msg = str(exc)
                self.after(0, self._gui_log, f"❌ Update failed: {err_msg}")
                self.after(0, lambda m=err_msg: messagebox.showerror("Update Failed", m))

        threading.Thread(target=_do_update, daemon=True).start()

    def _skip_this_version(self, version: str):
        """Mark a version as skipped so it won't prompt again."""
        self.settings["skip_update_version"] = version
        save_settings(self.settings)

    # ── About dialog ───────────────────────────────────────────────────
    def _show_about(self):
        """Show the about dialog."""
        msg = (
            f"YouTube Audio Ripper v{CURRENT_VERSION}\n\n"
            "Paste a YouTube link, get a FLAC/MP3/M4A with metadata and cover art.\n\n"
            "Built with customtkinter, yt-dlp, FFmpeg.\n\n"
            "© 2026 Conrad CJ Wilson\n"
            "https://github.com/cjps4linux-creator/youtube-audio-ripper"
        )
        messagebox.showinfo("About YouTube Audio Ripper", msg)

    # ── Pre-flight & updates ─────────────────────────────────────────
    def _pre_flight_check(self):
        missing = []
        if not _check_ffmpeg():
            missing.append("ffmpeg")
        if not _check_yt_dlp():
            missing.append("yt-dlp (Python package)")
        if missing:
            msg = (
                "⚠️ Missing required dependency:\n\n"
                + "\n".join(f"  • {m}" for m in missing)
                + "\n\nPlease install the missing dependency and restart the app.\n"
                "See README.md for installation instructions."
            )
            self.start_btn.configure(state="disabled", text="❌ Missing Dependency")
            self._gui_log(msg)
            logger.error("Pre-flight check failed: missing %s", ", ".join(missing))

    def _check_updates(self):
        release = check_for_updates()
        if release:
            msg = (
                f"🆕 Update available: v{release['version']} (current v{CURRENT_VERSION})\n"
                f"{release['body'][:200]}...\n"
                f"Download: {release['url']}"
            )
            self._gui_log(msg)
            logger.info("Update available: v%s", release["version"])
        else:
            logger.info("No update available")

    def _request_stop(self):
        self._stop_requested = True
        self._gui_log("⏹ Stop requested — finishing current files…")

    # ── Download flow ────────────────────────────────────────────────
    def _start_rip(self):
        if self.processing:
            return
        urls_text = self.url_text.get("0.0", "end").strip()
        if not urls_text:
            self._gui_log("❌ Enter YouTube URLs first")
            return

        raw_urls = [line.strip() for line in urls_text.split("\n") if line.strip()]
        valid_urls, errors = validate_urls(raw_urls)
        if errors:
            for err in errors:
                self._gui_log(f"❌ {err}")
            if not valid_urls:
                return
        if not valid_urls:
            self._gui_log("❌ No valid YouTube URLs found")
            return

        self.processing = True
        self._stop_requested = False
        self.completed_jobs = 0

        # Detect playlists if playlist mode is on
        urls_to_process = list(valid_urls)
        if self.playlist_var.get():
            urls_to_process = self._expand_playlists(urls_to_process)
            if not urls_to_process:
                self.processing = False
                return

        self.total_jobs = len(urls_to_process)
        self.current_job = 0

        max_workers = int(self.workers_var.get() or DEFAULT_MAX_WORKERS)

        self.start_btn.configure(state="disabled", text="⏳ Processing…")
        self.stop_btn.configure(state="normal")
        self.file_progress.set(0)
        self.batch_progress.set(0)
        self.batch_frame.pack(fill="x", pady=(0, 10))
        self.file_label.configure(text=f"Starting batch of {self.total_jobs}…")
        self._gui_log(f"📋 Processing {self.total_jobs} URL(s) with {max_workers} concurrent worker(s)…")
        Path(self.settings.get("output_dir", str(DEFAULT_OUTPUT_DIR))).mkdir(parents=True, exist_ok=True)

        threading.Thread(
            target=self._process_parallel, args=(urls_to_process, max_workers), daemon=True
        ).start()

    def _expand_playlists(self, urls: list[str]) -> list[str]:
        """Detect playlist URLs and prompt user to select videos."""
        import yt_dlp
        expanded: list[str] = []
        for url in urls:
            if PLAYLIST_URL_RE.match(url):
                self._gui_log(f"🔍 Detecting playlist: {url[:60]}…")
                try:
                    ydl_opts = {
                        "quiet": True,
                        "no_warnings": True,
                        "extract_flat": True,
                    }
                    if self.proxy_var.get():
                        ydl_opts["proxy"] = self.proxy_var.get()
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    entries = info.get("entries", [])
                    if not entries:
                        self._gui_log("⚠️ No entries found in playlist")
                        continue
                    # Show selection dialog
                    dialog_entries = [
                        (i, e.get("title", f"Video {i+1}"), e.get("url", f"https://www.youtube.com/watch?v={e.get('id')}"))
                        for i, e in enumerate(entries) if e
                    ]
                    dialog = PlaylistDialog(self, f"Playlist: {info.get('title', 'Untitled')}", dialog_entries)
                    self.wait_window(dialog)
                    selected = dialog.selected or []
                    self._gui_log(f"📋 Selected {len(selected)} of {len(dialog_entries)} videos from playlist")
                    expanded.extend(selected)
                except Exception as exc:
                    self._gui_log(f"❌ Failed to detect playlist: {str(exc)[:100]}")
                    logger.exception("Playlist detection failed for %s", url)
            else:
                expanded.append(url)
        return expanded

    def _process_parallel(self, urls: list[str], max_workers: int):
        output_dir = Path(self.settings.get("output_dir", str(DEFAULT_OUTPUT_DIR)))
        output_dir.mkdir(parents=True, exist_ok=True)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self._download_convert, url, output_dir): url
                for url in urls
            }
            for future in concurrent.futures.as_completed(future_to_url):
                if self._stop_requested:
                    break
                url = future_to_url[future]
                self.current_job += 1
                self.completed_jobs += 1
                try:
                    future.result()
                except Exception as exc:
                    self.after(0, self._gui_log, f"❌ Error for {url[:50]}: {str(exc)[:100]}")
                    logger.exception("Download failed for %s", url)
                finally:
                    progress = self.completed_jobs / self.total_jobs if self.total_jobs else 0
                    self.after(0, self.batch_progress.configure, {"value": progress})
                    self.after(0, self.file_label.configure, {
                        "text": f"Completed {self.completed_jobs}/{self.total_jobs}"
                    })

        self.after(0, self._done)

    def _download_convert(self, url: str, output_dir: Path):
        """Download, deduplicate-check, convert, and embed metadata + cover art."""
        import yt_dlp

        # ── Deduplication check ───────────────────────────────────────
        existing = is_already_downloaded(url, self.downloads_registry)
        if existing:
            self.after(0, self._gui_log, f"⏭️ Skipping (already downloaded): {existing}")
            return

        temp_dir = Path(tempfile.gettempdir())
        tid = threading.get_ident()
        temp_file = temp_dir / f"ripper_temp_{tid}.%(ext)s"
        thumbnail_file = temp_dir / f"ripper_thumb_{tid}.%(ext)s"

        # Clean old temp files for this thread
        for f in temp_dir.glob(f"ripper_temp_{tid}.*"):
            f.unlink(missing_ok=True)
        for f in temp_dir.glob(f"ripper_thumb_{tid}.*"):
            f.unlink(missing_ok=True)

        self.after(0, self._gui_log, f"⬇️ Downloading: {url[:60]}…")
        self.after(0, self.file_progress.configure, {"value": 0.2})

        # ── yt-dlp options ────────────────────────────────────────────
        cookies_from_browser = self.settings.get("cookies_browser", "None")
        bandwidth_kbps = self.settings.get("bandwidth_kbps", 0)
        proxy_url = self.settings.get("proxy_url", "")
        embed_cover = self.settings.get("embed_cover_art", True)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(temp_file),
            "quiet": True,
            "no_warnings": True,
            "continuedl": True,  # resume partial downloads
            "noplaylist": True,  # single video only (playlist handled separately)
        }

        if cookies_from_browser != "None":
            ydl_opts["cookiesfrombrowser"] = cookies_from_browser
        if bandwidth_kbps > 0:
            ydl_opts["ratelimit"] = bandwidth_kbps * 1024  # KB/s -> bytes/s
        if proxy_url:
            ydl_opts["proxy"] = proxy_url
        if embed_cover:
            ydl_opts["writethumbnail"] = True
            ydl_opts["thumbnail"] = str(thumbnail_file)

        def _do_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Unknown")
                artist = info.get("artist") or info.get("uploader") or "Unknown Artist"
                album = info.get("album") or ""
                track = info.get("track") or ""
                thumbnail = info.get("thumbnail") or ""
                return info, title, artist, album, track, thumbnail

        try:
            info, title, artist, album, track, thumbnail_url = retry_download(_do_download)
        except Exception as exc:
            self.after(0, self._gui_log, f"❌ Download failed after retries: {str(exc)[:100]}")
            raise

        self.after(0, self._gui_log, f"✅ Downloaded: {title[:40]}")
        self.after(0, self.file_progress.configure, {"value": 0.5})

        # Find downloaded audio file
        downloaded = None
        for f in temp_dir.glob(f"ripper_temp_{tid}.*"):
            if f.exists():
                downloaded = f
                break
        if not downloaded:
            raise FileNotFoundError("Download failed — no output file found")

        # Find thumbnail file
        thumbnail_path = None
        for f in temp_dir.glob(f"ripper_thumb_{tid}.*"):
            if f.exists():
                thumbnail_path = f
                break

        self.after(0, self._gui_log, "Converting to FLAC…")
        self.after(0, self.file_progress.configure, {"value": 0.7})

        fmt = self.settings.get("default_format", "FLAC")
        safe_title = sanitize_filename(title)
        output_file = output_dir / f"{safe_title}.{fmt.lower()}"

        counter = 1
        original_output = output_file
        while output_file.exists():
            output_file = output_dir / f"{original_output.stem}_{counter}.{fmt.lower()}"
            counter += 1

        # ── FFmpeg conversion with metadata + cover art ───────────────
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(downloaded),
        ]

        # Add thumbnail as second input if available and embedding enabled
        thumb_input = None
        if embed_cover and thumbnail_path and thumbnail_path.exists():
            thumb_input = str(thumbnail_path)
            ffmpeg_cmd.extend(["-i", thumb_input])

        if fmt == "FLAC":
            ffmpeg_cmd.extend(["-q:a", "0", "-c:a", "flac", "-ar", "44100"])
        elif fmt == "MP3":
            ffmpeg_cmd.extend(["-q:a", "0", "-c:a", "libmp3lame", "-ar", "44100"])
        elif fmt == "M4A":
            ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", "256k", "-ar", "44100"])

        ffmpeg_cmd.extend([
            "-metadata", f"title={title}",
            "-metadata", f"artist={artist}",
        ])
        if album:
            ffmpeg_cmd.extend(["-metadata", f"album={album}"])
        if track:
            ffmpeg_cmd.extend(["-metadata", f"track={track}"])

        # Embed cover art as attached picture
        if thumb_input:
            ffmpeg_cmd.extend([
                "-map", "0", "-map", "1",
                "-c", "copy", "-c:v", "mjpeg",
                "-disposition:v:0", "attached_pic",
            ])

        ffmpeg_cmd.append(str(output_file))

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("FFmpeg conversion failed")

        # Cleanup temp files
        downloaded.unlink(missing_ok=True)
        if thumb_input:
            Path(thumb_input).unlink(missing_ok=True)

        # ── Update deduplication registry ─────────────────────────────
        self.downloads_registry[url] = output_file.name
        save_registry(self.downloads_registry)

        # ── Add to download history ───────────────────────────────────
        size_mb = output_file.stat().st_size / (1024 * 1024)
        add_history_entry(url, title, output_file.name, fmt, size_mb)
        self.download_history = load_history()

        self.after(0, self._gui_log, f"✅ Saved: {output_file.name} ({size_mb:.1f} MB)")
        self.after(0, self.file_progress.configure, {"value": 1.0})
        logger.info(
            "Saved %s (%.1f MB) from %s [format=%s, cover=%s, proxy=%s]",
            output_file.name, size_mb, url, fmt,
            bool(thumb_input), bool(proxy_url),
        )

    def _done(self):
        self.processing = False
        self.start_btn.configure(state="normal", text="🎵 START RIPPING 🎵")
        self.stop_btn.configure(state="disabled")
        self.batch_frame.pack_forget()
        self.file_progress.set(0)
        self.batch_progress.set(0)
        status = "stopped early" if self._stop_requested else "Done"
        self._gui_log(f"\n✅ {status}! Files in: {self.settings.get('output_dir', str(DEFAULT_OUTPUT_DIR))}")
        logger.info("Batch complete. Output directory: %s", self.settings.get("output_dir"))
        self._refresh_file_list()

    # ── File Management ──────────────────────────────────────────────
    def _refresh_file_list(self):
        for widget in self.file_listbox.winfo_children():
            widget.destroy()

        output_dir = Path(self.settings.get("output_dir", str(DEFAULT_OUTPUT_DIR)))
        if not output_dir.exists():
            self.file_mgmt_frame.pack_forget()
            return

        files = sorted(
            [f for f in output_dir.iterdir() if f.is_file() and f.suffix.lower() in (".flac", ".mp3", ".m4a")],
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )

        if not files:
            self.file_mgmt_frame.pack_forget()
            return

        self.file_mgmt_frame.pack(fill="x", pady=(0, 10))

        for f in files:
            row = ctk.CTkFrame(self.file_listbox, fg_color="transparent")
            row.pack(fill="x", padx=5, pady=2)

            size_kb = f.stat().st_size / 1024
            name_label = ctk.CTkLabel(
                row, text=f"{f.name}  ({size_kb:.0f} KB)",
                font=ctk.CTkFont(size=10), anchor="w",
            )
            name_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.pack(side="right")

            ctk.CTkButton(btns, text="Open", width=50,
                          command=lambda p=f: self._open_file(p)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="Folder", width=50,
                          command=lambda p=f: self._open_folder(p)).pack(side="left", padx=2)
            ctk.CTkButton(btns, text="Delete", width=50, fg_color="red", hover_color="darkred",
                          command=lambda p=f, n=f.name: self._delete_file(p, n)).pack(side="left", padx=2)

    def _open_file(self, path: Path):
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", str(path)], check=False)
            elif platform.system() == "Windows":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            self._gui_log(f"❌ Could not open file: {exc}")

    def _open_folder(self, path: Path):
        folder = str(path.parent)
        try:
            if platform.system() == "Darwin":
                subprocess.run(["open", folder], check=False)
            elif platform.system() == "Windows":
                os.startfile(folder)  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", folder], check=False)
        except Exception as exc:
            self._gui_log(f"❌ Could not open folder: {exc}")

    def _delete_file(self, path: Path, name: str):
        try:
            path.unlink()
            for url, fname in list(self.downloads_registry.items()):
                if fname == name:
                    del self.downloads_registry[url]
            save_registry(self.downloads_registry)
            self._gui_log(f"🗑️ Deleted: {name}")
            self._refresh_file_list()
        except Exception as exc:
            self._gui_log(f"❌ Could not delete: {exc}")


if __name__ == "__main__":
    app = YouTubeRipperApp()
    app.mainloop()
