<h1 align="center">YouTube Audio Ripper</h1>

<p align="center"><b>Paste a link, get a FLAC named after the track. Local GUI, no account needed.</b></p>

<p align="center">
  <a href="https://github.com/cjps4linux-creator/youtube-audio-ripper/actions/workflows/ci.yml"><img src="https://github.com/cjps4linux-creator/youtube-audio-ripper/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/cjps4linux-creator/youtube-audio-ripper/releases/tag/v2.3.0"><img src="https://img.shields.io/badge/release-v2.3.0-0a7563" alt="Release v2.3.0"></a>
  <img src="https://img.shields.io/badge/license-MIT-0a7563" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-8a5800" alt="Platforms">
  <img src="https://img.shields.io/badge/no_account-no_telemetry-0a7563" alt="No account, no telemetry">
</p>

---

## What it does

A desktop app that downloads audio from YouTube links, converts it to FLAC
(or MP3/M4A), and names each file after the video title. No command line,
no account needed.

### Core workflow

| Step | What happens |
|------|--------------|
| 1 | Paste a YouTube URL into the app |
| 2 | App validates the URL and checks FFmpeg is present |
| 3 | yt-dlp downloads the best available audio |
| 4 | FFmpeg converts to your chosen format (FLAC default) |
| 5 | Metadata (title, artist, album, cover art) is embedded |
| 6 | File is saved with a clean, sanitised name |

### Key features

- **Paste-and-go GUI** — CustomTkinter interface, no command line required
- **Format choice** — FLAC (lossless), MP3, or M4A output
- **Metadata & cover art** — title, artist, album, and embedded thumbnail
- **Smart filenames** — `Rick Astley - Never Gonna Give You Up.flac`, not `001.flac`
- **Batch downloads** — queue multiple URLs, per-file progress, stop anytime
- **Playlist support** — detect and select which videos to rip from a playlist
- **Parallel downloads** — ThreadPoolExecutor for concurrent rips
- **Resume** — interrupted downloads continue where they left off
- **Deduplication** — `downloads.json` registry prevents re-ripping the same track
- **Retry** — exponential backoff (1s, 2s, 4s, max 3 attempts) on failure
- **Cookies-from-browser** — authenticate with Chrome/Edge/Firefox for bot-protected videos
- **Bandwidth limiting** — cap download speed in KB/s
- **Proxy support** — SOCKS5/HTTP proxy configuration
- **Download history** — view past rips, re-download, export to CSV
- **Themes** — Dark / Light / System toggle
- **Keyboard shortcuts** — Ctrl+V paste, Ctrl+Enter start, Escape stop, etc.
- **Portable mode** — create an empty `portable` file next to the EXE to store state locally
- **Auto-updater** — checks GitHub releases on startup, downloads and installs updates
- **FFmpeg bundled** — `ffmpeg.exe` and `ffprobe.exe` ship alongside the EXE
- **Logging** — file + console logs for troubleshooting

## Screenshots

<p align="center"><b>Main Menu</b></p>

<p align="center">
  <img src="assets/screenshots/main-menu.png" alt="YouTube Audio Ripper — Main Menu" width="700">
</p>

---

## Requirements

- Python 3.11+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

## Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Run

```bash
python rip_gui.py
```

Or double-click `launch.vbs` / `launch.bat` on Windows.

## Authentication

YouTube increasingly requires a signed-in session. When a download fails with
`Sign in to confirm you're not a bot`, the app needs browser cookies  -  it
supports `--cookies-from-browser`:

```bash
python rip_gui.py --cookies-from-browser="Chrome"
```

This is YouTube's intended authentication path; there is no bypass.

## Legal note

Download only content you have the right to download. Respect YouTube's Terms
of Service and applicable copyright law in your jurisdiction.

## Licence

MIT  -  see [LICENSE](LICENSE).

---

## Credits

Built by **Conrad CJ Wilson**  -  [GitHub](https://github.com/cjps4linux-creator) · [LinkedIn](https://linkedin.com/in/conradcjwilson)

`conradcjwilson0@gmail.com`

---

## Windows: "Unknown Publisher" Warning

The distributed `YouTube Audio Ripper.exe` is **not code-signed** (no
certificate purchased). On first launch, Windows SmartScreen may show an
"Unknown publisher" warning. Click **More info → Run anyway** — this only
happens once per version.

This is intentional: no budget for a code signing certificate (~$250–$500/year).
If you trust the source, the warning can be safely ignored.

## Download

Get the latest standalone EXE from the
[Releases page](https://github.com/cjps4linux-creator/youtube-audio-ripper/releases).
No installation required — just run the EXE.
