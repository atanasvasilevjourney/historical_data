#!/usr/bin/env python3
"""Download all planned year slices for one symbol."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import SYMBOL_MAP
from pull_all_planned import year_windows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=tuple(SYMBOL_MAP))
    args = parser.parse_args()
    symbol = args.symbol.upper()
    script = Path(__file__).resolve().parent / "pull_slice.py"
    failures = 0
    for year, start, end in year_windows():
        slice_id = f"{symbol.lower()}_1m_glbx_{year}"
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
        print(f"=== {symbol} {year} ===", flush=True)
        rc = -1
        for attempt in range(1, 4):
            rc = subprocess.call(cmd)
            if rc == 0:
                break
            time.sleep(10 * attempt)
        if rc != 0:
            failures += 1
            print(f"FAILED {slice_id}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())