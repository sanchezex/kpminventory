"""Resolve packaged resources for source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Resolve a bundled resource from source or a PyInstaller one-file app."""
    bundle_root = Path(
        getattr(sys, "_MEIPASS", None) or Path(__file__).resolve().parent
    )
    return bundle_root / relative_path
