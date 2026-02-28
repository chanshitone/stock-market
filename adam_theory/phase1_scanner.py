import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import tushare as ts
import warnings
import pandas as pd
from extract_stocks import extract_stocks
from utils import normalize_ts_code


def fetch_pro_bar(ts_code: str, start_date: str, end_date: str):
    return ts.pro_bar(
        ts_code=ts_code,
        adj="qfq",
        start_date=start_date,
        end_date=end_date,
        ma=[5],
        retry_count=5,
    )


def main():
    # start time
    start_time = pd.Timestamp.now()
    print(f"Current time: {start_time}")
    warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
    today = date.today()
    end_date = today.strftime("%Y%m%d")
    start_date = (today - timedelta(days=60)).strftime("%Y%m%d")

    # Extract stocks from gap up picture
    gap_up_stocks = extract_stocks(
        "input/picture/breakthrough/brk", f"brk_stocks_{today}.txt"
    )

    # Analyze stocks
    current_dir = os.path.dirname(__file__)

    outputDf = pd.DataFrame(
        columns=["stock", "ratio", "close_strength", "highest_high_13"]
    )

    count_allowed_per_minute = 0

    for stock in gap_up_stocks:
        ts_code = normalize_ts_code(stock)
        if not ts_code:
            print(f"Warning: Cannot normalize stock code: '{stock}'")
            continue

        try:
            count_allowed_per_minute += 1
            if count_allowed_per_minute == 49:
                print("Sleep for 60 seconds")
                count_allowed_per_minute = 0
                time.sleep(60)

            df = fetch_pro_bar(ts_code, start_date, end_date)
            # get first row of the DataFram
            latest_info = df.head(1)
            m_v_5 = latest_info["ma_v_5"].values[0]
            today_v = latest_info["vol"].values[0]
            ratio = round(today_v / m_v_5, 2)
            if ratio >= 2.0:
                # calculate the highest close price in last 13 days
                # get the 2nd to 14th rows of the DataFrame (exclude the latest row)
                df = df.iloc[1:14].reset_index(drop=True)
                highest_high_13 = df["high"].max()
                print(f"{stock} highest_high_13: {highest_high_13}")
                if latest_info["close"].values[0] >= highest_high_13:
                    close_strength = round(
                        (latest_info["close"].values[0] - latest_info["low"].values[0])
                        / (
                            latest_info["high"].values[0] - latest_info["low"].values[0]
                        ),
                        2,
                    )
                    print(f"{stock} close_strength: {close_strength}")
                    if close_strength >= 0.7:
                        outputDf.loc[len(outputDf)] = {
                            "stock": stock,
                            "ratio": ratio,
                            "close_strength": close_strength,
                            "highest_high_13": highest_high_13,
                        }
        except Exception as e:
            print(
                f"Error processing stock '{stock}' when checking financial indicator: {e}"
            )
            continue

    if not outputDf.empty:
        outputDf.sort_values(by="ratio", ascending=False, inplace=True)
        output_file = os.path.join(
            current_dir, "output", f"new_scanner_with_volume_{today}.csv"
        )
        outputDf.to_csv(output_file, index=False)

    end_time = pd.Timestamp.now()
    print(f"Current time: {end_time}")
    print(f"Time elapsed: {end_time - start_time}")


if __name__ == "__main__":
    main()
