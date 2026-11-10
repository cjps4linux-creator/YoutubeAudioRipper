# Code Signing — Administrative Task

**Status:** Pending (not yet implemented)  
**Owner:** Conrad CJ Wilson  
**Priority:** High (Windows users see "Unknown publisher" warning)

---

## Problem

Windows SmartScreen and Defender show an "Unknown publisher" warning when
running or installing `YouTube Audio Ripper.exe` because the executable is not
digitally signed. This discourages users and may trigger automatic quarantine.

## Solution

Purchase a **code signing certificate** from a trusted Certificate Authority
(CA) and sign all distributable artifacts:

| Artifact | Signing Required | Tool |
|----------|-----------------|------|
| `YouTube Audio Ripper.exe` | Yes | `signtool.exe` (Windows SDK) |
| `YouTube-Audio-Ripper-*.zip` | Yes | `signtool.exe` |
| Inno Setup `.exe` installer | Yes | `signtool.exe` |

## Recommended Certificate Authorities

| CA | Product | Approx. Cost | Validation |
|----|---------|-------------|------------|
| DigiCert | Code Signing Certificate | ~$500/year | Organisation validation |
| Sectigo (formerly Comodo) | Code Signing Certificate | ~$250/year | Organisation validation |
| GlobalSign | Code Signing Certificate | ~$400/year | Organisation validation |

> EV (Extended Validation) code signing certificates provide immediate
> SmartScreen reputation but cost more (~$600–$800/year). Standard OV
> certificates build reputation over time.

## Implementation Steps

1. **Purchase** a code signing certificate from DigiCert, Sectigo, or GlobalSign.
2. **Complete organisation validation** (provide business documents, D-U-N-S number).
3. **Install the certificate** on the build machine (Windows with Windows SDK).
4. **Add a CI step** to sign artifacts before upload:

   ```yaml
   - name: Sign Windows EXE
     shell: pwsh
     run: |
       & "C:\Program Files (x86)\Windows Kits\10\bin\<arch>\signtool.exe" sign `
         /f "path/to/certificate.pfx" `
         /p "$env:CODESIGN_PASSWORD" `
         /tr "http://timestamp.digicert.com" `
         /td SHA256 `
         /fd SHA256 `
         "dist/YouTube Audio Ripper/YouTube Audio Ripper.exe"
   ```

5. **Store the certificate password** as a GitHub Secret (`CODESIGN_PASSWORD`).
6. **Verify signatures** after signing:

   ```powershell
   signtool.exe verify /pa /v "dist/YouTube Audio Ripper/YouTube Audio Ripper.exe"
   ```

## CI Integration

Add the signing step to `.github/workflows/release.yml` between the "Bundle FFmpeg"
and "Create release zip" steps. The signing job must run on `windows-latest`
where `signtool.exe` is available.

## Verification

After signing, confirm:

- [ ] `signtool verify` passes for all artifacts
- [ ] Windows SmartScreen no longer shows "Unknown publisher"
- [ ] File Properties → Digital Signatures shows the certificate
- [ ] SHA256 checksums match between signed and unsigned builds

---

**Note:** This is an administrative task requiring a financial decision and
organisation validation. It cannot be fully automated in CI without the
certificate file and password.
