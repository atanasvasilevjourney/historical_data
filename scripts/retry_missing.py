#!/usr/bin/env python3
"""Re-pull year slices missing from manifest."""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import SYMBOL_MAP
from _common import load_manifest
from pull_all_planned import PLAN_END
from pull_all_planned import PLAN_START
from pull_all_planned import year_windows


def main() -> int:
    manifest = load_manifest()
    have = {row["id"] for row in manifest.get("slices", [])}
    script = Path(__file__).resolve().parent / "pull_slice.py"
    failures = 0
    for symbol in SYMBOL_MAP:
        for year, start, end in year_windows():
            slice_id = f"{symbol.lower()}_1m_glbx_{year}"
            if slice_id in have:
                continue
            cmd = [
                sys.executable,
                str(script),
                "--symbol",
                symbol,
                "--start",
                start.isoformat(),
                "--end",
                end.isoformat(),
                "--slice-id",
                slice_id,
            ]
            print(f"retry {slice_id}", flush=True)
            if subprocess.call(cmd) != 0:
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())