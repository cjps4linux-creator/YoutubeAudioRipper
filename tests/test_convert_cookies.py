"""Unit tests for ``android/convert_cookies.py``.

The module converts a Brave DevTools TSV cookie export into a Netscape
cookie file that yt-dlp understands.

Documented TSV layout (column index -> meaning)::

    0 Name | 1 Value | 2 Domain | 3 Path | 4 Expires
    5 Size | 6 HttpOnly | 7 HostOnly | 8 Secure | 9 SameSite

Each emitted line carries seven tab separated fields::

    domain <TAB> domain_flag <TAB> path <TAB> secure_flag <TAB> expiry <TAB> name <TAB> value

Two behaviours of the implementation are worth calling out because they are
surprising and are locked in by the tests below:

* The Netscape "domain flag" (2nd field, normally *include sub-domains*) is
  derived from the **HttpOnly** column, not from HostOnly.  A cookie whose
  HttpOnly value is ``TRUE`` therefore gets the flag ``FALSE`` and every
  other cookie gets ``TRUE``.  The tests assert this actual behaviour.
* The "secure flag" (4th field) is ``TRUE`` when the Secure column equals
  ``TRUE`` or is the check-mark character ``U+2713``.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timezone

import pytest

convert_cookies = importlib.import_module("convert_cookies")

HEADER = "# Netscape HTTP Cookie File"

# A well formed Brave DevTools row:  Name, Value, Domain, Path, Expires,
# Size, HttpOnly, HostOnly, Secure, SameSite
FULL_ROW = (
    "SID",
    "example_123",
    ".youtube.com",
    "/",
    "2025-01-01T00:00:00Z",
    "42",
    "FALSE",
    "TRUE",
    "TRUE",
    "Lax",
)


def make_row(**overrides):
    """Build a TSV row, overriding any of the ten documented columns."""
    fields = [
        overrides.get("name", FULL_ROW[0]),
        overrides.get("value", FULL_ROW[1]),
        overrides.get("domain", FULL_ROW[2]),
        overrides.get("path", FULL_ROW[3]),
        overrides.get("expires", FULL_ROW[4]),
        overrides.get("size", FULL_ROW[5]),
        overrides.get("http_only", FULL_ROW[6]),
        overrides.get("host_only", FULL_ROW[7]),
        overrides.get("secure", FULL_ROW[8]),
        overrides.get("samesite", FULL_ROW[9]),
    ]
    return "\t".join(fields)


def write_tsv(path, rows):
    """Write ``rows`` (raw strings) to ``path`` and return it as a string."""
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return str(path)


def read_output(path):
    return path.read_text(encoding="utf-8")


def parse_netscape(path):
    """Parse a Netscape cookie file into a list of 7-field tuples."""
    lines = read_output(path).splitlines()
    return [tuple(line.split("\t")) for line in lines[2:] if line.strip()]


def _is_utc():
    """True when the machine's local timezone is UTC (SAST differs by 2h)."""
    return datetime.now().astimezone().utcoffset().total_seconds() == 0


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_convert_returns_true_and_reports_count(tmp_path, capsys):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row()])
    target = tmp_path / "out" / "cookies.txt"

    assert convert_cookies.convert(str(source), str(target)) is True

    out = capsys.readouterr().out
    assert "Converted 1 cookies" in out
    assert str(target) in out


def test_output_has_netscape_header_and_blank_line(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row()])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    lines = read_output(target).splitlines()
    assert lines[0] == HEADER
    assert lines[1] == ""
    assert lines[2].startswith(".youtube.com\t")


def test_happy_path_field_order_and_values(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row()])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert len(rows) == 1
    domain, domain_flag, path, secure_flag, expiry, name, value = rows[0]
    assert domain == ".youtube.com"
    assert domain_flag == "TRUE"
    assert path == "/"
    assert secure_flag == "TRUE"
    assert expiry == str(int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()))
    assert name == "SID"
    assert value == "example_123"


def test_multiple_cookies_are_all_written_in_order(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(
        source,
        [
            make_row(name="FIRST", value="1", domain=".a.test"),
            make_row(name="SECOND", value="2", domain=".b.test"),
            make_row(name="THIRD", value="3", domain=".c.test"),
        ],
    )
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert [row[5] for row in rows] == ["FIRST", "SECOND", "THIRD"]
    assert [row[0] for row in rows] == [".a.test", ".b.test", ".c.test"]


def test_value_may_contain_equals_and_spaces(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(value="a=b c d")])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][6] == "a=b c d"


# ---------------------------------------------------------------------------
# Missing input file
# ---------------------------------------------------------------------------


def test_missing_input_returns_false(tmp_path, capsys):
    missing = tmp_path / "nope.tsv"
    target = tmp_path / "cookies.txt"

    assert convert_cookies.convert(str(missing), str(target)) is False

    assert "Input file not found" in capsys.readouterr().out
    assert not target.exists()


# ---------------------------------------------------------------------------
# Skipped lines: blank, comments, too few fields
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "skipped_line"),
    [
        ("blank", ""),
        ("whitespace_only", "   "),
        ("comment_hash", "# a DevTools comment"),
        ("comment_with_tabs", "#\tname\tvalue"),
        ("netlike_comment", "# Netscape HTTP Cookie File"),
    ],
)
def test_blank_and_comment_lines_are_skipped(tmp_path, label, skipped_line):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [skipped_line, make_row(name="KEPT")])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert [row[5] for row in rows] == ["KEPT"], f"{label} line was not skipped"


@pytest.mark.parametrize(
    "short_line",
    [
        "one",
        "one\ttwo",
        "one\ttwo\tthree",
        "one\ttwo\tthree\tfour",
        "one\ttwo\tthree\tfour\tfive",
        "one\ttwo\tthree\tfour\tfive\tsix",
    ],
)
def test_lines_with_fewer_than_seven_fields_are_skipped(tmp_path, short_line):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [short_line, make_row(name="KEPT")])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert [row[5] for row in rows] == ["KEPT"]


def test_seven_fields_is_enough_to_be_kept(tmp_path):
    """Exactly seven fields is the acceptance threshold."""
    seven = "\t".join(["N", "V", ".d.test", "/", "1700000000", "0", "FALSE"])
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [seven])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert len(rows) == 1
    assert rows[0][0] == ".d.test"
    # Columns 8/9 are absent -> Secure defaults to FALSE.
    assert rows[0][3] == "FALSE"


def test_empty_input_file_produces_header_only(tmp_path):
    source = tmp_path / "cookies.tsv"
    source.write_text("", encoding="utf-8")
    target = tmp_path / "cookies.txt"

    assert convert_cookies.convert(str(source), str(target)) is True

    assert read_output(target) == HEADER + "\n\n"


# ---------------------------------------------------------------------------
# Expiry parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("expires", "expected_epoch"),
    [
        # Timezone-aware ISO strings are UTC based, so the epoch is stable.
        ("2025-01-01T00:00:00Z", 1735689600),
        ("2025-01-01T00:00:00+00:00", 1735689600),
        ("2025-06-01T12:30:45Z", 1748781045),
        ("2025-06-01T12:30:45.123Z", 1748781045),
        # Naive ISO strings carry no offset, so they are read as LOCAL time.
        ("2025-01-01", int(datetime(2025, 1, 1).timestamp())),
        ("20250101", int(datetime(2025, 1, 1).timestamp())),
    ],
)
def test_iso_expiry_is_converted_to_epoch(tmp_path, expires, expected_epoch):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(expires=expires)])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][4] == str(expected_epoch)


@pytest.mark.parametrize(
    ("expires", "expected_epoch"),
    [
        ("1700000000", 1700000000),
        ("1700000000.75", 1700000000),
        ("0", 0),
        ("-1", -1),
    ],
)
def test_numeric_expiry_falls_back_to_float_int(tmp_path, expires, expected_epoch):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(expires=expires)])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][4] == str(expected_epoch)


@pytest.mark.parametrize(
    "expires",
    ["not-a-date", "", "   ", "yesterday", "null", "NaN", "inf"],
)
def test_unparseable_expiry_becomes_zero(tmp_path, expires):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(expires=expires)])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][4] == "0"


def test_iso_with_z_suffix_uses_utc_not_local_time(tmp_path):
    """``Z`` is rewritten to ``+00:00`` so the epoch is timezone independent."""
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(expires="2025-01-01T00:00:00Z")])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][4] == str(int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()))


def test_naive_iso_expiry_is_interpreted_as_local_time(tmp_path):
    """ACTUAL behaviour: a timestamp without an offset is read as local time.

    ``datetime.fromisoformat`` returns a naive datetime for values such as
    ``2025-01-01``; ``.timestamp()`` then interprets it in the machine's local
    timezone.  Only the ``Z`` suffix (rewritten to ``+00:00``) makes the
    result timezone independent.
    """
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(expires="2025-01-01")])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][4] == str(int(datetime(2025, 1, 1).timestamp()))
    assert rows[0][4] != str(int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())) or _is_utc()


# ---------------------------------------------------------------------------
# Secure flag
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("secure_column", "expected_flag"),
    [
        ("TRUE", "TRUE"),
        ("true", "TRUE"),
        ("True", "TRUE"),
        ("✓", "TRUE"),
        ("FALSE", "FALSE"),
        ("false", "FALSE"),
        ("", "FALSE"),
        ("yes", "FALSE"),
        ("1", "FALSE"),
    ],
)
def test_secure_flag_variants(tmp_path, secure_column, expected_flag):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(secure=secure_column)])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][3] == expected_flag


def test_secure_column_missing_defaults_to_false(tmp_path):
    seven = "\t".join(["N", "V", ".d.test", "/", "1700000000", "0", "FALSE"])
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [seven])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][3] == "FALSE"


# ---------------------------------------------------------------------------
# Domain flag (derived from HttpOnly -- surprising, but asserted as-is)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("http_only", "expected_domain_flag"),
    [
        ("TRUE", "FALSE"),
        ("true", "FALSE"),
        ("True", "FALSE"),
        ("FALSE", "TRUE"),
        ("false", "TRUE"),
        ("", "TRUE"),
        ("0", "TRUE"),
        ("1", "TRUE"),
    ],
)
def test_domain_flag_is_derived_from_http_only_column(tmp_path, http_only, expected_domain_flag):
    """ACTUAL behaviour: the Netscape domain flag mirrors the HttpOnly column.

    In the Netscape cookie format the second field means "include sub-domains"
    and should come from Brave's *HostOnly* column.  The implementation reads
    *HttpOnly* instead, so the flag is inverted relative to the intent.
    """
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(http_only=http_only)])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][1] == expected_domain_flag


def test_host_only_column_does_not_influence_the_domain_flag(tmp_path):
    """The HostOnly column (index 7) is parsed but never used."""
    source = tmp_path / "cookies.tsv"
    write_tsv(
        source,
        [
            make_row(name="HOST_ONLY_TRUE", host_only="TRUE", http_only="FALSE"),
            make_row(name="HOST_ONLY_FALSE", host_only="FALSE", http_only="FALSE"),
        ],
    )
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert [row[1] for row in rows] == ["TRUE", "TRUE"]


def test_http_only_true_inverts_the_domain_flag(tmp_path):
    """A single HttpOnly cookie proves the flag is tied to column 6."""
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(http_only="TRUE")])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    rows = parse_netscape(target)
    assert rows[0][1] == "FALSE"


# ---------------------------------------------------------------------------
# Output file creation
# ---------------------------------------------------------------------------


def test_output_file_is_created(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row()])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    assert target.is_file()
    assert target.stat().st_size > 0


def test_output_parent_directories_are_created(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row()])
    target = tmp_path / "deeply" / "nested" / "dir" / "cookies.txt"

    assert not target.parent.exists()

    convert_cookies.convert(str(source), str(target))

    assert target.is_file()


def test_existing_output_file_is_overwritten(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row(name="FRESH")])
    target = tmp_path / "cookies.txt"
    target.write_text("stale content that must disappear\n", encoding="utf-8")

    convert_cookies.convert(str(source), str(target))

    assert "stale content" not in read_output(target)
    assert parse_netscape(target)[0][5] == "FRESH"


def test_output_ends_with_a_newline(tmp_path):
    source = tmp_path / "cookies.tsv"
    write_tsv(source, [make_row()])
    target = tmp_path / "cookies.txt"

    convert_cookies.convert(str(source), str(target))

    assert read_output(target).endswith("\n")
