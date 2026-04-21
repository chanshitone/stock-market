import os
import sys
import time
import warnings

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, datetime, timedelta

import pandas as pd
import tushare as ts

from env_config import configure_tushare
from phase1_scanner import FETCH_PRO_BAR_CALLS_PER_MINUTE, fetch_pro_bar
from utils import normalize_ts_code


def normalize_detect_date(raw_value: str) -> str | None:
    if raw_value is None:
        return None

    digits = "".join(ch for ch in str(raw_value).strip() if ch.isdigit())
    if len(digits) != 8:
        return None

    try:
        datetime.strptime(digits, "%Y%m%d")
    except ValueError:
        return None
    return digits


def load_candidates(candidate_file: str) -> pd.DataFrame:
    candidates = pd.read_csv(candidate_file, dtype=str)
    missing_columns = {"ts_code", "detect_date"} - set(candidates.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"candidate file is missing required columns: {missing}")

    return candidates[["ts_code", "detect_date"]].copy()


def evaluate_phase1_rule(df: pd.DataFrame) -> dict[str, float | str] | None:
    if df is None or df.empty:
        return None

    ordered = df.sort_values("trade_date", ascending=False).reset_index(drop=True)
    if len(ordered) < 14:
        return None

    latest_info = ordered.head(1)
    ma_v_5 = latest_info["ma_v_5"].values[0]
    today_v = latest_info["vol"].values[0]
    if pd.isna(ma_v_5) or pd.isna(today_v) or float(ma_v_5) <= 0:
        return None

    ratio = round(float(today_v) / float(ma_v_5), 2)
    if ratio < 2.0:
        return None

    previous_13 = ordered.iloc[1:14].reset_index(drop=True)
    highest_high_13 = previous_13["high"].max()
    latest_close = float(latest_info["close"].values[0])
    latest_low = float(latest_info["low"].values[0])
    latest_high = float(latest_info["high"].values[0])
    intraday_range = latest_high - latest_low

    if pd.isna(highest_high_13) or latest_close < float(highest_high_13):
        return None

    if intraday_range <= 0:
        return None

    close_strength = round((latest_close - latest_low) / intraday_range, 2)
    if close_strength < 0.7:
        return None

    return {
        "trade_date": str(latest_info["trade_date"].values[0]),
        "ratio": ratio,
        "close_strength": close_strength,
        "highest_high_13": round(float(highest_high_13), 2),
    }


def main():
    start_time = pd.Timestamp.now()
    print(f"Current time: {start_time}")
    warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
    configure_tushare(ts)

    current_dir = os.path.dirname(__file__)
    today = date.today()
    candidate_file = os.path.join(current_dir, "input", "gap_up", "candidate.csv")
    candidates = load_candidates(candidate_file)

    output_df = pd.DataFrame(
        columns=[
            "ts_code",
            "detect_date",
            "trade_date",
            "ratio",
            "close_strength",
            "highest_high_13",
        ]
    )

    fetch_pro_bar_calls_in_window = 0
    fetch_pro_bar_window_start = time.monotonic()

    for _, candidate in candidates.iterrows():
        ts_code = normalize_ts_code(candidate["ts_code"])
        detect_date = normalize_detect_date(candidate["detect_date"])
        if not ts_code:
            print(f"Warning: Cannot normalize stock code: '{candidate['ts_code']}'")
            continue
        if not detect_date:
            print(f"Warning: Invalid detect_date for {ts_code}: '{candidate['detect_date']}'")
            continue

        try:
            now = time.monotonic()
            if now - fetch_pro_bar_window_start >= 60:
                fetch_pro_bar_window_start = now
                fetch_pro_bar_calls_in_window = 0

            fetch_pro_bar_calls_in_window += 1
            if fetch_pro_bar_calls_in_window > FETCH_PRO_BAR_CALLS_PER_MINUTE:
                print("Sleep for 60 seconds")
                time.sleep(60)
                fetch_pro_bar_window_start = time.monotonic()
                fetch_pro_bar_calls_in_window = 1

            start_date = (
                datetime.strptime(detect_date, "%Y%m%d") - timedelta(days=60)
            ).strftime("%Y%m%d")
            df = fetch_pro_bar(ts_code, start_date, detect_date)
            result = evaluate_phase1_rule(df)
            if result is None:
                continue

            output_df.loc[len(output_df)] = {
                "ts_code": ts_code,
                "detect_date": detect_date,
                "trade_date": result["trade_date"],
                "ratio": result["ratio"],
                "close_strength": result["close_strength"],
                "highest_high_13": result["highest_high_13"],
            }
        except Exception as exc:
            print(
                f"Error processing candidate '{ts_code}' with detect_date '{detect_date}': {exc}"
            )
            continue

    if not output_df.empty:
        output_df = output_df.sort_values(
            by=["detect_date", "ratio"],
            ascending=[False, False],
        )
        output_file = os.path.join(
            current_dir, "output", f"phase1_candidate_scan_{today}.csv"
        )
        output_df.to_csv(output_file, index=False)
        print(f"Saved {len(output_df)} matches to {output_file}")
    else:
        print("No candidates matched the phase1 rule")

    end_time = pd.Timestamp.now()
    print(f"Current time: {end_time}")
    print(f"Time elapsed: {end_time - start_time}")


if __name__ == "__main__":
    main()