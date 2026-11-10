"""
Unit tests for YouTube Audio Ripper core logic.

Tests validation, filename sanitization, and deduplication registry.
Run: pytest -q tests/
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add repo root to path so we can import rip_gui modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rip_gui import (  # noqa: E402
    sanitize_filename,
    validate_youtube_url,
    validate_urls,
    is_already_downloaded,
)


# ── URL Validation Tests ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "url,expected_ok",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://youtu.be/dQw4w9WgXcQ", True),
        ("http://youtube.com/watch?v=dQw4w9WgXcQ", True),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s", True),
        ("https://www.youtube.com/watch?v=abcdefghijk", True),
        ("https://www.youtube.com/watch?v=ABCDEFGHIJK", True),
        # Invalid
        ("", False),
        ("not a url", False),
        ("https://google.com", False),
        ("https://www.youtube.com/watch", False),
        ("https://www.youtube.com/watch?v=short", False),  # < 11 chars
        ("https://www.youtube.com/watch?v=toolong123456", False),  # > 11 chars
        (None, False),
    ],
)
def test_validate_youtube_url(url, expected_ok):
    ok, err = validate_youtube_url(url)
    assert ok == expected_ok, f"URL={url!r} expected_ok={expected_ok}, got ok={ok}, err={err}"
    if expected_ok:
        assert err is None
    else:
        assert err is not None


def test_validate_youtube_url_too_long():
    # Valid 11-char ID with a very long query parameter (>2048 chars)
    long_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" + "&" + "x" * 3000
    ok, err = validate_youtube_url(long_url)
    assert ok is False
    assert "too long" in err.lower()


def test_validate_urls_batch():
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
    ]
    valid, errors = validate_urls(urls)
    assert len(valid) == 2
    assert len(errors) == 0


def test_validate_urls_mixed():
    urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "not a url",
        "",
    ]
    valid, errors = validate_urls(urls)
    assert len(valid) == 1
    assert len(errors) == 2


def test_validate_urls_too_many():
    urls = ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"] * 51
    valid, errors = validate_urls(urls)
    assert len(valid) == 0
    assert len(errors) == 1
    assert "too many" in errors[0].lower()


# ── Filename Sanitization Tests ────────────────────────────────────────

@pytest.mark.parametrize(
    "title,expected",
    [
        ("Normal Song Title", "Normal Song Title"),
        (r'Song<>:"\|?*', "Song"),
        ("   Multiple   Spaces   ", "Multiple Spaces"),
        ("A" * 100, "A" * 80),  # truncated to 80 chars
        ("", "Unknown_Track"),
        (None, "Unknown_Track"),
        ("   ", "Unknown_Track"),
    ],
)
def test_sanitize_filename(title, expected):
    result = sanitize_filename(title)
    assert result == expected, f"Title={title!r} expected={expected!r}, got={result!r}"


def test_sanitize_filename_removes_invalid_chars():
    result = sanitize_filename(r'test<>:"\|?*file')
    assert "<" not in result
    assert ">" not in result
    assert ":" not in result
    assert '"' not in result
    assert "/" not in result
    assert "\\" not in result
    assert "|" not in result
    assert "?" not in result
    assert "*" not in result


# ── Deduplication Registry Tests ───────────────────────────────────────


def test_registry_save_and_load_roundtrip(tmp_path):
    registry_file = tmp_path / "downloads.json"
    registry = {"https://example.com/video1": "Song One.flac"}

    registry_file.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    loaded = json.loads(registry_file.read_text(encoding="utf-8"))
    assert loaded == registry


def test_is_already_downloaded_returns_none_for_missing_url():
    registry = {}
    result = is_already_downloaded("https://example.com/new", registry)
    assert result is None


def test_is_already_downloaded_returns_filename_for_existing(tmp_path, monkeypatch):
    import rip_gui

    registry = {"https://example.com/video1": "Song One.flac"}

    # Create the file so it "exists"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "Song One.flac").write_text("fake audio", encoding="utf-8")

    # Monkeypatch load_settings to return our temp output dir
    monkeypatch.setattr(
        rip_gui,
        "load_settings",
        lambda: {"output_dir": str(output_dir)},
    )

    result = is_already_downloaded("https://example.com/video1", registry)
    assert result == "Song One.flac"


def test_is_already_downloaded_returns_none_when_file_missing(tmp_path, monkeypatch):
    import rip_gui

    registry = {"https://example.com/video1": "Missing.flac"}

    # Point to an empty directory via load_settings
    monkeypatch.setattr(
        rip_gui,
        "load_settings",
        lambda: {"output_dir": str(tmp_path / "output")},
    )

    result = is_already_downloaded("https://example.com/video1", registry)
    assert result is None
