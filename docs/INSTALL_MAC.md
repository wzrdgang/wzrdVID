# Install WZRD.VID on Mac

The current packaged app is intended for Apple Silicon Macs. Intel Mac users should run from source for now.

## Download

1. Go to the [latest WZRD.VID release](https://github.com/wzrdgang/wzrdVID/releases/latest).
2. Download `WZRD.VID-macOS.dmg`.
3. Do **not** download `Source code (zip)` unless you want to run/build from source.

`WZRD.VID-macOS.zip` remains available as a fallback packaged-app download. This build is tested primarily on Apple Silicon Macs. Intel Mac users should run from source for now; universal or Intel-native packaging is planned later.

## Install

1. Open `WZRD.VID-macOS.dmg`.
2. Drag `WZRD.VID.app` onto the `Applications` shortcut.
3. Choose **Replace** when updating an existing installation.

## If macOS Blocks It

WZRD.VID is currently ad-hoc signed and unnotarized.

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
4. Download the latest `WZRD.VID-macOS.dmg`.
5. Open it and drag `WZRD.VID.app` onto `Applications`.
6. Choose **Replace**, then use right-click **Open** if macOS blocks the first launch.

There is no automatic updater yet. Signed/notarized builds and real auto-update support are planned after Apple Developer approval.

The update checker only tells you when a newer release exists and opens the download page. It does not auto-download or replace the app.

## Common First-Run Issues

- **I downloaded Source code (zip).** That archive is only for developers. Go back to Releases and download `WZRD.VID-macOS.dmg`; `WZRD.VID-macOS.zip` is the packaged fallback.
- **macOS says the app is blocked.** Right-click `WZRD.VID.app`, choose **Open**, then confirm.
- **The app says ffmpeg is missing.** Run `brew install ffmpeg`, then open WZRD.VID again.
- **I am on an Intel Mac.** Use the source-run instructions in `README.md` for now. The packaged release is currently Apple Silicon-focused.
