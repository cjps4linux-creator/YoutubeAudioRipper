@echo off
REM Build Windows standalone executable for YouTube Audio Ripper
REM Run from the repo root: build\build_windows.bat

echo ============================================
echo YouTube Audio Ripper - Windows Build
echo ============================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found on PATH
    exit /b 1
)

REM Check PyInstaller
python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    python -m pip install pyinstaller
)

REM Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo Building standalone executable...
python -m PyInstaller build/youtube_ripper.spec --noconfirm --clean

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)

echo ============================================
echo Build complete: dist\YouTube Audio Ripper.exe
echo ============================================

pause
