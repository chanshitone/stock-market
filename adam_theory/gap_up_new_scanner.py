import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import tushare as ts
import warnings
import pandas as pd
from extract_stocks import extract_stocks
from env_config import configure_tushare
from utils import normalize_ts_code


FETCH_PRO_BAR_CALLS_PER_MINUTE = 200
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
PICTURE_PATH = "input/picture/breakthrough/gap_up"


def fetch_pro_bar(ts_code: str, start_date: str, end_date: str):
    return ts.pro_bar(
        ts_code=ts_code,
        adj="qfq",
        start_date=start_date,
        end_date=end_date,
        retry_count=5,
    )


def has_picture_inputs(picture_path: str) -> bool:
    image_dir = os.path.join(os.path.dirname(__file__), picture_path)
    if not os.path.isdir(image_dir):
        return False
    return any(name.lower().endswith(IMAGE_EXTENSIONS) for name in os.listdir(image_dir))


def evaluate_gap_up_rule(df: pd.DataFrame) -> dict | None:
    """Return gap-up metrics if the stock meets all criteria, else None.

    Gap-up condition: today's low > previous day's high (clean gap, not filled).
    Momentum filter:  pct_chg > 1%  OR  close_strength >= 5%
                      where close_strength = (close - low) / (high - low) * 100.
    Computed outputs: body = close - open,  gap = today_low - prev_high.
    """
    if df is None or df.empty:
        return None

    ordered = df.sort_values("trade_date", ascending=False).reset_index(drop=True)
    if len(ordered) < 2:
        return None

    latest = ordered.iloc[0]
    prev = ordered.iloc[1]

    latest_low = float(latest["low"])
    latest_high = float(latest["high"])
    latest_open = float(latest["open"])
    latest_close = float(latest["close"])
    prev_high = float(prev["high"])
    latest_volume = float(latest["vol"]) if not pd.isna(latest["vol"]) else 0.0

    # Gap-up condition: today's entire range is above previous day's high
    if latest_low <= prev_high:
        return None

    # pct_chg is provided directly by pro_bar
    pct_chg = float(latest["pct_chg"]) if not pd.isna(latest["pct_chg"]) else 0.0

    intraday_range = latest_high - latest_low
    if intraday_range > 0:
        close_strength_pct = (latest_close - latest_low) / intraday_range * 100
    else:
        close_strength_pct = 0.0

    # Momentum filter: at least one condition must pass
    if pct_chg <= 1.0 and close_strength_pct < 50.0:
        return None

    body = round(latest_close - latest_open, 3)
    gap = round(latest_low - prev_high, 3)
    output_volume = latest_volume / 10000 if latest_volume > 100000 else latest_volume

    return {
        "close": round(latest_close, 3),
        "gap": gap,
        "volumn": int(output_volume) if output_volume.is_integer() else round(output_volume, 2),
        "pct_chg": round(pct_chg, 2),
        "close_strength_pct": round(close_strength_pct, 2),
        "body": body,
    }


def analyze_stocks(stocks: list[str], start_date: str, end_date: str) -> pd.DataFrame:
    output_df = pd.DataFrame(
        columns=[
            "stock",
            "075_v",
            "b_price",
            "v_ful",
            "p_ful",
            "can_b",
            "status",
            "reason",
            "close",
            "gap",
            "volumn",
        ]
    )

    fetch_calls = 0
    window_start = time.monotonic()

    for stock in stocks:
        ts_code = normalize_ts_code(stock)
        if not ts_code:
            print(f"Warning: Cannot normalize stock code: '{stock}'")
            continue

        try:
            now = time.monotonic()
            if now - window_start >= 60:
                window_start = now
                fetch_calls = 0

            fetch_calls += 1
            if fetch_calls > FETCH_PRO_BAR_CALLS_PER_MINUTE:
                print("Sleep for 60 seconds")
                time.sleep(60)
                window_start = time.monotonic()
                fetch_calls = 1

            df = fetch_pro_bar(ts_code, start_date, end_date)
            result = evaluate_gap_up_rule(df)
            if result is None:
                continue

            print(
                f"{stock}  pct_chg: {result['pct_chg']}%  "
                f"close_strength: {result['close_strength_pct']}%  "
                f"body: {result['body']}  gap: {result['gap']}"
            )

            output_df.loc[len(output_df)] = {
                "stock": stock,
                "075_v": round(result["volumn"] * 0.75, 2),
                "b_price": round(result["gap"] * 0.8 + result["close"], 3),
                "v_ful": "",
                "p_ful": "",
                "can_b": "",
                "status": "",
                "reason": "",
                "close": result["close"],
                "gap": result["gap"],
                "volumn": result["volumn"],
            }
        except Exception as e:
            print(f"Error processing stock '{stock}': {e}")
            continue

    return output_df


def add_excel_formulas(output_df: pd.DataFrame) -> pd.DataFrame:
    output_df = output_df.copy()
    for row_idx in range(len(output_df)):
        excel_row = row_idx + 2
        output_df.at[row_idx, "can_b"] = f"=AND(D{excel_row}=1,E{excel_row}=1)"
    return output_df


def main():
    start_time = pd.Timestamp.now()
    print(f"Current time: {start_time}")
    warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
    configure_tushare(ts)

    today = date.today()
    timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M%S")
    end_date = today.strftime("%Y%m%d")
    # 20 days back is enough to guarantee at least 2 trading days
    start_date = (today - timedelta(days=20)).strftime("%Y%m%d")

    if not has_picture_inputs(PICTURE_PATH):
        print(f"No pictures found under {PICTURE_PATH}")
        return

    stock_output_name = f"gapsup_stocks_{timestamp}.txt"
    stocks = extract_stocks(PICTURE_PATH, stock_output_name)
    if not stocks:
        print("No stocks extracted from images")
        return

    output_df = analyze_stocks(stocks, start_date, end_date)
    if output_df.empty:
        print("No stocks matched the gap-up criteria")
        return

    output_df.sort_values(by="gap", ascending=False, inplace=True)
    output_df.reset_index(drop=True, inplace=True)
    output_df = add_excel_formulas(output_df)
    output_file = os.path.join(
        os.path.dirname(__file__),
        "output",
        f"gap_up_scanner_{timestamp}.xlsx",
    )
    output_df.to_excel(output_file, index=False)
    print(f"Saved {len(output_df)} rows to {output_file}")

    end_time = pd.Timestamp.now()
    print(f"Time elapsed: {end_time - start_time}")


if __name__ == "__main__":
    main()
