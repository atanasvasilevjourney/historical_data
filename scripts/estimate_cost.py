#!/usr/bin/env python3
"""Estimate Databento credit for one or more slice definitions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import DATASET
from _common import SCHEMA
from _common import STYPE_IN
from _common import SYMBOL_MAP
from _common import historical_client
from _common import load_manifest
from _common import save_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate Databento cost for OHLCV slices")
    parser.add_argument("--symbol", action="append", help="Koko symbol (NQ, ES, …)")
    parser.add_argument("--start", help="ISO start date")
    parser.add_argument("--end", help="ISO end date (inclusive calendar day)")
    parser.add_argument("--write-manifest", action="store_true", help="Store estimates on manifest")
    parser.add_argument(
        "--full-decade",
        action="store_true",
        help="Estimate 2015-11-26..today for all five symbols",
    )
    args = parser.parse_args()

    client = historical_client()
    manifest = load_manifest()

    if args.full_decade:
        symbols = list(SYMBOL_MAP)
        start = "2015-11-26"
        end = args.end or "2025-11-26"
    else:
        if not args.symbol or not args.start or not args.end:
            parser.error("--symbol, --start, and --end required unless --full-decade")
        symbols = args.symbol
        start = args.start
        end = args.end

    results: list[dict] = []
    total = 0.0
    for sym in symbols:
        db_sym = SYMBOL_MAP.get(sym.upper(), sym)
        cost = client.metadata.get_cost(
            dataset=DATASET,
            symbols=db_sym,
            schema=SCHEMA,
            start=start,
            end=end,
            stype_in=STYPE_IN,
        )
        total += cost
        row = {
            "symbol": sym.upper(),
            "databento_symbol": db_sym,
            "start": start,
            "end": end,
            "cost_usd": round(float(cost), 4),
        }
        results.append(row)

    payload = {
        "dataset": DATASET,
        "schema": SCHEMA,
        "stype_in": STYPE_IN,
        "symbols": results,
        "total_cost_usd": round(total, 4),
    }
    print(json.dumps(payload, indent=2))

    if args.write_manifest:
        manifest.setdefault("estimates", {})["full_decade_10y_x5"] = payload
        manifest["symbology"] = SYMBOL_MAP
        save_manifest(manifest)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())