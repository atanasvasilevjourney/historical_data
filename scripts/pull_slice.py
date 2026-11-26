#!/usr/bin/env python3
"""Download one OHLCV-1m slice from Databento and update manifest.yaml."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import DATASET
from _common import SCHEMA
from _common import STYPE_IN
from _common import SYMBOL_MAP
from _common import SliceSpec
from _common import historical_client
from _common import load_manifest
from _common import normalize_ohlcv
from _common import save_manifest
from _common import sha256_file
from _common import upsert_slice


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull one Databento OHLCV slice to Parquet")
    parser.add_argument("--symbol", required=True, help="Koko symbol: NQ, ES, GC, HG, YM")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument("--slice-id", required=True, help="Manifest slice id, e.g. nq_1m_glbx_2024")
    parser.add_argument("--dry-run", action="store_true", help="Cost estimate only, no download")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    if symbol not in SYMBOL_MAP:
        raise SystemExit(f"unknown symbol {symbol}; choose from {', '.join(SYMBOL_MAP)}")
    db_sym = SYMBOL_MAP[symbol]
    spec = SliceSpec(
        slice_id=args.slice_id,
        symbol=symbol,
        databento_symbol=db_sym,
        start=args.start,
        end=args.end,
    )

    client = historical_client()
    from datetime import date, timedelta

    end_day = date.fromisoformat(args.end)
    end_excl = (end_day + timedelta(days=1)).isoformat()

    cost = client.metadata.get_cost(
        dataset=DATASET,
        symbols=db_sym,
        schema=SCHEMA,
        start=args.start,
        end=end_excl,
        stype_in=STYPE_IN,
    )
    summary = {
        "slice_id": spec.slice_id,
        "symbol": symbol,
        "start": args.start,
        "end": args.end,
        "cost_usd": round(float(cost), 4),
    }
    if args.dry_run:
        print(json.dumps({**summary, "dry_run": True}, indent=2))
        return 0

    last_err: Exception | None = None
    store = None
    for attempt in range(1, 6):
        try:
            store = client.timeseries.get_range(
                dataset=DATASET,
                symbols=db_sym,
                schema=SCHEMA,
                start=args.start,
                end=end_excl,
                stype_in=STYPE_IN,
            )
            break
        except Exception as exc:  # noqa: BLE001 — retry transient gateway errors
            last_err = exc
            if attempt >= 5:
                raise
            time.sleep(min(60, 4 * (2 ** (attempt - 1))))
    if store is None:
        raise SystemExit(last_err)
    frame = normalize_ohlcv(store.to_df())
    if frame.empty:
        raise SystemExit(f"empty frame for {spec.slice_id}")

    out_path = spec.out_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, out_path, compression="zstd")

    digest = sha256_file(out_path)
    manifest = load_manifest()
    rel = out_path.relative_to(out_path.parents[2]).as_posix()
    entry = {
        "id": spec.slice_id,
        "symbol": symbol,
        "databento_symbol": db_sym,
        "dataset": DATASET,
        "schema": SCHEMA,
        "stype_in": STYPE_IN,
        "start": args.start,
        "end": args.end,
        "path": rel,
        "bars": int(len(frame)),
        "bytes": int(out_path.stat().st_size),
        "sha256": digest,
        "cost_usd": round(float(cost), 4),
        "databento_job": None,
    }
    upsert_slice(manifest, entry)
    manifest["symbology"] = SYMBOL_MAP
    save_manifest(manifest)

    print(
        json.dumps(
            {
                **summary,
                "bars": entry["bars"],
                "bytes": entry["bytes"],
                "sha256": digest,
                "path": str(out_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())