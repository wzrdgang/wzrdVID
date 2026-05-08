"""Compatibility wrapper for the //wzrdVID branding generator.

The public branding source of truth lives in scripts/generate_branding.py and
assets/branding/. This wrapper keeps older docs or habits working without
regenerating the retired pre-release logo style.
"""

from __future__ import annotations

from generate_branding import main


if __name__ == "__main__":
    main()
