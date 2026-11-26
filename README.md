# Historical CME Globex 1-minute OHLCV (Databento)

Canonical **1-minute OHLCV** tapes for Koko backtests. Data is fetched from [Databento](https://databento.com) dataset **`GLBX.MDP3`** schema **`ohlcv-1m`**. Parquet files live under `slices/` (Git LFS).

## Symbology (GLBX continuous)

| Koko | Databento (`stype_in=continuous`) | Parent |
|------|-------------------------------------|--------|
| NQ | `NQ.v.0` | NQ |
| ES | `ES.v.0` | ES |
| GC | `GC.v.0` | GC |
| HG | `HG.v.0` | HG |
| YM | `YM.v.0` | YM |

**Roll:** volume-weighted continuous (`.v.0`) — suitable for research; not a single expiry without roll rules. Session is **Globex calendar** (23h CME); apply RTH filters in Koko ingest or strategy.

## Column layout

Every slice parquet file:

`timestamp, open, high, low, close, volume`

- `timestamp`: UTC `datetime64[ns, UTC]`
- Prices: float64 (already decoded from Databento fixed-point)
- `volume`: int64 contract count per minute

## Credit and phase plan

- Budget assumption: **~$125** Databento credit; downloads stop if an estimate exceeds **~$120** for a batch.
- **Phase:** one parquet per **calendar year** per symbol (`slices/{SYMBOL}/{symbol}_1m_glbx_{YEAR}.parquet`).
- Full scope: **2015-11-26 → 2025-11-26** (10 years) × **5 symbols**.
- Run **`scripts/estimate_cost.py --full-decade --write-manifest`** before large pulls.

Actual cost and per-slice estimates are recorded in `manifest.yaml` (`estimates`, `slices`, `queue`).

## Secrets

`DATABENTO_API_KEY` — environment only. Never commit, log, or write to `manifest.yaml`.

## Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABENTO_API_KEY='…'   # from Cursor secrets

# Cost estimate (10y × 5)
python scripts/estimate_cost.py --full-decade --write-manifest

# One slice
python scripts/pull_slice.py --symbol NQ --start 2024-01-01 --end 2024-12-31 \
  --slice-id nq_1m_glbx_2024

# Full phased plan (all years × symbols)
python scripts/pull_all_planned.py
```

## Git LFS

```bash
git lfs install
git add slices/
```

## Koko engine

Point the engine at this clone with `KOKO_DATA_ROOT=/path/to/historical_data` or run `koko data fetch databento --manifest …` (see `mechkarevo_algo` PR). Use manifest slice `id` for backtests.