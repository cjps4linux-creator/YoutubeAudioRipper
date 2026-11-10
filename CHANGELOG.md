# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
