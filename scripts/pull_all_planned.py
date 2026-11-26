#!/usr/bin/env python3
"""Download all year-by-symbol slices in the phase plan."""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import date
from pathlib import Path

SYMBOLS = ("NQ", "ES", "GC", "HG", "YM")
PLAN_START = date(2015, 11, 26)
PLAN_END = date(2025, 11, 26)


def year_windows() -> list[tuple[int, date, date]]:
    windows: list[tuple[int, date, date]] = []
    for year in range(PLAN_START.year, PLAN_END.year + 1):
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        if year == PLAN_START.year:
            start = PLAN_START
        if year == PLAN_END.year:
            end = PLAN_END
        if start > end:
            continue
        windows.append((year, start, end))
    return windows


def main() -> int:
    script = Path(__file__).resolve().parent / "pull_slice.py"
    failures = 0
    for symbol in SYMBOLS:
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