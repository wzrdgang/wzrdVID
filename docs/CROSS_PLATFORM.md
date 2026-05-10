# Cross-Platform Source Runs

WZRD.VID is developed and packaged primarily on Apple Silicon macOS. Windows and Linux source runs are supported on a best-effort, experimental basis so people can try the app without waiting for native packages.

The current packaged Mac release ZIP is tested primarily on Apple Silicon Macs. Intel Mac users should run from source until universal or Intel-native packaging exists.

Packaged Windows and Linux builds are not currently official. The Apple Silicon macOS release app remains the primary downloadable build.

## Requirements

- Python 3.10+
- ffmpeg and ffprobe available on PATH
- Python dependencies from `requirements.txt`

## Install ffmpeg

macOS:

```sh
brew install ffmpeg
```

Debian/Ubuntu:

```sh
sudo apt update
sudo apt install ffmpeg
```

Fedora:

```sh
sudo dnf install ffmpeg
```

Arch:

```sh
sudo pacman -S ffmpeg
```

Windows:

```powershell
winget install Gyan.FFmpeg
```

Or download ffmpeg from <https://ffmpeg.org/download.html>. Make sure `ffmpeg.exe` and `ffprobe.exe` are on PATH before launching WZRD.VID.

## Run From Source

macOS/Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Windows Command Prompt:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python run.py
```

There is also a convenience launcher for Windows:

```bat
run_windows.bat
```

## Known Caveats

- Apple Silicon macOS is the only platform with an official packaged app today.
- Intel Macs should run from source for now; universal or Intel-native packaging is planned later.
- Windows/Linux source runs depend on the local Python, PySide6, OpenCV, and ffmpeg installations.
- HEIC/HEIF photo support depends on installed imaging libraries and may not be available everywhere.
- Some fonts differ across systems. The UI falls back to common Windows/Linux monospace fonts.
- File dialogs and video codec support may vary by platform.

## Packaging Roadmap

Possible future packaging targets:

- Windows: PyInstaller `.exe` installer or zip build
- Linux: AppImage, Flatpak, or `.deb` if there is demand

Those are not promised yet. For now, Windows and Linux users should run from source.
