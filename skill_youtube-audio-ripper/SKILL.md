---
name: youtube-audio-ripper
description: YouTube Audio Ripper - Modern GUI for downloading YouTube audio to FLAC with AI voice detection. Use when the user wants to download YouTube audio, convert to lossless FLAC, or detect AI-generated voices in audio content.
---

# YouTube Audio Ripper

Modern GUI application for downloading YouTube audio, converting to FLAC, and detecting AI-generated voices.

## Quick Start

```bash
cd path\to\youtube-audio-ripper
./venv/Scripts/python.exe rip_gui.py
```

## Features

- **Multi-URL Input**: Paste one or more YouTube URLs (one per line, or bulk paste with Ctrl+V)
- **High-Quality Download**: Uses yt-dlp for highest quality audio extraction
- **FLAC Conversion**: Lossless audio format with metadata preservation
- **AI Voice Detection**: Spectral analysis (spectral flatness + ZCR) detects AI vs Human vocals
- **Smart Naming**: `001.flac` (human) or `AI_001.flac` (AI-detected)
- **Real-Time Progress**: Progress sample with detailed logging
- **Silent Launcher**: VBS launches without console window

## File Structure

```
path\to\youtube-audio-ripper\
├── rip_gui.py            # Main application
├── launch.vbs            # Silent Windows launcher
├── launch.bat            # Batch file launcher
├── requirements.txt      # Python dependencies
├── venv/                 # Python virtual environment
├── ripped_music/         # Output folder (auto-created)
└── skill_youtube-audio-ripper/
    ├── SKILL.md          # This file
    ├── references/       # Session-specific details
    ├── templates/        # Reusable code templates
    └── scripts/          # Verification scripts
```

## Dependencies

**Python packages** (installed in venv):
- `customtkinter` - Modern GUI framework
- `yt-dlp` - YouTube download library
- `pillow` - Image handling
- `librosa` - Audio analysis (spectral features)
- `soundfile` - FLAC file writing
- `numpy` - Numerical computing

**System requirements**:
- FFmpeg (already installed on system)
- Windows 10/11
- Python 3.11+

## YouTube Authentication

**Public videos** (no auth required):
- Standalone music videos
- Most short clips
- Example: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`

**Protected content** (auth required):
- Playlist videos
- Private videos
- Some trending content
- Error: "Sign in to confirm you're not a bot"

**Authentication options**:
1. Use only public videos
2. Browser cookie authentication: `--cookies-from-browser="Chrome"`
3. Manual cookie injection (advanced)

## Usage

1. **Launch the app**:
   - Double-click `launch.vbs` (silent)
   - Or run from terminal
   - Or click desktop shortcut

2. **Paste YouTube URLs**:
   - One URL per line
   - Or use Ctrl+V for bulk paste

3. **Adjust AI sensitivity** (optional):
   - Lower = more sensitive (more AI flags)
   - Higher = stricter (fewer AI flags)

4. **Click "START RIPPING"**:
   - App downloads and processes each URL
   - Progress sample shows status
   - Log shows track-by-track results

5. **Access results**:
   - Files saved to `ripped_music/`
   - Format: `001.flac` (human) or `AI_001.flac` (AI)
   - Click "Open Folder" to access

## Output Format

**Human voice detected**: `001.flac`, `002.flac`, etc.
**AI voice detected**: `AI_001.flac`, `AI_002.flac`, etc.

All files:
- FLAC lossless format
- Original metadata preserved
- Numbered sequentially per URL
- Organized in single `ripped_music/` folder

## AI Detection Algorithm

Spectral analysis based on:
1. **Spectral Flatness**: AI voices are more tonal (lower flatness)
2. **Zero Crossing Rate**: Human voices have more variation (higher ZCR)
3. **Combined Score**: Weighted average determines AI probability

**Threshold tuning**:
- Default: 0.65 (balanced)
- Range: 0.3 (very sensitive) to 0.9 (very strict)

## Common Issues

**1. YouTube authentication required**:
- Use public videos only
- Or authenticate via browser cookies

**2. No tracks detected from single video**:
- YouTube videos often have no silence gaps
- Use longer videos (5+ minutes)
- Or accept single-track output

**3. Download fails**:
- Check internet connection
- Verify ffmpeg is installed
- Try different video

**4. GUI not appearing**:
- Check taskbar
- App may be running in background
- Verify Python dependencies installed

## Session Notes

**Built during**: August 31, 2026 session
**User**: Conrad CJ Wilson (Durban, South Africa)
**Environment**: Windows 11, i7-1185G7, 16GB CPU-only
**Python**: 3.11.15 (venv-based)

**Key learnings**:
- `essentia-python` fails to build on Windows → use `librosa` instead
- YouTube authentication varies by video type
- Public videos work without auth; playlists require auth
- GUI needs prominent Start button for usability
- VBS launcher runs app silently (no console window)
- Test public videos first to establish baseline

## Support Files

- `references/gui-layout.md` - GUI layout specifications
- `references/authentication.md` - Authentication workflow details
- `templates/rip-template.py` - Ripper template script
- `scripts/validate-rip.py` - Post-rip validation script

## Version History

**1.0.0** (2026-08-31):
- Initial release
- Core GUI functionality
- YouTube download and FLAC conversion
- AI voice detection
- Silent VBS launcher
- Desktop shortcut creation

## References

- yt-dlp: https://yt-dlp.org/
- CustomTkinter: https://customtkinter.tomschimansky.de/
- Librosa: https://librosa.org/
- FFmpeg: https://ffmpeg.org/
