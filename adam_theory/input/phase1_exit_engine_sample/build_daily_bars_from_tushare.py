import argparse
import os
import time
from datetime import date, timedelta

import pandas as pd
import tushare as ts


def _to_yyyymmdd(d: pd.Timestamp | date) -> str:
    if isinstance(d, pd.Timestamp):
        d = d.date()
    return d.strftime("%Y%m%d")


def _normalize_pro_bar(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize tushare pro_bar output to exit-engine schema."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["symbol", "date", "open", "high", "low", "close", "volume", "ma5"])

    out = df.copy()

    # pro_bar usually returns trade_date as YYYYMMDD string and is often sorted desc by date
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

    # ma=[5] usually creates ma5
    if "ma5" not in out.columns:
        raise ValueError("pro_bar result missing ma5 (did you pass ma=[5]?)")

    out["symbol"] = str(symbol)

    out = out[["symbol", "date", "open", "high", "low", "close", "volume", "ma5"]]
    out = out.dropna(subset=["date"]).sort_values(["symbol", "date"])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Build daily_bars.csv for phase1_exit_engine via Tushare pro_bar.")
    ap.add_argument("--positions", required=True, help="positions.csv (symbol column should be ts_code)")
    ap.add_argument("--out", required=True, help="output daily_bars.csv")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (default: today-60d)")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--token", default=None, help="Tushare token (or set env TUSHARE_TOKEN)")
    ap.add_argument("--throttle", type=int, default=49, help="calls per minute before sleeping (default: 49)")
    args = ap.parse_args()

    token = args.token or os.getenv("TUSHARE_TOKEN")
    if not token:
        raise SystemExit("Missing Tushare token. Provide --token or set env TUSHARE_TOKEN")

    ts.set_token(token)

    today = date.today()
    start_dt = pd.to_datetime(args.start) if args.start else pd.Timestamp(today - timedelta(days=60))
    end_dt = pd.to_datetime(args.end) if args.end else pd.Timestamp(today)

    start_date = _to_yyyymmdd(start_dt)
    end_date = _to_yyyymmdd(end_dt)

    pos_df = pd.read_csv(args.positions)
    if "symbol" not in pos_df.columns:
        raise SystemExit("positions.csv must contain a 'symbol' column")

    symbols = [str(s).strip() for s in pos_df["symbol"].dropna().unique().tolist() if str(s).strip()]
    if not symbols:
        raise SystemExit("No symbols found in positions.csv")

    all_rows: list[pd.DataFrame] = []

    count_allowed_per_minute = 0
    for sym in symbols:
        count_allowed_per_minute += 1
        if args.throttle > 0 and count_allowed_per_minute >= args.throttle:
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

        norm = _normalize_pro_bar(df, symbol=sym)
        if norm.empty:
            print(f"Warning: no data for {sym}")
            continue
        all_rows.append(norm)

    out_df = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame(
        columns=["symbol", "date", "open", "high", "low", "close", "volume", "ma5"]
    )

    out_df.to_csv(args.out, index=False, encoding="utf-8-sig")
    print(f"Saved: {args.out}")
    print(out_df.tail(10).to_string(index=False))


if __name__ == "__main__":
    main()
