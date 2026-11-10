# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-11-10

### Added

- **Phase 8 — Documentation & Operations.** User manual (`USER_MANUAL.md`),
  troubleshooting guide (`TROUBLESHOOTING.md`), release notes template
  (`RELEASE_NOTES_TEMPLATE.md`), code signing documentation (`CODESIGNING.md`).
- **Auto-download and install updates** — Windows auto-updater downloads the
  release ZIP, extracts it, and replaces the running EXE via a helper batch
  script (macOS/Linux still open the download page).
- **Cross-platform CI builds** — `.github/workflows/release.yml` now builds
  Windows (EXE + ZIP), macOS (.app + tar.gz), and Linux (binary + tar.gz)
  in parallel and aggregates all assets into a single GitHub Release.

### Changed

- `CURRENT_VERSION` bumped to `2.3.0`.
- `_check_updates_prompt()` now offers "Download & Install" (Windows) in
  addition to "Open download page".

## [2.2.0] - 2026-11-10

### Added

- **Phase 7 — UX Enhancements.** Download history UI with re-download and
  CSV export (`tests/test_validation.py` + `tests/test_integration.py`).
  Dark/Light/System theme toggle. Keyboard shortcuts: Ctrl+V paste,
  Ctrl+Enter start, Ctrl+S save, Ctrl+O browse, Escape stop,
  Ctrl+H toggle history, F1 about. Portable mode (state stored next to
  executable when a `portable` file is present). Auto-updater client
  that checks GitHub releases on startup and prompts to download.
- **`add_history_entry()` and `export_history_csv()` helpers** for
  tracking and exporting download history.

### Changed

- `CURRENT_VERSION` bumped to `2.2.0`.
- `_download_convert()` and `rip_single_url()` now record every
  completed download to history.

## [2.1.0] - 2026-11-10

### Added

- **Phase 6 — Testing & CI.** Integration tests (`tests/test_integration.py`)
  for end-to-end download → convert → cover-art embedding against real
  YouTube URLs, gated behind `--run-integration`. Performance benchmark
  script (`scripts/benchmark_downloads.py`) measuring concurrent download
  throughput vs. worker count. CI gains coverage reporting (`pytest-cov` +
  Codecov) and optional workflow-dispatch jobs for integration and
  benchmark runs.
- **Standalone `rip_single_url()` helper** — download, convert, embed
  metadata and cover art without the GUI, usable from scripts and tests.
- **Standalone `_fetch_playlist_entries()` helper** — resolve playlist
  URLs to individual video URLs without downloading.

### Changed

- `CURRENT_VERSION` bumped to `2.1.0`.
- CI `test` job now runs with `--cov=rip_gui` and uploads to Codecov.

## [1.0.0]  -  2026-10-20

### Added

- **Real CI test gate.** The workflow ran `pytest -q || echo "No tests yet"`,
  which executes no tests and always exits zero. It is replaced with a
  pinned `pytest==8.3.3` installation and an unconditional `pytest -q`.
  The suite has 88 tests.
- **Dependency pin guard** (`scripts/pin_guard.py`), wired as a required
  `pin-check` status check.

### Fixed

- **Hardcoded absolute paths.** The project and Desktop paths were
  embedded in the source, so the project could not run from a clone.
- **Missing `pywin32` dependency**, required on Windows and previously
  undeclared.
- **Syntax and runtime errors in `test_demo.py` and `test_simple.py`**:
  an unclosed dictionary, a misplaced parenthesis, invalid `self.`
  references, an uninitialised `results` variable, and a reference to a
  [lorem]-existent `result['is_ai']` key.
- **Launcher scripts are location-independent**, including the Android
  Termux setup script.

### Changed

- The Ruff rule set is pinned to `E4,E7,E9,F` with `ruff==0.17.1`.
- **README author credit** added: Conrad CJ Wilson.

### Security

- Secret scanning and push protection enabled at the repository level.

## [0.1.0]

- Initial release: paste a link, get a FLAC with the track title as filename

[1.0.0]: https://github.com/cjps4linux-creator/youtube-audio-ripper/releases/tag/v1.0.0
