# Install WZRD.VID on Mac

## Download

1. Go to the [latest WZRD.VID release](https://github.com/wzrdgang/wzrdVID/releases/latest).
2. Download `WZRD.VID-macOS.zip`.
3. Do **not** download `Source code (zip)` unless you want to run/build from source.

## Install

1. Unzip `WZRD.VID-macOS.zip`.
2. Open `WZRD.VID.app`.
3. Optional: move `WZRD.VID.app` to your `Applications` folder.

## If macOS Blocks It

WZRD.VID is currently unsigned/unnotarized.

Right-click `WZRD.VID.app`, choose **Open**, then confirm you want to open it.

## If ffmpeg Is Missing

WZRD.VID needs `ffmpeg` and `ffprobe` for rendering.

Install with Homebrew:

```bash
brew install ffmpeg
```

Then open WZRD.VID again.

## Update

1. Open WZRD.VID.
2. Check the update status in the **Output** tab.
3. If a newer version is available, click **Download Update**.
4. Download the latest `WZRD.VID-macOS.zip`.
5. Unzip it.
6. Replace your old `WZRD.VID.app`.

There is no automatic updater yet. Signed/notarized builds and real auto-update support are planned after Apple Developer approval.
