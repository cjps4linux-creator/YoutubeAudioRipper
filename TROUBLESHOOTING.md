# YouTube Audio Ripper — Troubleshooting Guide

**Version 2.3.0** · Common errors, causes, and fixes.

---

## Table of Contents

1. [FFmpeg Not Found](#ffmpeg-not-found)
2. [Bot Detection / Sign-In Required](#bot-detection-sign-in-required)
3. [Rate Limiting / 429 Errors](#rate-limiting-429-errors)
4. [Download Fails Silently](#download-fails-silently)
5. [File Already Exists / Overwrite](#file-already-exists-overwrite)
6. [App Won't Start (Windows)](#app-wont-start-windows)
7. [App Won't Start (macOS/Linux)](#app-wont-start-macoslinux)
8. [Slow Downloads](#slow-downloads)
9. [Cover Art Missing](#cover-art-missing)
10. [Metadata Wrong or Missing](#metadata-wrong-or-missing)
11. [Playlist Not Detected](#playlist-not-detected)
12. [Portable Mode Not Working](#portable-mode-not-working)
13. [Update Check Fails](#update-check-fails)
14. [Getting Further Help](#getting-further-help)

---

## FFmpeg Not Found

### Symptom
Pre-flight check shows "⚠️ Missing required dependency: ffmpeg" and the Start button is disabled.

### Cause
FFmpeg is not on the system PATH and not bundled next to the executable.

### Fix

**Standalone installer:** FFmpeg is bundled automatically. Re-download from the [Releases page](https://github.com/cjps4linux-creator/youtube-audio-ripper/releases).

**Source install:** Install FFmpeg and ensure `ffmpeg` is on PATH:
```bash
# Windows (winget)
winget install Gyan.FFmpeg

# macOS (Homebrew)
brew install ffmpeg

# Linux (apt)
sudo apt-get install ffmpeg
```

Then restart the app.

---

## Bot Detection / Sign-In Required

### Symptom
Download fails with an error like:
- "Sign in to confirm you're not a bot"
- "This video is unavailable"
- HTTP 429 or 403 from YouTube

### Cause
YouTube is throttling or blocking requests from your IP address because it suspects automated access.

### Fix

Use **cookies-from-browser** to authenticate with your signed-in browser session:

1. Open Settings in the app.
2. Select your browser from the "Auth" dropdown (Chrome, Firefox, Edge, Safari, Opera, Brave).
3. Save settings.
4. Retry the download.

> **Important:** This is YouTube's intended authentication path. There is no bypass. You must be signed into YouTube in the selected browser.

---

## Rate Limiting / 429 Errors

### Symptom
Downloads start but fail after a few files with HTTP 429 (Too Many Requests).

### Cause
YouTube is rate-limiting your IP address due to too many rapid requests.

### Fix

1. **Reduce concurrency:** Set "Max concurrent" to 1 in Settings.
2. **Add a delay:** Use a bandwidth cap (e.g., 500 KB/s) to slow requests.
3. **Wait:** Stop downloads and wait 15–30 minutes before resuming.
4. **Use cookies:** Authenticate via cookies-from-browser (see above).

---

## Download Fails Silently

### Symptom
The log shows "❌ Download failed after retries" with no further detail.

### Cause
yt-dlp encountered an error it couldn't recover from after 3 retry attempts.

### Fix

1. Check the log file (`youtube_ripper.log` next to the EXE) for the full traceback.
2. Verify the URL is valid by opening it in a browser.
3. Try the URL alone (not in a batch) to isolate the issue.
4. If the video is age-restricted or region-blocked, cookies-from-browser may be required.

---

## File Already Exists / Overwrite

### Symptom
Downloading the same URL twice produces `Song Title_1.flac`, `Song Title_2.flac`, etc.

### Cause
The deduplication registry records that the URL was already downloaded. To avoid overwriting, the app appends a counter.

### Fix

This is expected behavior. To replace an existing file:

1. Delete the existing file from the output directory (use the "Delete" button in File Management).
2. Remove the URL from the deduplication registry (`downloads.json`) — or simply download again; the app will create a numbered copy.

---

## App Won't Start (Windows)

### Symptom
Double-clicking `YouTube Audio Ripper.exe` does nothing, or a window flashes and closes.

### Cause
Missing FFmpeg, missing Python runtime, or antivirus blocking the unsigned EXE.

### Fix

1. Check `youtube_ripper.log` next to the EXE for errors.
2. Ensure Windows SmartScreen isn't blocking it: right-click → Properties → "Unblock".
3. Add an exclusion in Windows Defender for the app folder.
4. If building from source, ensure all dependencies are installed: `pip install -r requirements.txt`.

---

## App Won't Start (macOS/Linux)

### Symptom
`YouTube Audio Ripper.app` won't open, or the binary exits immediately.

### Cause
Missing FFmpeg, missing GUI libraries, or Gatekeeper blocking on macOS.

### Fix

**macOS:**
```bash
# Install FFmpeg
brew install ffmpeg

# If Gatekeeper blocks the app:
xattr -d com.apple.quarantine "YouTube Audio Ripper.app"
```

**Linux:**
```bash
# Install FFmpeg and GUI libraries
sudo apt-get install ffmpeg libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender1 libfreetype6 libfontconfig1

# Run with xvfb if no display available
xvfb-run -a ./YouTube\ Audio\ Ripper
```

---

## Slow Downloads

### Symptom
Downloads take much longer than expected.

### Cause
YouTube throttling, bandwidth cap set in Settings, or network issues.

### Fix

1. Check Settings → "Bandwidth cap (KB/s)" — set to 0 for unlimited.
2. Reduce "Max concurrent" if you're on a slow connection.
3. Use a proxy if your ISP throttles YouTube (Settings → Proxy).
4. Try downloading during off-peak hours.

---

## Cover Art Missing

### Symptom
The downloaded FLAC/MP3/M4A has no thumbnail image.

### Cause
"Embed cover art" is disabled, or yt-dlp couldn't extract a thumbnail.

### Fix

1. Check Settings → "Embed cover art" is enabled.
2. Some videos (age-restricted, region-blocked) don't expose thumbnails to yt-dlp.
3. Check `youtube_ripper.log` for cover-art extraction errors.

---

## Metadata Wrong or Missing

### Symptom
Artist, album, or track fields are blank or incorrect in the output file.

### Cause
YouTube doesn't always provide structured metadata. The app falls back to the uploader name as "artist".

### Fix

Metadata quality depends on the video. There is no manual override in v2.2.0. Use a dedicated tag editor (e.g., Mp3tag, Kid3) to correct metadata after download.

---

## Playlist Not Detected

### Symptom
Pasting a playlist URL downloads only one video, or none.

### Cause
"Playlist mode" is not enabled, or the playlist is private/deleted.

### Fix

1. Check Settings → "Playlist mode" is enabled.
2. Ensure the playlist URL is public and accessible.
3. The app fetches playlist entries and shows a selection dialog — make sure you select at least one video.

---

## Portable Mode Not Working

### Symptom
State (settings, history) is not preserved when moving the app folder.

### Cause
The `portable` marker file is missing, or the app doesn't have write permission to its own directory.

### Fix

1. Create an empty file named exactly `portable` (no extension) next to `YouTube Audio Ripper.exe`.
2. Ensure the app folder is writable (not in `C:\Program Files\` — use `C:\Users\<name>\PortableApps\` or a USB stick).
3. Restart the app.

---

## Update Check Fails

### Symptom
No update notification appears, or the app logs "Auto-update check failed".

### Cause
No network access, GitHub API rate limit, or the app is running an older version without the updater.

### Fix

1. Verify internet connectivity.
2. Check Settings → "Check for updates on startup" is enabled.
3. Manually visit the [Releases page](https://github.com/cjps4linux-creator/youtube-audio-ripper/releases) to check for new versions.
4. If you're behind a proxy, configure it in Settings → Proxy.

---

## Getting Further Help

If this guide doesn't resolve your issue:

1. Check `youtube_ripper.log` for the full error traceback.
2. Search existing issues: https://github.com/cjps4linux-creator/youtube-audio-ripper/issues
3. Open a new issue with:
   - Your OS and version
   - App version (shown in the header)
   - The full log output
   - Steps to reproduce

**Security issues:** Email `conradcjwilson0@gmail.com` — do not open public issues for vulnerabilities.
