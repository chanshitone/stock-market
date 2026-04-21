"""gap_up_exit_engine.py

Exit engine for gap-up momentum positions.

Exit conditions (checked in priority order each trading day):
  1. Gap-down stop  : day open <= stop_price                          → exit at open
  2. Fixed stop     : intrabar low <= stop_price (5 % below entry)    → exit at stop_price
  3. MA exit        : N consecutive closes below MA(K)                → exit at next open
  4. Volume spike   : daily vol >= R × vol_MA(M) and close not        → exit at next open
                      new high since entry
  5. Timeout        : hold_days >= D and max_R < T                    → exit at next open

Config keys and defaults
  risk.initial_stop_loss_pct               0.05
  exit.ma_window                           13
  exit.consecutive_close_below_ma_days     2
  exit.vol_spike_ratio                     1.5
  exit.vol_spike_ma_window                 5
  exit.timeout_hold_days                   10
  exit.timeout_target_r                    0.5
"""

import argparse
from dataclasses import dataclass
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd

from env_config import get_tushare_token


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_STOP_LOSS_PCT = 0.05
_DEFAULT_MA_WINDOW = 13
_DEFAULT_CONSECUTIVE_BELOW_MA = 2
_DEFAULT_VOL_SPIKE_RATIO = 1.5
_DEFAULT_VOL_SPIKE_MA_WINDOW = 5
_DEFAULT_TIMEOUT_HOLD_DAYS = 10
_DEFAULT_TIMEOUT_TARGET_R = 0.5
_SCRIPT_DIR = Path(__file__).resolve().parent


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ExitConfig:
    """Configurable exit parameters.  All values match spec defaults."""

    initial_stop_loss_pct: float = _DEFAULT_STOP_LOSS_PCT
    ma_window: int = _DEFAULT_MA_WINDOW
    consecutive_close_below_ma_days: int = _DEFAULT_CONSECUTIVE_BELOW_MA
    vol_spike_ratio: float = _DEFAULT_VOL_SPIKE_RATIO
    vol_spike_ma_window: int = _DEFAULT_VOL_SPIKE_MA_WINDOW
    timeout_hold_days: int = _DEFAULT_TIMEOUT_HOLD_DAYS
    timeout_target_r: float = _DEFAULT_TIMEOUT_TARGET_R


@dataclass
class Position:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    stop_price: float  # fixed (monotonically fixed; no trailing in this engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_yyyymmdd(d: "pd.Timestamp | date") -> str:
    if isinstance(d, pd.Timestamp):
        d = d.date()
    return d.strftime("%Y%m%d")


def _resolve_input_path(path_value: str) -> str:
    candidate = Path(path_value)
    if candidate.exists() or candidate.is_absolute():
        return str(candidate)

    script_relative = _SCRIPT_DIR / candidate
    if script_relative.exists():
        return str(script_relative)

    return str(candidate)


def _normalize_symbol(symbol_value: object) -> str:
    if pd.isna(symbol_value):
        return ""

    if isinstance(symbol_value, (int, float)) and not isinstance(symbol_value, bool):
        if float(symbol_value).is_integer():
            symbol = str(int(symbol_value)).zfill(6)
        else:
            symbol = str(symbol_value)
    else:
        symbol = str(symbol_value).strip().upper()

    if not symbol:
        return symbol

    if symbol.endswith(".SZ") or symbol.endswith(".SH"):
        return symbol

    if symbol.endswith(".0"):
        symbol = symbol[:-2]

    if symbol.isdigit():
        symbol = symbol.zfill(6)

    if symbol.startswith(("0", "3")):
        return f"{symbol}.SZ"
    if symbol.startswith("6"):
        return f"{symbol}.SH"

    return symbol


def _read_csv_with_symbol_columns(path_value: str) -> pd.DataFrame:
    df = pd.read_csv(path_value)
    for column in ("symbol", "ts_code"):
        if column in df.columns:
            df[column] = df[column].map(_normalize_symbol)
    return df


def _normalize_pro_bar(
    df: pd.DataFrame, symbol: str, ma_window: int = _DEFAULT_MA_WINDOW
) -> pd.DataFrame:
    """Normalise tushare pro_bar output to exit-engine schema."""
    ma_col = f"ma{ma_window}"
    empty = pd.DataFrame(
        columns=["symbol", "date", "open", "high", "low", "close", "volume", ma_col]
    )
    if df is None or df.empty:
        return empty

    out = df.copy()

    if "trade_date" in out.columns:
        out["date"] = pd.to_datetime(
            out["trade_date"].astype(str), format="%Y%m%d", errors="coerce"
        )
    elif "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
    else:
        raise ValueError("pro_bar result missing trade_date/date column")

    if "vol" in out.columns:
        out["volume"] = out["vol"]
    elif "volume" not in out.columns:
        raise ValueError("pro_bar result missing vol/volume column")

    if ma_col not in out.columns:
        raise ValueError(
            f"pro_bar result missing {ma_col} (did you pass ma=[{ma_window}]?)"
        )

    out["symbol"] = str(symbol)
    out = out[["symbol", "date", "open", "high", "low", "close", "volume", ma_col]]
    out = out.dropna(subset=["date"]).sort_values(["symbol", "date"])
    return out


# ---------------------------------------------------------------------------
# Tushare fetch
# ---------------------------------------------------------------------------
def fetch_daily_bars(
    symbols: list,
    start: pd.Timestamp,
    end: pd.Timestamp,
    ma_window: int = _DEFAULT_MA_WINDOW,
    token: str = None,
    throttle: int = 49,
) -> pd.DataFrame:
    """Fetch OHLCV + MA(ma_window) for *symbols* via Tushare pro_bar."""
    try:
        import tushare as ts
    except ImportError as e:
        raise SystemExit(
            "Missing dependency 'tushare'. Install it or provide --bars instead."
        ) from e

    try:
        token = get_tushare_token(token=token, required=True)
    except RuntimeError as e:
        raise SystemExit(str(e)) from e

    ts.set_token(token)

    start_date = _to_yyyymmdd(start)
    end_date = _to_yyyymmdd(end)
    ma_col = f"ma{ma_window}"

    all_rows: list = []
    call_count = 0

    for sym in symbols:
        call_count += 1
        if throttle > 0 and call_count >= throttle:
            print("Throttle: sleeping 60 s")
            call_count = 0
            time.sleep(60)

        try:
            df = ts.pro_bar(
                ts_code=sym,
                adj="qfq",
                start_date=start_date,
                end_date=end_date,
                ma=[ma_window],
                retry_count=5,
            )
        except Exception as exc:
            print(f"Error fetching {sym}: {exc}")
            continue

        try:
            norm = _normalize_pro_bar(df, symbol=sym, ma_window=ma_window)
        except Exception as exc:
            print(f"Error normalising {sym}: {exc}")
            continue

        if norm.empty:
            print(f"Warning: no data for {sym}")
            continue

        all_rows.append(norm)

    if not all_rows:
        return pd.DataFrame(
            columns=["symbol", "date", "open", "high", "low", "close", "volume", ma_col]
        )

    return pd.concat(all_rows, ignore_index=True)


# ---------------------------------------------------------------------------
# Position parsing
# ---------------------------------------------------------------------------
def parse_positions(df: pd.DataFrame, cfg: ExitConfig) -> list:
    """Build Position list from CSV dataframe.

    Accepts either 'symbol' or 'ts_code' as the symbol column.
    If 'stop_price' column is absent or NaN, defaults to
    entry_price * (1 - cfg.initial_stop_loss_pct).
    """
    df = df.copy()

    # Normalise symbol column name
    if "symbol" not in df.columns and "ts_code" in df.columns:
        df = df.rename(columns={"ts_code": "symbol"})

    df["entry_date"] = pd.to_datetime(df["entry_date"])
    positions: list = []

    for _, r in df.iterrows():
        entry_price = float(r["entry_price"])
        if "stop_price" in df.columns and pd.notna(r.get("stop_price")):
            stop_price = float(r["stop_price"])
        else:
            stop_price = round(entry_price * (1.0 - cfg.initial_stop_loss_pct), 4)

        positions.append(
            Position(
                symbol=_normalize_symbol(r["symbol"]),
                entry_date=r["entry_date"],
                entry_price=entry_price,
                stop_price=stop_price,
            )
        )

    return positions


# ---------------------------------------------------------------------------
# Core decision logic
# ---------------------------------------------------------------------------
def gap_up_decide_for_symbol(
    bars: pd.DataFrame,
    pos: Position,
    asof: pd.Timestamp,
    cfg: ExitConfig = None,
) -> dict:
    """Evaluate exit conditions for one position as of *asof*.

    Parameters
    ----------
    bars : rows for this symbol, columns include date / open / high / low /
           close / volume / ma{cfg.ma_window}
    pos  : Position
    asof : evaluation date; only bars up to this date are considered
    cfg  : ExitConfig (defaults used when None)

    Returns
    -------
    dict with keys:
      action            SELL | HOLD
      reason            str
      exit_price        float | None  (None means "execute at next open")
      r_close           float | None
      hold_days         int
      max_r_since_entry float | None
    """
    if cfg is None:
        cfg = ExitConfig()

    ma_col = f"ma{cfg.ma_window}"
    vol_ma_col = f"vol_ma{cfg.vol_spike_ma_window}"

    # ── narrow to asof ──────────────────────────────────────────────────────
    b = bars[bars["date"] <= asof].copy().sort_values("date")
    if b.empty:
        return {
            "action": "HOLD",
            "reason": "NO_DATA",
            "exit_price": None,
            "r_close": None,
            "hold_days": 0,
            "max_r_since_entry": None,
        }

    # volume MA computed over full pre-asof history for a stable baseline
    b[vol_ma_col] = b["volume"].rolling(cfg.vol_spike_ma_window).mean()

    b_entry = b[b["date"] >= pos.entry_date].copy()
    if b_entry.empty:
        return {
            "action": "HOLD",
            "reason": "NO_DATA_AFTER_ENTRY",
            "exit_price": None,
            "r_close": None,
            "hold_days": 0,
            "max_r_since_entry": None,
        }

    today = b_entry.iloc[-1]
    hold_days = len(b_entry)
    is_entry_day = today["date"].normalize() == pos.entry_date.normalize()

    entry = pos.entry_price
    stop = pos.stop_price
    risk = entry - stop

    # ── shared metrics ───────────────────────────────────────────────────────
    def _safe(val: float) -> "float | None":
        return None if (isinstance(val, float) and pd.isna(val)) else round(val, 4)

    r_close = ((float(today["close"]) - entry) / risk) if risk > 0 else float("nan")
    max_close = float(b_entry["close"].max())
    max_r = ((max_close - entry) / risk) if risk > 0 else float("nan")
    max_close_before_today = (
        float(b_entry.iloc[:-1]["close"].max()) if len(b_entry) >= 2 else float("-inf")
    )

    common = {
        "r_close": _safe(r_close),
        "hold_days": hold_days,
        "max_r_since_entry": _safe(max_r),
    }

    # ── Rule 1: Gap-down stop ────────────────────────────────────────────────
    # day open <= stop_price → exit at open
    today_open = float(today["open"])
    if (not is_entry_day) and today_open <= stop:
        return {
            "action": "SELL",
            "reason": f"GAP_DOWN_STOP: open={today_open:.3f} <= stop={stop:.3f}",
            "exit_price": today_open,
            **common,
        }

    # ── Rule 2: Fixed stop (intrabar) ────────────────────────────────────────
    # intrabar low <= stop_price → exit at stop_price
    if (not is_entry_day) and float(today["low"]) <= stop:
        return {
            "action": "SELL",
            "reason": f"FIXED_STOP: low={float(today['low']):.3f} <= stop={stop:.3f}",
            "exit_price": stop,
            **common,
        }

    # ── Rule 3: MA exit ──────────────────────────────────────────────────────
    # N consecutive closes below MA(K) → exit at next open
    n = cfg.consecutive_close_below_ma_days
    if ma_col in b_entry.columns and len(b_entry) >= n:
        recent = b_entry.tail(n)
        if all(
            float(row["close"]) < float(row[ma_col]) for _, row in recent.iterrows()
        ):
            return {
                "action": "SELL",
                "reason": (
                    f"MA_EXIT: {n} consecutive closes below MA{cfg.ma_window}"
                ),
                "exit_price": None,
                **common,
            }

    # ── Rule 4: Volume spike ─────────────────────────────────────────────────
    # vol >= R × vol_MA(M) and close is not a new high close since entry
    today_in_b = b[b["date"] == today["date"]]
    if not today_in_b.empty:
        raw_vol_ma = today_in_b.iloc[-1][vol_ma_col]
        today_vol_ma = float(raw_vol_ma) if pd.notna(raw_vol_ma) else None
        if today_vol_ma and today_vol_ma > 0:
            vol_spike = float(today["volume"]) >= cfg.vol_spike_ratio * today_vol_ma
            not_new_high = float(today["close"]) <= max_close_before_today
            if vol_spike and not_new_high:
                return {
                    "action": "SELL",
                    "reason": (
                        f"VOL_SPIKE: vol>={cfg.vol_spike_ratio}"
                        f"×vol_MA{cfg.vol_spike_ma_window}"
                        " and close not new high since entry"
                    ),
                    "exit_price": None,
                    **common,
                }

    # ── Rule 5: Timeout ──────────────────────────────────────────────────────
    # hold_days >= D and max R achieved < T → exit at next open
    if hold_days >= cfg.timeout_hold_days and risk > 0:
        if not pd.isna(max_r) and max_r < cfg.timeout_target_r:
            return {
                "action": "SELL",
                "reason": (
                    f"TIMEOUT: hold_days={hold_days}>={cfg.timeout_hold_days}"
                    f" and max_r={max_r:.2f}<{cfg.timeout_target_r}"
                ),
                "exit_price": None,
                **common,
            }

    return {
        "action": "HOLD",
        "reason": "HOLD: no exit condition triggered",
        "exit_price": None,
        **common,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="Gap-up momentum position exit engine."
    )
    ap.add_argument(
        "--positions",
        default=os.path.join(".", "input", "positions.csv"),
        help=(
            "Positions CSV.  Required columns: symbol (or ts_code), entry_date, "
            "entry_price.  Optional: stop_price (default: entry_price × (1-stop-pct))."
        ),
    )
    ap.add_argument(
        "--bars",
        default=None,
        help=(
            "Pre-fetched daily_bars CSV with columns: symbol, date, open, high, low, "
            "close, volume, ma13 (or whichever --ma-window you choose).  "
            "If omitted, bars are fetched via Tushare pro_bar."
        ),
    )
    ap.add_argument("--asof", default=None, help="YYYY-MM-DD (default: latest in bars)")
    ap.add_argument("--out", default=None, help="Output decisions CSV path")
    ap.add_argument(
        "--token", default=None, help="Tushare token (or set env TUSHARE_TOKEN)"
    )
    ap.add_argument("--start", default=None, help="YYYY-MM-DD start for API fetch")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD end for API fetch (default: today)")
    ap.add_argument(
        "--throttle",
        type=int,
        default=49,
        help="Max API calls per minute before sleeping (default: 49)",
    )

    # ── Exit config overrides ────────────────────────────────────────────────
    ap.add_argument(
        "--stop-pct",
        type=float,
        default=_DEFAULT_STOP_LOSS_PCT,
        help=f"Fixed stop as fraction below entry price (default: {_DEFAULT_STOP_LOSS_PCT})",
    )
    ap.add_argument(
        "--ma-window",
        type=int,
        default=_DEFAULT_MA_WINDOW,
        help=f"MA window for exit rule 3 (default: {_DEFAULT_MA_WINDOW})",
    )
    ap.add_argument(
        "--ma-days",
        type=int,
        default=_DEFAULT_CONSECUTIVE_BELOW_MA,
        help=f"Consecutive closes below MA to trigger exit (default: {_DEFAULT_CONSECUTIVE_BELOW_MA})",
    )
    ap.add_argument(
        "--vol-ratio",
        type=float,
        default=_DEFAULT_VOL_SPIKE_RATIO,
        help=f"Volume spike multiplier vs vol MA (default: {_DEFAULT_VOL_SPIKE_RATIO})",
    )
    ap.add_argument(
        "--vol-ma",
        type=int,
        default=_DEFAULT_VOL_SPIKE_MA_WINDOW,
        help=f"Volume MA window for spike detection (default: {_DEFAULT_VOL_SPIKE_MA_WINDOW})",
    )
    ap.add_argument(
        "--timeout-days",
        type=int,
        default=_DEFAULT_TIMEOUT_HOLD_DAYS,
        help=f"Max holding days before timeout check (default: {_DEFAULT_TIMEOUT_HOLD_DAYS})",
    )
    ap.add_argument(
        "--timeout-r",
        type=float,
        default=_DEFAULT_TIMEOUT_TARGET_R,
        help=f"Minimum R progress required to avoid timeout exit (default: {_DEFAULT_TIMEOUT_TARGET_R})",
    )

    args = ap.parse_args()

    cfg = ExitConfig(
        initial_stop_loss_pct=args.stop_pct,
        ma_window=args.ma_window,
        consecutive_close_below_ma_days=args.ma_days,
        vol_spike_ratio=args.vol_ratio,
        vol_spike_ma_window=args.vol_ma,
        timeout_hold_days=args.timeout_days,
        timeout_target_r=args.timeout_r,
    )

    if args.out is None:
        ts_str = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M%S")
        args.out = os.path.join(
            ".", "adam_theory", "output", f"gap_up_exit_{ts_str}.xlsx"
        )

    pos_df = _read_csv_with_symbol_columns(_resolve_input_path(args.positions))

    # ── Load or fetch bars ───────────────────────────────────────────────────
    if args.bars:
        bars_df = _read_csv_with_symbol_columns(_resolve_input_path(args.bars))
        bars_df["date"] = pd.to_datetime(bars_df["date"])
        bars_df["symbol"] = bars_df["symbol"].map(_normalize_symbol)
        ma_col = f"ma{cfg.ma_window}"
        if ma_col not in bars_df.columns:
            raise SystemExit(
                f"bars CSV is missing column '{ma_col}'.  "
                f"Re-export with ma=[{cfg.ma_window}] or adjust --ma-window."
            )
    else:
        tmp = pos_df.copy()
        if "entry_date" not in tmp.columns:
            raise SystemExit("positions CSV must contain an 'entry_date' column")
        tmp["entry_date"] = pd.to_datetime(tmp["entry_date"], errors="coerce")
        earliest_entry = tmp["entry_date"].dropna().min()
        if pd.isna(earliest_entry):
            raise SystemExit("positions CSV has no valid entry_date values")

        # 30 calendar days of pre-entry history so MA has enough warm-up
        default_start = (earliest_entry - pd.Timedelta(days=30)).normalize()
        start_dt = pd.to_datetime(args.start) if args.start else default_start
        end_dt = (
            pd.to_datetime(args.end) if args.end else pd.Timestamp(date.today())
        )

        sym_col = "symbol" if "symbol" in tmp.columns else "ts_code"
        symbols = [
            _normalize_symbol(s)
            for s in tmp[sym_col].dropna().unique().tolist()
            if _normalize_symbol(s)
        ]
        if not symbols:
            raise SystemExit("positions CSV must contain at least one symbol")

        print(
            f"Fetching bars via Tushare: {len(symbols)} symbol(s), "
            f"{start_dt.date()} → {end_dt.date()}"
        )
        bars_df = fetch_daily_bars(
            symbols=symbols,
            start=start_dt,
            end=end_dt,
            ma_window=cfg.ma_window,
            token=args.token,
            throttle=args.throttle,
        )
        if bars_df.empty:
            raise SystemExit("No bars fetched.  Check token / symbols / date range.")

    asof = pd.to_datetime(args.asof) if args.asof else bars_df["date"].max()

    positions = parse_positions(pos_df, cfg)

    # ── Evaluate each position ───────────────────────────────────────────────
    decisions = []
    for p in positions:
        sym_bars = bars_df[bars_df["symbol"] == p.symbol].copy()
        if sym_bars.empty:
            decisions.append(
                {
                    "date": asof.strftime("%Y-%m-%d"),
                    "symbol": p.symbol,
                    "entry_price": p.entry_price,
                    "stop_price": p.stop_price,
                    "action": "HOLD",
                    "reason": "NO_SYMBOL_DATA",
                    "exit_price": None,
                    "r_close": None,
                    "hold_days": None,
                    "max_r_since_entry": None,
                }
            )
            continue

        d = gap_up_decide_for_symbol(sym_bars, p, asof=asof, cfg=cfg)
        decisions.append(
            {
                "date": asof.strftime("%Y-%m-%d"),
                "symbol": p.symbol,
                "entry_price": p.entry_price,
                "stop_price": p.stop_price,
                "action": d["action"],
                "reason": d["reason"],
                "exit_price": d.get("exit_price"),
                "r_close": d.get("r_close"),
                "hold_days": d.get("hold_days"),
                "max_r_since_entry": d.get("max_r_since_entry"),
            }
        )

    out_df = pd.DataFrame(decisions).sort_values(["action", "symbol"])
    out_df.to_excel(args.out, index=False)
    print(f"Saved: {args.out}")
    print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
