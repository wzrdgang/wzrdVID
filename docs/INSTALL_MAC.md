# Install WZRD.VID on Mac

The current packaged ZIP is intended for Apple Silicon Macs. Intel Mac users should run from source for now.

## Download

1. Go to the [latest WZRD.VID release](https://github.com/wzrdgang/wzrdVID/releases/latest).
2. Download `WZRD.VID-macOS.zip`.
3. Do **not** download `Source code (zip)` unless you want to run/build from source.

Current packaged ZIP note: this build is tested primarily on Apple Silicon Macs. Intel Mac users should run from source for now; universal or Intel-native packaging is planned later.

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
2. Check the update status in the app header.
3. If a newer version is available, click **Download Update**.
4. Download the latest `WZRD.VID-macOS.zip`.
5. Unzip it.
6. Replace your old `WZRD.VID.app`.

There is no automatic updater yet. Signed/notarized builds and real auto-update support are planned after Apple Developer approval.

The update checker only tells you when a newer release exists and opens the download page. It does not auto-download or replace the app.

## Common First-Run Issues

- **I downloaded Source code (zip).** That archive is only for developers. Go back to Releases and download `WZRD.VID-macOS.zip`.
- **macOS says the app is blocked.** Right-click `WZRD.VID.app`, choose **Open**, then confirm.
- **The app says ffmpeg is missing.** Run `brew install ffmpeg`, then open WZRD.VID again.
- **I am on an Intel Mac.** Use the source-run instructions in `README.md` for now. The release ZIP is currently Apple Silicon-focused.
