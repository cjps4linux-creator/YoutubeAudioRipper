# YouTube Audio Ripper — User Manual

**Version 2.2.0** · Conrad CJ Wilson · https://github.com/cjps4linux-creator/youtube-audio-ripper

---

## Table of Contents

1. [What It Does](#what-it-does)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [First Launch](#first-launch)
5. [Downloading Audio](#downloading-audio)
6. [Batch Downloads](#batch-downloads)
7. [Settings & Preferences](#settings--preferences)
8. [Download History](#download-history)
9. [Portable Mode](#portable-mode)
10. [Auto-Updates](#auto-updates)
11. [Keyboard Shortcuts](#keyboard-shortcuts)
12. [Troubleshooting](#troubleshooting)
13. [Legal & Licence](#legal--licence)

---

## What It Does

YouTube Audio Ripper is a desktop application that downloads the audio from a
YouTube link, converts it to FLAC (or MP3/M4A), names the file after the video
title, and embeds metadata (title, artist, album, track) plus cover art.

No account is required. No telemetry is collected. Everything runs locally.

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10/11, macOS 12+, Linux | Windows 11, macOS 14+, Linux |
| CPU | Dual-core 1.6 GHz | Quad-core 2.0 GHz+ |
| RAM | 4 GB | 8 GB+ |
| Disk | 500 MB free | 2 GB free |
| Python | 3.11+ | 3.11+ |
| FFmpeg | Bundled with installer | Bundled with installer |
| Network | Broadband | Broadband |

---

## Installation

### Option A: Standalone Installer (Recommended)

1. Go to the [Releases page](https://github.com/cjps4linux-creator/youtube-audio-ripper/releases).
2. Download the asset for your platform:
   - **Windows:** `YouTube-Audio-Ripper-vX.Y.Z-win64.zip`
   - **macOS:** `YouTube-Audio-Ripper-vX.Y.Z-macos.tar.gz`
   - **Linux:** `YouTube-Audio-Ripper-vX.Y.Z-linux.tar.gz`
3. Extract the archive.
4. Run `YouTube Audio Ripper.exe` (Windows), `YouTube Audio Ripper.app` (macOS), or `YouTube Audio Ripper` (Linux).

> **Windows "Unknown publisher" warning:** The installer is not yet code-signed. Windows SmartScreen may show a warning. Click "More info" → "Run anyway" to proceed. A code-signed installer is planned for a future release.

### Option B: From Source (Python)

1. Clone the repository:
   ```bash
   git clone https://github.com/cjps4linux-creator/youtube-audio-ripper.git
   cd youtube-audio-ripper
   ```
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   source .venv/bin/activate     # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install FFmpeg separately if not already on PATH.
5. Run:
   ```bash
   python rip_gui.py
   ```

---

## First Launch

On first launch the app performs a **pre-flight check**:

1. Verifies FFmpeg is available (bundled with installer, or on PATH for source installs).
2. Verifies yt-dlp Python package is importable.
3. Checks for updates on startup (if enabled in settings).

If anything is missing, the Start button is disabled and an error message is shown.

---

## Downloading Audio

### Single Video

1. Copy a YouTube URL (e.g. `https://www.youtube.com/watch?v=dQw4w9WgXcQ`).
2. Paste it into the URL text box (or press **Ctrl+V**).
3. Select the output format (FLAC, MP3, or M4A).
4. Click **🎵 START RIPPING 🎵** (or press **Ctrl+Enter**).
5. The downloaded file appears in the output directory (default: `ripped_music/`).

### Playlist

1. Check **Playlist mode**.
2. Paste a YouTube playlist URL.
3. Click **Start**.
4. A dialog appears listing all videos in the playlist. Select which ones to download.
5. Click **Select All** or **Select None** to quickly choose, then click OK.

---

## Batch Downloads

You can paste multiple YouTube URLs, one per line, into the URL text box:

```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/abcdefghijk
https://www.youtube.com/watch?v=ABCDEFGHIJK
```

- Up to 50 URLs per batch.
- Downloads run in parallel (configurable in Settings, default 3 workers).
- Each file shows individual progress; a batch progress bar shows overall completion.
- Click **⏹ STOP** (or press **Escape**) to abort after the current file finishes.

---

## Settings & Preferences

Open the **Settings / Preferences** panel to configure:

| Setting | Description |
|---------|-------------|
| Output Directory | Where downloaded files are saved |
| Default Format | FLAC (lossless), MP3, or M4A |
| Cookies From Browser | Chrome, Firefox, Edge, etc. (for bot-protected videos) |
| Max Concurrent | Number of parallel downloads (1–10) |
| Bandwidth Cap | KB/s limit (0 = unlimited) |
| Proxy | HTTP/SOCKS5 proxy URL |
| Embed Cover Art | Include thumbnail as attached picture in FLAC |
| Playlist Mode | Detect and process playlist URLs |
| Appearance Theme | Dark, Light, or System |
| Show History Panel | Display download history on startup |
| Check for Updates | Check GitHub releases on launch |

Click **Save Settings** to persist changes.

---

## Download History

Every completed download is recorded in the history:

- **View:** Press **Ctrl+H** or enable "Show download history panel on startup" in Settings.
- **Re-download:** Click "Re-download" next to any history entry.
- **Export:** Click "📤 Export CSV" to save the history as a spreadsheet-compatible file.
- **Clear:** Click "🗑️ Clear History" to remove all entries.

History is limited to the 500 most recent downloads.

---

## Portable Mode

Run the app from a USB stick without writing to AppData:

1. Create an empty file named `portable` (no extension) next to `YouTube Audio Ripper.exe`.
2. Launch the app.
3. All state (settings, download registry, history, logs) is stored in the same folder as the EXE.

A "💾 Portable mode detected" message appears in the log on startup.

---

## Auto-Updates

The app checks GitHub releases on startup (if enabled in Settings):

1. A dialog appears if a new version is available.
2. Click **Yes** to open the download page in your browser.
3. Download the new installer and run it.

> **Auto-download-and-replace:** Planned for a future release. Currently the app opens the download page; you must manually install the update.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+V** | Paste clipboard contents into URL box |
| **Ctrl+Enter** | Start ripping |
| **Ctrl+S** | Save settings |
| **Ctrl+O** | Browse output directory |
| **Escape** | Stop processing (after current file) |
| **Ctrl+H** | Toggle download history panel |
| **F1** | Show About dialog |

---

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common errors and fixes.

---

## Legal & Licence

- Download only content you have the right to download.
- Respect YouTube's Terms of Service and applicable copyright law.
- This software is provided under the MIT License — see [LICENSE](./LICENSE).

---

**Built by Conrad CJ Wilson** · [GitHub](https://github.com/cjps4linux-creator) · [LinkedIn](https://linkedin.com/in/conradcjwilson)
