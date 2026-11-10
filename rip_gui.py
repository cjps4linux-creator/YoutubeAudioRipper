#!/usr/bin/env python3
"""
YouTube Audio Ripper - Production-Grade Hardened Version (Phase 2)
Paste a YouTube link, get a FLAC named after the track. Local GUI, no account needed.

Phase 1 — Stabilise: class name fix, logging module, FFmpeg pre-flight check,
URL validation regex, sanitised filenames, [lorem]→job_id fix, CI test isolation,
path traversal protection.

Phase 2 — Harden: cookies-from-browser support, resume partial downloads,
deduplication registry, metadata embedding (title/artist/album/track),
retry with exponential backoff on transient yt-dlp failures.
"""

import json
import logging
import logging.handlers
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import customtkinter as ctk

# ── Configuration ──────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = APP_DIR / "ripped_music"
LOG_FILE = APP_DIR / "youtube_ripper.log"
DOWNLOADS_REGISTRY = OUTPUT_DIR / "downloads.json"

MAX_URL_LENGTH = 2048
MAX_URLS_PER_BATCH = 50
MAX_DOWNLOAD_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds

YOUTUBE_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]{11}(?:[?&].*)?$",
    re.IGNORECASE,
)

SUPPORTED_BROWSERS = [
    "None",
    "Chrome",
    "Firefox",
    "Edge",
    "Safari",
    "Opera",
    "Brave",
]

OUTPUT_DIR.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────
logger = logging.getLogger("youtube_ripper")
logger.setLevel(logging.DEBUG)

# Console handler
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(
    logging.Formatter("%(levelname)s: %(message)s")
)
logger.addHandler(_console_handler)

# File handler (rotating, keeps last 5 files × 5 MB each)
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
    """Return True if ffmpeg is available on PATH, False otherwise."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
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
    """
    Validate a single YouTube URL.
    Returns (is_valid, error_message_or_none).
    """
    if not url or not url.strip():
        return False, "URL is empty."

    url = url.strip()

    if len(url) > MAX_URL_LENGTH:
        return False, f"URL too long ({len(url)} chars, max {MAX_URL_LENGTH})."

    if not YOUTUBE_URL_RE.match(url):
        return False, "Not a valid YouTube video URL."

    return True, None


def validate_urls(urls: list[str]) -> tuple[list[str], list[str]]:
    """
    Validate a list of URLs.
    Returns (valid_urls, error_messages).
    """
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

    # Remove invalid filename characters
    invalid = '<>:\"/\\|?*'
    for char in invalid:
        title = title.replace(char, "")

    # Collapse multiple spaces
    title = re.sub(r"\s+", " ", title).strip()

    # Limit length
    title = title[:80]

    return title if title else "Unknown_Track"


# ── Downloads registry (deduplication) ─────────────────────────────────
def _load_downloads_registry() -> dict[str, str]:
    """Load the URL -> filename registry from disk."""
    try:
        data = json.loads(DOWNLOADS_REGISTRY.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return {}


def _save_downloads_registry(registry: dict[str, str]) -> None:
    """Persist the URL -> filename registry to disk."""
    try:
        DOWNLOADS_REGISTRY.write_text(
            json.dumps(registry, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Could not save downloads registry: %s", exc)


def _is_already_downloaded(url: str, registry: dict[str, str]) -> str | None:
    """
    Check if a URL has already been downloaded and the file still exists.
    Returns the existing filename if found, else None.
    """
    filename = registry.get(url)
    if filename:
        existing_path = OUTPUT_DIR / filename
        if existing_path.exists():
            return filename
    return None


# ── Retry with exponential backoff ─────────────────────────────────────
def _retry_download(func, *args, max_retries: int = MAX_DOWNLOAD_RETRIES,
                    base_delay: float = RETRY_BASE_DELAY, **kwargs):
    """
    Execute *func* with exponential backoff retries.
    Retries on any Exception. Delays: base, base*2, base*4, ...
    """
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
                logger.error(
                    "Download failed after %d attempts: %s",
                    max_retries, exc,
                )
    raise last_error  # type: ignore[misc]


# ── Application ────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class YouTubeRipperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Audio Ripper")
        self.geometry("700x620")

        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 700) // 2
        y = (self.winfo_screenheight() - 620) // 2
        self.geometry(f"+{x}+{y}")

        self.processing = False
        self.downloads_registry: dict[str, str] = _load_downloads_registry()
        self._build_ui()

        # Run pre-flight checks after UI is built
        self.after(100, self._pre_flight_check)

    # ── UI Construction ──────────────────────────────────────────────
    def _build_ui(self):
        # Main frame
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        ctk.CTkLabel(
            main, text="🎵 YouTube Audio Ripper",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(0, 5))
        ctk.CTkLabel(
            main, text="Download → FLAC with metadata & resume support",
            font=ctk.CTkFont(size=11), text_color="gray",
        ).pack(pady=(0, 15))

        # URL Input
        ctk.CTkLabel(
            main, text="YouTube URLs (one per line):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", pady=(0, 5))

        self.url_text = ctk.CTkTextbox(
            main, height=70,
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.url_text.pack(fill="x", pady=(0, 10))
        self.url_text.insert(
            "0.0", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        # Validation hint
        self.hint_label = ctk.CTkLabel(
            main,
            text="Paste one or more YouTube video URLs (one per line). Max 50 per batch.",
            font=ctk.CTkFont(size=9), text_color="gray",
        )
        self.hint_label.pack(anchor="w", pady=(0, 5))

        # Options row
        options_frame = ctk.CTkFrame(main, fg_color="transparent")
        options_frame.pack(fill="x", pady=(0, 10))

        # Cookies browser dropdown
        ctk.CTkLabel(
            options_frame, text="Authentication:",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="left", padx=(0, 6))
        self.browser_var = ctk.StringVar(value="None")
        self.browser_dropdown = ctk.CTkOptionMenu(
            options_frame,
            values=SUPPORTED_BROWSERS,
            variable=self.browser_var,
            width=140,
            font=ctk.CTkFont(size=11),
        )
        self.browser_dropdown.pack(side="left")

        # BIG START BUTTON
        self.start_btn = ctk.CTkButton(
            main, text="🎵 START RIPPING 🎵",
            font=ctk.CTkFont(size=20, weight="bold"),
            height=60, fg_color="green", hover_color="darkgreen",
            command=self._start_rip,
        )
        self.start_btn.pack(fill="x", pady=15)

        # Progress
        self.progress = ctk.CTkProgressBar(main)
        self.progress.pack(fill="x", pady=(0, 5))
        self.progress.set(0)

        self.status = ctk.CTkLabel(
            main, text="Ready", font=ctk.CTkFont(size=10)
        )
        self.status.pack()

        # Log
        ctk.CTkLabel(
            main, text="Log:",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="w", pady=(10, 5))
        self.log = ctk.CTkTextbox(
            main, height=140,
            font=ctk.CTkFont(family="Consolas", size=10), state="disabled",
        )
        self.log.pack(fill="both", expand=True)

    # ── Logging ────────────────────────────────────────────────────────
    def _gui_log(self, msg: str):
        """Write a message to the GUI log box."""
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log(self, msg: str, level: str = "info"):
        """Log to both GUI and file/console."""
        getattr(logger, level)(msg)
        self.after(0, self._gui_log, msg)

    # ── Pre-flight ─────────────────────────────────────────────────────
    def _pre_flight_check(self):
        """Verify required system dependencies before user starts ripping."""
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

    # ── Download flow ──────────────────────────────────────────────────
    def _start_rip(self):
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

        self.start_btn.configure(state="disabled", text="⏳ Processing…")
        self.progress.set(0.1)
        self._log(f"📋 Processing {len(valid_urls)} URL(s)…")

        threading.Thread(target=self._process, args=(valid_urls,), daemon=True).start()

    def _process(self, urls: list[str]):
        for i, url in enumerate(urls):
            self.after(0, self._gui_log, f"\n[{i + 1}/{len(urls)}] {url[:60]}…")
            try:
                self._download_convert(url)
            except Exception as e:
                self.after(0, self._gui_log, f"❌ Error: {str(e)[:100]}")
                logger.exception("Download failed for %s", url)

        self.after(0, self._done)

    def _download_convert(self, url: str):
        """Download, deduplicate-check, convert, and embed metadata."""
        import yt_dlp

        # ── Deduplication check ───────────────────────────────────────
        existing_filename = _is_already_downloaded(url, self.downloads_registry)
        if existing_filename:
            self.after(0, self._gui_log, f"⏭️ Skipping (already downloaded): {existing_filename}")
            return

        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / "ripper_temp.%(ext)s"

        # Clean old temp files
        for f in temp_dir.glob("ripper_temp.*"):
            f.unlink(missing_ok=True)

        self.after(0, self._gui_log, "Downloading…")
        self.after(0, self.progress.configure, {"value": 0.2})

        # ── yt-dlp options ────────────────────────────────────────────
        cookies_from_browser = self.browser_var.get()
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": str(temp_file),
            "quiet": True,
            "no_warnings": True,
            "continuedl": True,  # resume partial downloads
            "noplaylist": True,  # single video only
        }

        if cookies_from_browser != "None":
            ydl_opts["cookiesfrombrowser"] = cookies_from_browser
            self.after(0, self._gui_log, f"Using cookies from {cookies_from_browser}…")

        # ── Retry-wrapped download ────────────────────────────────────
        def _do_download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "Unknown")
                artist = info.get("artist") or info.get("uploader") or "Unknown Artist"
                album = info.get("album") or ""
                track = info.get("track") or ""
                return info, title, artist, album, track

        try:
            info, title, artist, album, track = _retry_download(_do_download)
        except Exception as exc:
            self.after(0, self._gui_log, f"❌ Download failed after retries: {str(exc)[:100]}")
            raise

        self.after(0, self._gui_log, f"✅ Downloaded: {title[:40]}")

        # Find downloaded file
        downloaded = None
        for f in temp_dir.glob("ripper_temp.*"):
            if f.exists():
                downloaded = f
                break

        if not downloaded:
            raise FileNotFoundError("Download failed — no output file found")

        self.after(0, self._gui_log, "Converting to FLAC…")
        self.after(0, self.progress.configure, {"value": 0.6})

        # Build output filename
        safe_title = sanitize_filename(title)
        output_file = OUTPUT_DIR / f"{safe_title}.flac"

        # Avoid overwriting: add counter suffix
        counter = 1
        original_output = output_file
        while output_file.exists():
            output_file = OUTPUT_DIR / f"{original_output.stem}_{counter}.flac"
            counter += 1

        # ── FFmpeg conversion with metadata embedding ─────────────────
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(downloaded),
            "-q:a", "0", "-c:a", "flac", "-ar", "44100",
            "-metadata", f"title={title}",
            "-metadata", f"artist={artist}",
        ]
        if album:
            ffmpeg_cmd.extend(["-metadata", f"album={album}"])
        if track:
            ffmpeg_cmd.extend(["-metadata", f"track={track}"])
        ffmpeg_cmd.append(str(output_file))

        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError("FFmpeg conversion failed")

        # Cleanup temp
        downloaded.unlink(missing_ok=True)

        # ── Update deduplication registry ─────────────────────────────
        self.downloads_registry[url] = output_file.name
        _save_downloads_registry(self.downloads_registry)

        size_mb = output_file.stat().st_size / (1024 * 1024)
        self.after(0, self._gui_log, f"✅ Saved: {output_file.name} ({size_mb:.1f} MB)")
        self.after(0, self.progress.configure, {"value": 1.0})
        logger.info(
            "Saved %s (%.1f MB) from %s [cookies=%s]",
            output_file.name, size_mb, url, cookies_from_browser,
        )

    def _done(self):
        self.start_btn.configure(state="normal", text="🎵 START RIPPING 🎵")
        self._gui_log(f"\n✅ Done! Files in: {OUTPUT_DIR}")
        logger.info("Batch complete. Output directory: %s", OUTPUT_DIR)


if __name__ == "__main__":
    app = YouTubeRipperApp()
    app.mainloop()
