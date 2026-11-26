"""Shared helpers for Databento slice pull and manifest updates."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import databento as db
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "manifest.yaml"
SLICES_DIR = REPO_ROOT / "slices"

DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
STYPE_IN = "continuous"

# Koko short symbol -> Databento volume-rolled continuous (parent root on GLBX)
SYMBOL_MAP: dict[str, str] = {
    "NQ": "NQ.v.0",
    "ES": "ES.v.0",
    "GC": "GC.v.0",
    "HG": "HG.v.0",
    "YM": "YM.v.0",
}

OUTPUT_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def resolve_api_key() -> str:
    value = os.environ.get("DATABENTO_API_KEY", "").strip()
    if not value:
        raise RuntimeError("DATABENTO_API_KEY is not set")
    return value


def historical_client() -> db.Historical:
    return db.Historical(key=resolve_api_key())


def load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        return {
            "version": 1,
            "dataset": DATASET,
            "schema": SCHEMA,
            "stype_in": STYPE_IN,
            "symbology": SYMBOL_MAP,
            "credit_budget_usd": 120.0,
            "estimates": {},
            "slices": [],
            "queue": [],
        }
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def save_manifest(data: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = MANIFEST_PATH.with_suffix(".lock")
    with lock_path.open("w", encoding="utf-8") as lock:
        import fcntl

        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if MANIFEST_PATH.is_file():
            on_disk = yaml.safe_load(MANIFEST_PATH.open(encoding="utf-8")) or {}
            merged = on_disk
            disk_slices = {s.get("id"): s for s in on_disk.get("slices", []) if s.get("id")}
            for row in data.get("slices", []):
                if row.get("id"):
                    disk_slices[row["id"]] = row
            merged["slices"] = sorted(disk_slices.values(), key=lambda r: r.get("id", ""))
            for key, value in data.items():
                if key != "slices":
                    merged[key] = value
            data = merged
        with MANIFEST_PATH.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, default_flow_style=False, sort_keys=False)
        fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    work = df.reset_index()
    if "ts_event" in work.columns:
        work = work.rename(columns={"ts_event": "timestamp"})
    elif work.index.name == "ts_event":
        work = work.rename_axis("timestamp").reset_index()
    missing = [c for c in OUTPUT_COLUMNS if c not in work.columns]
    if missing:
        raise ValueError(f"missing columns after normalize: {missing}")
    out = work.loc[:, list(OUTPUT_COLUMNS)].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    for col in ("open", "high", "low", "close"):
        out[col] = out[col].astype(float)
    out["volume"] = pd.to_numeric(out["volume"], errors="raise").astype("int64")
    out = out.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")
    return out.reset_index(drop=True)


@dataclass(frozen=True)
class SliceSpec:
    slice_id: str
    symbol: str
    databento_symbol: str
    start: str
    end: str

    def out_path(self) -> Path:
        return SLICES_DIR / self.symbol / f"{self.slice_id}.parquet"


def upsert_slice(manifest: dict, entry: dict) -> None:
    slices = manifest.setdefault("slices", [])
    for index, row in enumerate(slices):
        if row.get("id") == entry["id"]:
            slices[index] = entry
            return
    slices.append(entry)


def iso_end_exclusive(end: date) -> str:
    """Databento end is exclusive; use next calendar day for date-only ends."""
    return (end + pd.Timedelta(days=1)).date().isoformat()


def today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()