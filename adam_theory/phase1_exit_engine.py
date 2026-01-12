import argparse
from dataclasses import dataclass
import os
import time
from datetime import date, timedelta
import pandas as pd


DEFAULT_TUSHARE_TOKEN = "8b8ed979c3736e2485771cea39630f5e083921c78ae181f5f1ec34f5"


@dataclass
class Position:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float   # weighted cost
    initial_stop: float  # S0
    current_stop: float  # current stop (monotonic up)


def _to_yyyymmdd(d: pd.Timestamp | date) -> str:
    if isinstance(d, pd.Timestamp):
        d = d.date()
    return d.strftime("%Y%m%d")


def _normalize_pro_bar(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize tushare pro_bar output to exit-engine schema."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "ma5"])

    out = df.copy()

    # pro_bar returns trade_date as YYYYMMDD string and is often sorted desc by date
    if "trade_date" in out.columns:
        out["date"] = pd.to_datetime(out["trade_date"].astype(str), format="%Y%m%d", errors="coerce")
    elif "date" in out.columns:
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
    else:
        raise ValueError("pro_bar result missing trade_date/date column")

    # volume column name in tushare is 'vol'
    if "vol" in out.columns:
        out["volume"] = out["vol"]
    elif "volume" not in out.columns:
        raise ValueError("pro_bar result missing vol/volume column")

    # ma=[5] creates ma5
    if "ma5" not in out.columns:
        raise ValueError("pro_bar result missing ma5 (did you pass ma=[5]?)")

    out["symbol"] = str(symbol)
    out = out[["symbol", "date", "open", "high", "low", "close", "volume", "ma5"]]
    out = out.dropna(subset=["date"]).sort_values(["symbol", "date"])
    return out


def fetch_daily_bars_from_tushare(
    symbols: list[str],
    start: pd.Timestamp,
    end: pd.Timestamp,
    token: str | None = None,
    throttle: int = 49,
) -> pd.DataFrame:
    """Fetch OHLCV + ma5 for symbols using Tushare pro_bar."""
    try:
        import tushare as ts
    except ImportError as e:
        raise SystemExit(
            "Missing dependency 'tushare'. Install it or provide --bars instead of API fetching."
        ) from e

    token = token or os.getenv("TUSHARE_TOKEN") or DEFAULT_TUSHARE_TOKEN

    ts.set_token(token)

    start_date = _to_yyyymmdd(start)
    end_date = _to_yyyymmdd(end)

    all_rows: list[pd.DataFrame] = []
    count_allowed_per_minute = 0

    for sym in symbols:
        count_allowed_per_minute += 1
        if throttle > 0 and count_allowed_per_minute >= throttle:
            print("Sleep for 60 seconds")
            count_allowed_per_minute = 0
            time.sleep(60)

        try:
            df = ts.pro_bar(
                ts_code=sym,
                adj="qfq",
                start_date=start_date,
                end_date=end_date,
                ma=[5],
                retry_count=5,
            )
        except Exception as e:
            print(f"Error fetching {sym}: {e}")
            continue

        try:
            norm = _normalize_pro_bar(df, symbol=sym)
        except Exception as e:
            print(f"Error normalizing {sym}: {e}")
            continue

        if norm.empty:
            print(f"Warning: no data for {sym}")
            continue
        all_rows.append(norm)

    if not all_rows:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "ma5"])

    return pd.concat(all_rows, ignore_index=True)


def parse_positions(df: pd.DataFrame) -> list[Position]:
    df = df.copy()
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    positions: list[Position] = []
    for _, r in df.iterrows():
        positions.append(
            Position(
                symbol=str(r["symbol"]),
                entry_date=r["entry_date"],
                entry_price=float(r["entry_price"]),
                initial_stop=float(r["initial_stop"]),
                current_stop=float(r["current_stop"]),
            )
        )
    return positions


def calc_r(price: float, entry: float, s0: float) -> float:
    risk = entry - s0
    if risk <= 0:
        return float("nan")
    return (price - entry) / risk


def phase1_decide_for_symbol(
    bars: pd.DataFrame,
    pos: Position,
    asof: pd.Timestamp,
    time_stop_days: int = 10,
    time_stop_progress_r: float = 0.5,
    vol_spike_mult: float = 1.5,
) -> dict:
    """
    bars: rows for (symbol), contains date, open, high, low, close, volume, ma5
    asof: evaluation date (use the latest date in bars by default)
    Returns: action dict with fields:
      - action: HOLD / SELL
      - reason: string
      - new_stop: float (suggested stop after today's close)
      - r_close: float
      - max_close_since_entry: float
      - hold_days: int (trading days)
    """

    # Filter timeframe
    b = bars[bars["date"] <= asof].copy()
    b = b.sort_values("date")
    if b.empty:
        return {"action": "HOLD", "reason": "NO_DATA", "new_stop": pos.current_stop}

    # Entry slice (from entry_date to asof)
    b_entry = b[b["date"] >= pos.entry_date].copy()
    if b_entry.empty:
        return {"action": "HOLD", "reason": "NO_DATA_AFTER_ENTRY", "new_stop": pos.current_stop}

    today = b_entry.iloc[-1]
    prev = b_entry.iloc[-2] if len(b_entry) >= 2 else None

    # Rolling MA5(volume) for vol spike detection (use full b, then align)
    b["vol_ma5"] = b["volume"].rolling(5).mean()
    b_entry = b[b["date"] >= pos.entry_date].copy()
    b_entry = b_entry.merge(b[["date", "vol_ma5"]], on="date", how="left")

    # Basic metrics
    entry = pos.entry_price
    s0 = pos.initial_stop
    risk = entry - s0
    if risk <= 0:
        return {"action": "HOLD", "reason": "INVALID_RISK(entry<=stop)", "new_stop": pos.current_stop}

    r_close = calc_r(float(today["close"]), entry, s0)
    hold_days = len(b_entry)

    # Max close since entry (excluding today) for "未创新高"
    if len(b_entry) >= 2:
        max_close_before_today = float(b_entry.iloc[:-1]["close"].max())
    else:
        max_close_before_today = float("-inf")

    # -------------------------
    # Step 1: Price stop (触及止损价)
    # We check intraday low <= current_stop (stronger than close-based).
    # Signal: SELL (execute next day / next open in real trading)
    # -------------------------
    current_stop = float(pos.current_stop)
    if float(today["low"]) <= current_stop:
        return {
            "action": "SELL",
            "reason": f"STOP_HIT(low<=stop) stop={current_stop:.3f}",
            "new_stop": current_stop,
            "r_close": r_close,
            "hold_days": hold_days,
            "max_close_since_entry": max_close_before_today if max_close_before_today != float("-inf") else None,
        }

    # -------------------------
    # Step 2: Structural exit
    # 2a) Two consecutive closes below MA5(price)
    # 2b) Vol spike AND close not making new high close
    # -------------------------
    # 2a
    if prev is not None:
        prev_close = float(prev["close"])
        prev_ma5 = float(prev["ma5"])
        today_close = float(today["close"])
        today_ma5 = float(today["ma5"])
        if (prev_close < prev_ma5) and (today_close < today_ma5):
            return {
                "action": "SELL",
                "reason": "STRUCT_BREAK: 2 consecutive closes below MA5",
                "new_stop": current_stop,
                "r_close": r_close,
                "hold_days": hold_days,
                "max_close_since_entry": max_close_before_today if max_close_before_today != float("-inf") else None,
            }

    # 2b: vol spike + no advance (close not new high close)
    # vol spike uses today's volume compared to MA5(volume) of full series
    today_row_full = b[b["date"] == today["date"]].iloc[-1]
    vol_ma5 = float(today_row_full["vol_ma5"]) if pd.notna(today_row_full["vol_ma5"]) else None
    if vol_ma5 and vol_ma5 > 0:
        vol_spike = float(today["volume"]) >= vol_spike_mult * vol_ma5
        not_new_high_close = float(today["close"]) <= max_close_before_today
        if vol_spike and not_new_high_close:
            return {
                "action": "SELL",
                "reason": f"STRUCT_STALL: vol>= {vol_spike_mult}xMA5(vol) and close not new high close",
                "new_stop": current_stop,
                "r_close": r_close,
                "hold_days": hold_days,
                "max_close_since_entry": max_close_before_today if max_close_before_today != float("-inf") else None,
            }

    # -------------------------
    # Step 3: Profit-protection stop raise (close-based)
    # +2R -> stop >= entry + 1R
    # +1R -> stop >= entry
    # Stop is monotonic (never down)
    # -------------------------
    new_stop = current_stop
    if r_close >= 2.0:
        target = entry + risk  # lock +1R
        new_stop = max(new_stop, target)
        if new_stop > current_stop:
            reason = f"RAISE_STOP: close>=+2R, stop {current_stop:.3f}->{new_stop:.3f} (target {target:.3f})"
        else:
            reason = f"HOLD: close>=+2R but stop already >= target {target:.3f}"
    elif r_close >= 1.0:
        target = entry  # breakeven
        new_stop = max(new_stop, target)
        if new_stop > current_stop:
            reason = f"RAISE_STOP: close>=+1R, stop {current_stop:.3f}->{new_stop:.3f} (target {target:.3f})"
        else:
            reason = f"HOLD: close>=+1R but stop already >= target {target:.3f}"
    else:
        reason = "HOLD: no stop raise"

    # -------------------------
    # Step 4: Time stop (only if NOT in profit-protection)
    # You defined: once in +1R/+2R protection, time stop disabled.
    # We treat "in protection" as (new_stop >= entry) OR (current_stop >= entry).
    # "No progress": by default use max R achieved via max close since entry.
    # -------------------------
    in_protection = (new_stop >= entry) or (current_stop >= entry)
    if (not in_protection) and (hold_days >= time_stop_days):
        # progress proxy: max close since entry relative to risk
        max_close = float(b_entry["close"].max())
        max_r = calc_r(max_close, entry, s0)
        if pd.notna(max_r) and max_r < time_stop_progress_r:
            return {
                "action": "SELL",
                "reason": f"TIME_STOP: hold_days>={time_stop_days} and maxR<{time_stop_progress_r}",
                "new_stop": new_stop,
                "r_close": r_close,
                "hold_days": hold_days,
                "max_close_since_entry": max_close_before_today if max_close_before_today != float("-inf") else None,
            }

    return {
        "action": "HOLD",
        "reason": reason,
        "new_stop": new_stop,
        "r_close": r_close,
        "hold_days": hold_days,
        "max_close_since_entry": max_close_before_today if max_close_before_today != float("-inf") else None,
    }


def main():
    ap = argparse.ArgumentParser(description="Phase 1 exit decision engine (Day-2 shallow pullback, long-only).")
    ap.add_argument(
        "--positions",
        default=os.path.join(".", "adam_theory", "input", "phase1_exit_engine_sample", "positions.csv"),
        help="positions.csv",
    )
    ap.add_argument(
        "--bars",
        default=None,
        help="daily_bars.csv (OHLCV + ma5). If omitted, bars are fetched via Tushare pro_bar.",
    )
    ap.add_argument("--asof", default=None, help="YYYY-MM-DD, default = latest in bars")
    ap.add_argument("--out", default=None, help="output decisions csv")
    ap.add_argument("--token", default=None, help="Tushare token (or set env TUSHARE_TOKEN)")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD for API fetch (default: based on earliest entry)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD for API fetch (default: today)")
    ap.add_argument("--throttle", type=int, default=49, help="API calls per minute before sleeping (default: 49)")
    args = ap.parse_args()

    if args.out is None:
        current_ts = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M%S")
        args.out = os.path.join(".", "adam_theory", "output", f"exit_decisions_{current_ts}.csv")

    pos_df = pd.read_csv(args.positions)

    # If bars not provided, fetch via Tushare pro_bar.
    if args.bars:
        bars_df = pd.read_csv(args.bars)
        bars_df["date"] = pd.to_datetime(bars_df["date"])
        bars_df["symbol"] = bars_df["symbol"].astype(str)
    else:
        tmp = pos_df.copy()
        if "entry_date" not in tmp.columns:
            raise SystemExit("positions.csv must contain an 'entry_date' column when using API fetch")
        tmp["entry_date"] = pd.to_datetime(tmp["entry_date"], errors="coerce")
        earliest_entry = tmp["entry_date"].dropna().min()
        if pd.isna(earliest_entry):
            raise SystemExit("positions.csv has no valid entry_date values")

        # default start: 30 calendar days before earliest entry (gives MA5 buffer)
        default_start = (earliest_entry - pd.Timedelta(days=30)).normalize()
        start_dt = pd.to_datetime(args.start) if args.start else default_start
        end_dt = pd.to_datetime(args.end) if args.end else pd.Timestamp(date.today())

        symbols = [str(s).strip() for s in tmp["symbol"].dropna().unique().tolist() if str(s).strip()]
        if not symbols:
            raise SystemExit("positions.csv must contain at least one symbol")

        print(f"Fetching bars via Tushare: symbols={len(symbols)}, start={start_dt.date()}, end={end_dt.date()}")
        bars_df = fetch_daily_bars_from_tushare(
            symbols=symbols,
            start=start_dt,
            end=end_dt,
            token=args.token,
            throttle=args.throttle,
        )

        if bars_df.empty:
            raise SystemExit("No bars fetched. Check token/symbols/date range.")

    asof = pd.to_datetime(args.asof) if args.asof else bars_df["date"].max()

    positions = parse_positions(pos_df)

    decisions = []
    for p in positions:
        sym_bars = bars_df[bars_df["symbol"] == p.symbol].copy()
        if sym_bars.empty:
            decisions.append({"symbol": p.symbol, "action": "HOLD", "reason": "NO_SYMBOL_DATA", "new_stop": p.current_stop})
            continue

        d = phase1_decide_for_symbol(sym_bars, p, asof=asof)
        decisions.append({
            "date": asof.strftime("%Y-%m-%d"),
            "symbol": p.symbol,
            "action": d["action"],
            "reason": d["reason"],
            "new_stop": round(float(d["new_stop"]), 4),
            "r_close": None if pd.isna(d.get("r_close", float("nan"))) else round(float(d["r_close"]), 4),
            "hold_days": d.get("hold_days", None),
        })

    out_df = pd.DataFrame(decisions).sort_values(["action", "symbol"])
    out_df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"Saved: {args.out}")
    print(out_df.to_string(index=False))


if __name__ == "__main__":
    main()
