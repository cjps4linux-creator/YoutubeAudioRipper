# Code Signing — Not Required

**Status:** Skipped (by design)  
**Owner:** Conrad CJ Wilson  
**Priority:** None — users accept "Unknown publisher" warning

---

## Decision

We are **not purchasing a code signing certificate**. Windows SmartScreen will show
an "Unknown publisher" warning when running `YouTube Audio Ripper.exe` for the
first time. Users click **"More info" → "Run anyway"** and the app works normally.

This is acceptable for:
- Personal use
- Small open-source projects
- Projects with no budget for certificates (~$250–$500/year)

---

## What Users See

On first launch, Windows Defender SmartScreen may show:

> "Windows protected your PC"
> Microsoft Defender SmartScreen prevented an unrecognized app from starting.

**To proceed:**
1. Click **More info**
2. Click **Run anyway**
3. The app launches normally

This only happens once per EXE version. Subsequent launches of the same file
don't show the warning.

---

## If You Change Your Mind Later

If you ever want to eliminate the warning, purchase a code signing certificate
from DigiCert, Sectigo, or GlobalSign (~$250–$500/year), then add a `signtool.exe`
step to `.github/workflows/release.yml` between "Bundle FFmpeg" and
"Create release zip."

---

## Verification

- [x] App runs without code signing (verified)
- [x] FFmpeg + ffprobe bundle alongside EXE (verified)
- [x] Users can click "Run anyway" on SmartScreen warning
