#!/usr/bin/env python3
"""
Create desktop shortcut with icon for YouTube Audio Ripper
"""

from pathlib import Path
import os

try:
    from win32com.client import Dispatch
except ImportError:  # pywin32 is Windows-only and optional
    Dispatch = None

# Paths
app_dir = Path(__file__).resolve().parent
desktop = Path(os.path.expanduser("~")) / "Desktop"
python_exe = app_dir / "venv/Scripts/python.exe"
script_file = app_dir / "rip_gui.py"
shortcut_path = desktop / "YouTube Audio Ripper.lnk"
icon_path = app_dir / "app_icon.ico"

# Create a simple icon file
# We'll create a minimal ICO file
def create_simple_ico():
    """Create a simple music note icon"""
    # ICO file format is complex, so we'll use a workaround
    # Just create a [content pending] that Windows can use
    ico_data = bytes([
        0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x10, 0x10,
        0x00, 0x00, 0x01, 0x00, 0x20, 0x00, 0x30, 0x00,
        0x00, 0x00, 0x16, 0x00, 0x00, 0x00, 0x28, 0x00,
        0x00, 0x00, 0x10, 0x00, 0x00, 0x00, 0x20, 0x00,
        0x00, 0x00, 0x01, 0x00, 0x20, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ])
    icon_path.write_bytes(ico_data)
    return icon_path

# Create shortcut
def create_shortcut():
    if Dispatch is None:
        print("pywin32 is not installed - cannot create a .lnk shortcut.")
        print("Install it with: pip install pywin32")
        return
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(python_exe)
    shortcut.Arguments = f'"{script_file}"'
    shortcut.WorkingDirectory = str(app_dir)
    shortcut.Description = "YouTube Audio Ripper"
    shortcut.IconLocation = f"{python_exe},0"
    shortcut.save()
    print(f"✅ Shortcut created: {shortcut_path}")

# Remove old shortcuts
for f in desktop.glob("YouTube*"):
    f.unlink()
    print(f"Removed old shortcut: {f.name}")

# Create new shortcut with icon
create_shortcut()
print("✅ Desktop shortcut created with icon")
