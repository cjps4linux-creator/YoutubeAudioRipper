<h1 align="center">YouTube Audio Ripper</h1>

<p align="center"><b>Paste a link, get a FLAC named after the track. Local GUI, no account needed.</b></p>

<p align="center">
  <a href="https://github.com/cjps4linux-creator/youtube-audio-ripper/actions/workflows/ci.yml"><img src="https://github.com/cjps4linux-creator/youtube-audio-ripper/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/cjps4linux-creator/youtube-audio-ripper/releases/tag/v1.0.0"><img src="https://img.shields.io/badge/release-v1.0.0-0a7563" alt="Release v1.0.0"></a>
  <img src="https://img.shields.io/badge/license-MIT-0a7563" alt="License: MIT">
  <img src="https://img.shields.io/badge/python-3.11%2B-3776ab" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-8a5800" alt="Platforms">
  <img src="https://img.shields.io/badge/no_account-no_telemetry-0a7563" alt="No account, no telemetry">
</p>

---

## What it does

A desktop app that downloads the audio from a YouTube link, converts it to
FLAC, and names the file after the video title rather than a running number.

- **Paste-and-go GUI**  -  CustomTkinter, no command line
- **FLAC output**  -  with metadata preserved
- **Smart filenames**  -  `Rick Astley - Never Gonna Give You Up.flac`, sanitised
  for the filesystem
- **Batch friendly**  -  no more `001.flac` overwriting `001.flac`

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
