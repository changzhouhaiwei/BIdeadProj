#!/usr/bin/env python3
"""Backward-compatible wrapper → chroma_key.py (prefer that entrypoint)."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Map old --key defaults: if user passes nothing, keep green for compat
if __name__ == "__main__":
    script = Path(__file__).with_name("chroma_key.py")
    # If caller didn't specify --key, default to green (old behavior)
    argv = sys.argv[1:]
    if "--key" not in argv:
        argv = ["--key", "green", *argv]
    sys.argv = [str(script), *argv]
    runpy.run_path(str(script), run_name="__main__")
