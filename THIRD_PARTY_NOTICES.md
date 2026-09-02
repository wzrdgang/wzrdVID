# Third-Party Notices

The WZRD.VID Freeware License applies only to AMPYX-owned portions of WZRD.VID. It does not replace or narrow any third-party license. Where a third-party license grants broader rights, that license controls for its component.

## Current Public Repository

The current public `main` branch distributes the static WZRD.VID website, the dependency-free browser-side WZRD.VID Lite implementation, public assets, documentation, and legal records. It does not distribute a packaged desktop application or the current proprietary desktop source/build tree.

WZRD.VID Lite uses browser-provided File, object URL, Canvas, Web Audio, and MediaRecorder APIs. It has no server upload path and no bundled third-party JavaScript runtime dependency.

## Historical Copies

Historical source snapshots and tags retain the notices and licenses present in those copies. Historical packaged binaries have been withdrawn from GitHub Releases, while their release records, source tags, provenance records, and previously granted rights remain available or preserved as applicable.

The historical artifact records do not describe a currently downloadable binary and do not retroactively adopt the qualified future-build inventory below.

## Qualified Desktop Distribution Architecture

A separately qualified future macOS application bundle is designed to include exact notices, license texts, source provenance, SPDX data, native-code provenance, and replacement materials under `WZRD.VID.app/Contents/Resources/Legal/`.

The qualified inventory includes these principal bundled components:

| Component | Qualified version | Principal license |
| --- | --- | --- |
| CPython | 3.14.4 | Python-2.0 |
| OpenSSL | 3.6.2 | Apache-2.0 |
| mpdecimal | 4.0.1 | BSD-2-Clause |
| Zstandard | 1.5.7 | BSD-3-Clause |
| PySide6 / PySide6 Essentials / Shiboken6 | 6.11.2 | LGPL-3.0-only |
| Qt Base frameworks and plugins | 6.11.2 | LGPL-3.0-only |
| Qt Image Formats ICNS/WebP plugins | 6.11.2 | LGPL-3.0-only |
| NumPy | 2.5.2 | BSD-3-Clause plus incorporated notices |
| Pillow | 12.3.0 | MIT-CMU plus incorporated dependency notices |
| PyInstaller loader/bootloader runtime | 6.22.2 | GPL-2.0-or-later WITH Bootloader-exception |
| PyInstaller runtime hooks/utilities | 6.22.2 | Apache-2.0 |

OpenCV is not a production dependency in that qualified architecture. A controlled FFmpeg 8.1.2 helper is designed as an independent `ffmpeg`/`ffprobe` process pair built under an LGPL-only capability profile without GPL, nonfree, libx264, libx265, or Rubber Band components.

This summary is not a substitute for the exact Legal directory accompanying a qualified binary. No qualified desktop binary is currently available from this repository.

## Third-Party Rights And Materials

Nothing in the WZRD.VID Freeware License restricts rights supplied by an applicable third-party license or applicable law, including required rights to inspect, debug, modify, replace, relink, reverse engineer for interoperability, or redistribute a third-party component.

Qualified bundles are designed to carry the corresponding exact source and Qt replacement/relinking materials or their documented access path. Use the official public support channel for questions about third-party materials associated with an official WZRD.VID copy.

Third-party names and marks remain the property of their respective owners. This notice is an engineering summary, not legal advice or a claim of attorney review.
