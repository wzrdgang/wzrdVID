"""Cross-platform source launcher for WZRD.VID."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent
    app_path = project_root / "app.py"
    completed = subprocess.run([sys.executable, str(app_path)], cwd=str(project_root), check=False)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
