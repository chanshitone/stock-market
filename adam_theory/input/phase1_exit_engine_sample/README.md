# phase1_exit_engine sample inputs

This folder supports two ways to test:

1) Use the included static `daily_bars.csv` (fully deterministic).
2) Run the engine with **only** `positions.csv` and let it fetch `daily_bars` from Tushare automatically.

Files:
- `positions.csv`: current holdings (entry + stops). Note: the included `AAA/BBB/...` symbols are only for the static demo; for API mode, set `symbol` to your real `ts_code` (e.g. `000001.SZ`).
- `daily_bars.csv`: per-symbol OHLCV + `ma5` (price MA5). Used directly by `phase1_exit_engine.py`.
- `build_daily_bars_from_tushare.py`: generates `daily_bars.csv` via `ts.pro_bar(..., adj="qfq", ma=[5], retry_count=5)`.

## Option A: Run using the included static bars

Run from repo root:

```powershell
python .\adam_theory\phase1_exit_engine.py `
  --positions .\adam_theory\input\phase1_exit_engine_sample\positions.csv `
  --bars .\adam_theory\input\phase1_exit_engine_sample\daily_bars.csv `
  --asof 2026-01-10 `
  --out .\adam_theory\output\phase1_exit_engine_decisions_sample.csv
```

What each sample symbol is designed to trigger (as-of 2026-01-10):
- `AAA`: STOP_HIT (today low <= current_stop)
- `BBB`: STRUCT_BREAK (2 consecutive closes below MA5)
- `CCC`: STRUCT_STALL (volume spike vs MA5(volume) + close not new high close)
- `DDD`: HOLD with stop raise (+2R => stop >= entry + 1R)
- `EEE`: TIME_STOP (>=10 bars since entry, maxR < 0.5, not in protection)

## Option B: Run engine with API bars (simplest)

Set your token (recommended):

```powershell
$env:TUSHARE_TOKEN="<your_token_here>"
```

Run the engine; it will fetch bars via Tushare automatically when `--bars` is omitted:

```powershell
python .\adam_theory\phase1_exit_engine.py `
  --positions .\adam_theory\input\phase1_exit_engine_sample\positions.csv `
  --out .\adam_theory\output\phase1_exit_engine_decisions_api.csv
```

Optional fetch controls:
- `--start YYYY-MM-DD` / `--end YYYY-MM-DD`
- `--throttle 49`
- `--token <token>` (instead of env var)
