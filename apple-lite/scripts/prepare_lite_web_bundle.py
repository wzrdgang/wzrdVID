#!/usr/bin/env python3
"""Prepare bundled static assets for the WZRD.VID Lite Apple wrapper."""

from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEST_ROOT = REPO_ROOT / "apple-lite" / "WZRDVIDLite" / "Resources" / "LiteWeb"


def copy_tree(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Missing required source: {source}")
    shutil.copytree(source, destination)


def main() -> int:
    docs = REPO_ROOT / "docs"
    if DEST_ROOT.exists():
        shutil.rmtree(DEST_ROOT)
    DEST_ROOT.mkdir(parents=True)

    copy_tree(docs / "lite", DEST_ROOT / "lite")
    shutil.copy2(docs / "i18n.js", DEST_ROOT / "i18n.js")

    assets_dest = DEST_ROOT / "assets"
    assets_dest.mkdir()
    for folder in ("branding", "logo", "ui"):
        copy_tree(docs / "assets" / folder, assets_dest / folder)

    required = [
        DEST_ROOT / "lite" / "index.html",
        DEST_ROOT / "lite" / "app.js",
        DEST_ROOT / "lite" / "styles.css",
        DEST_ROOT / "i18n.js",
        DEST_ROOT / "assets" / "branding" / "wzrdvid_favicon_32.png",
        DEST_ROOT / "assets" / "ui" / "jazz_backdrop_field.png",
        DEST_ROOT / "assets" / "logo" / "wzrdvid-github-banner.png",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing: {path}")
        return 1

    file_count = sum(1 for path in DEST_ROOT.rglob("*") if path.is_file())
    print(f"Prepared {file_count} files in {DEST_ROOT}")
    print("Add this LiteWeb folder to the Xcode app target as a folder reference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
