# YouTube Audio Ripper - Android Edition

Download YouTube audio as FLAC / MP3 / M4A on your Android phone using Termux.

## Quick Start

### 1. Install Termux

Download Termux from **F-Droid** (not Play Store):
https://f-droid.org/packages/com.termux/

> Play Store version is deprecated. Use F-Droid only.

### 2. Push Files to Phone

Connect your phone to the same network as your Windows PC, then:

```bash
# Enable wireless ADB on your phone:
#   Settings > Developer Options > Wireless Debugging > Pair device

# From your Windows PC:
adb connect <your-phone-ip>:<port>
adb push android\* /sdcard/YouTubeAudioRipper/
adb push android\static /sdcard/YouTubeAudioRipper/
```

### 3. Set Up Termux

Open Termux and run:

```bash
bash /sdcard/YouTubeAudioRipper/setup_termux.sh
```

This installs Python, Node.js, FFmpeg, and yt-dlp automatically.

### 4. Start the Ripper

```bash
cd ~/storage/shared/YouTubeAudioRipper
python ripper_server.py
```

Open your browser to: **http://localhost:8080**

### 5. Add Home Screen Widget (Optional)

Install **Termux:API** from F-Droid, then in Termux:

```bash
# Install Termux:API app from F-Droid first, then:
pkg install termux-api
termux-setup-storage

# Create widget:
mkdir -p ~/.shortcuts/tasks/yt-ripper
# Copy widget_launcher.sh into that folder
```

Then use a widget app (like **KWCH** or **Nova Launcher** shortcuts) to add the Termux task to your home screen.

---

## File Structure

```
/sdcard/YouTubeAudioRipper/
├── ripper_server.py        # Main app (HTTP server + downloader)
├── convert_cookies.py      # Brave cookie converter
├── setup_termux.sh         # One-command setup
├── widget_launcher.sh      # Termux widget script
├── cookies.txt             # Optional: your browser cookies
└── static/
    └── index.html          # Phone-optimized UI

Output:
~/storage/shared/Music/     # FLAC / MP3 / M4A files land here
```

---

## Authentication

**Public videos**  -  no auth needed, just paste and download.

**Protected content** (playlists, private, bot-protected):
1. Export cookies from Brave Android DevTools
2. Convert: `python convert_cookies.py cookies.tsv cookies.txt`
3. Place `cookies.txt` in the app folder

See your Windows app's `skill_youtube-audio-ripper/references/authentication.md` for details.

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Phone-optimized UI |
| `/health` | GET | Server status |
| `/files` | GET | List downloaded files |
| `/download/{name}` | GET | Stream a file |
| `/rip` | POST | Start download `{url, format, quality}` |
| `/progress/{[lorem]}` | GET | SSE progress stream |
| `/delete/{name}` | POST | Delete a file |

---

## Formats

| Format | Quality | Use Case |
|---|---|---|
| **FLAC** | Lossless | Archiving, audiophile |
| **MP3** | 320kbps | Universal compatibility |
| **M4A** | 256k AAC | Apple ecosystem, smaller files |

---

## Troubleshooting

**"Connection refused" on localhost:8080**
- Make sure the server is running: `python ripper_server.py`
- Check Termux has storage permission: `termux-setup-storage`

**Download fails with 403**
- Add cookies.txt (see Authentication above)
- Make sure Node.js is installed: `pkg install nodejs`

**"Sign in to confirm you're not a bot"**
- This is YouTube's anti-bot check
- Solution: fresh cookies.txt from Brave

**Server won't start after phone reboot**
- Re-run: `python ripper_server.py`
- Or use the widget launcher

**Files not appearing in Music app**
- Files are in `~/storage/shared/Music/`
- Reboot your phone's media scanner: `termux-media-scan ~/storage/shared/Music/`

---

## Credits

Built by Conrad CJ Wilson  -  https://linkedin.com/in/conradcjwilson

Reuses the proven yt-dlp stack from the Windows YouTube Audio Ripper.
