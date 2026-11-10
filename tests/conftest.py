"""Shared fixtures and safety hooks for the Youtube Audio Ripper test-suite.

Design constraints
------------------
* The suite is PURE: no network, no GUI window, no subprocess.
* The repo root contains interactive/network/GUI scripts named ``test_*.py``.
  ``pytest.ini`` pins collection to ``tests/``; the hook below turns that
  promise into an assertion that fails the run if it is ever broken.
* ``create_desktop_shortcut.py`` and ``create_shortcut.py`` execute code at
  import time (they delete/create files on the user's Desktop) and
  ``create_simple_ico()`` writes ``app_icon.ico`` next to the script.  The
  ``load_script`` fixture therefore imports a *copy* of such a script from
  ``tmp_path`` with a patched ``HOME``, so the real Desktop and the real
  repository are never touched.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_DIR = Path(__file__).resolve().parent
ANDROID_DIR = REPO_ROOT / "android"

# Captured before any monkeypatching so tests can prove isolation.
_REAL_EXPANDUSER = os.path.expanduser
REAL_HOME = Path(_REAL_EXPANDUSER("~"))

# Make the importable modules reachable: `convert_cookies` lives in android/,
# the shortcut helpers live in the repo root.
for _extra_path in (str(REPO_ROOT), str(ANDROID_DIR)):
    if _extra_path not in sys.path:
        sys.path.insert(0, _extra_path)


def pytest_collection_modifyitems(session, config, items):
    """Fail the run if pytest ever collects a file outside ``tests/``.

    This guards the CI gate: the root-level ``test_*.py`` scripts are manual
    tools, and importing them downloads from YouTube or opens a GUI window.
    The check runs at collection time (before any test executes) and raises
    ``pytest.UsageError`` so pytest reports a clean failure instead of an
    internal error.
    """
    offenders = sorted(
        item.nodeid for item in items if not Path(str(item.path)).resolve().is_relative_to(TESTS_DIR)
    )
    if offenders:
        raise pytest.UsageError(
            "pytest collected files outside tests/:\n  "
            + "\n  ".join(offenders)
            + "\n\nThe repository root holds manual/network/GUI scripts named "
            "test_*.py that must never be collected.  Keep `testpaths = tests` "
            "in pytest.ini."
        )


@pytest.fixture
def real_home():
    """The genuine user home directory.

    ``Path.home()`` calls ``os.path.expanduser("~")`` at call time, so it
    would return the *fake* home while the ``load_script`` fixture has
    ``os.path.expanduser`` patched.  Tests that need to prove the real
    Desktop was left untouched must use this fixture instead.
    """
    return REAL_HOME


@pytest.fixture
def load_script(tmp_path, monkeypatch):
    """Import a repository script as an isolated, side-effect-free copy.

    The copy lives in ``tmp_path`` so that module-level constants such as
    ``app_dir``/``icon_path`` resolve inside the temporary directory.
    ``os.path.expanduser("~")`` is redirected to a fake home directory, so
    Desktop clean-up / shortcut creation stays inside ``tmp_path``.
    """

    def _load(rel_path, module_name=None, dispatch=None, hide_pywin32=False, prepare=None):
        source = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        work = tmp_path / "script"
        work.mkdir(parents=True, exist_ok=True)
        dest = work / Path(rel_path).name
        dest.write_text(source, encoding="utf-8")

        home = work / "home"
        (home / "Desktop").mkdir(parents=True, exist_ok=True)
        if prepare is not None:
            prepare(home)

        def fake_expanduser(path):
            if path == "~":
                return str(home)
            return _REAL_EXPANDUSER(path)

        monkeypatch.setattr(os.path, "expanduser", fake_expanduser)

        recorder = None
        if hide_pywin32:
            # Make `from win32com.client import Dispatch` raise ImportError.
            stub = types.ModuleType("win32com.client")
            package = types.ModuleType("win32com")
            package.client = stub
            monkeypatch.setitem(sys.modules, "win32com", package)
            monkeypatch.setitem(sys.modules, "win32com.client", stub)
        else:
            # Never touch real COM: replace Dispatch with a recording double.
            recorder = dispatch if dispatch is not None else DispatchRecorder()
            try:
                import win32com.client
            except ImportError:
                # pywin32 is not installed (e.g. Linux CI).  Provide a stub
                # module so the script under test still imports and the
                # recording double is used -- tests stay identical on every
                # platform.
                stub = types.ModuleType("win32com.client")
                stub.Dispatch = recorder
                package = types.ModuleType("win32com")
                package.client = stub
                monkeypatch.setitem(sys.modules, "win32com", package)
                monkeypatch.setitem(sys.modules, "win32com.client", stub)
            else:
                monkeypatch.setattr(win32com.client, "Dispatch", recorder, raising=False)

        name = module_name or f"_isolated_{dest.stem}"
        spec = importlib.util.spec_from_file_location(name, dest)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(name, None)
        module.dispatch_recorder = recorder
        return module

    return _load


class DispatchRecorder:
    """Stand-in for ``win32com.client.Dispatch`` that never touches COM.

    It records the requested ProgID and hands out a shortcut object whose
    attribute assignments are captured, so tests can assert on the shortcut
    configuration without creating a real ``.lnk`` file.
    """

    def __init__(self):
        self.progids = []
        self.shortcuts = []
        self.shells = []

    def __call__(self, progid):
        self.progids.append(progid)
        shortcut = ShortcutDouble()
        shell = ShortcutShell(shortcut)
        self.shortcuts.append(shortcut)
        self.shells.append(shell)
        return shell


class ShortcutDouble:
    """Captures the properties a .lnk shortcut would be given."""

    def __init__(self):
        self.Targetpath = ""
        self.Arguments = ""
        self.WorkingDirectory = ""
        self.Description = ""
        self.IconLocation = ""
        self.saved = False

    def save(self):
        self.saved = True


class ShortcutShell:
    """Minimal ``WScript.Shell`` double."""

    def __init__(self, shortcut):
        self._shortcut = shortcut
        self.paths = []

    def CreateShortCut(self, path):  # noqa: N802 - mirrors the COM API name
        self.paths.append(path)
        return self._shortcut
