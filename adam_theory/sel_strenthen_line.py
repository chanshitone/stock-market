import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import tushare as ts
import warnings
import pandas as pd
from extract_stocks import extract_stocks
from utils import normalize_ts_code

# start time
start_time = pd.Timestamp.now()
print(f"Current time: {start_time}")
warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
today = date.today()
end_date = today.strftime("%Y%m%d")
start_date = (today - timedelta(days=365)).strftime("%Y%m%d")

# Extract stocks from gap up picture
checking_stocks = extract_stocks("input/picture/breakthrough/13", f"checking_stocks_{today}.txt")

# Analyze stocks
current_dir = os.path.dirname(__file__)

outputDf = pd.DataFrame(columns=["stock", "ratio"])

for stock in checking_stocks:
    ts_code = normalize_ts_code(stock)
    if not ts_code:
        print(f"Warning: Cannot normalize stock code: '{stock}'")
        continue
    try:
        df = ts.pro_bar(
            ts_code=ts_code,
            adj="qfq",
            start_date=start_date,
            end_date=end_date,
            ma=[13],
            retry_count=5,
        )
        # get first row of the DataFram
        latest_info = df.iloc[0:1]
        # get second row of the DataFrame
        yst_info = df.iloc[1:2]
        # get 3rd row of the DataFrame
        third_info = df.iloc[2:3]
        m_v_13 = latest_info["ma_v_13"].values[0]
        today_v = latest_info["vol"].values[0]
        ratio = today_v / m_v_13
        if (
            latest_info["close"].values[0] > latest_info["ma13"].values[0]
            and yst_info["close"].values[0] > yst_info["ma13"].values[0]
            and third_info["close"].values[0] < third_info["ma13"].values[0]
        ):
            print(f"{stock} 连续两天收盘价站上13日均线")
            print(f"{stock} ma_v_13: {m_v_13}, today_v: {today_v}, ratio: {ratio}")
            # add the stock to dataset with ratio
            outputDf.loc[len(outputDf)] = {
                "stock": stock,
                "ratio": ratio
            }

        elif (
            latest_info["close"].values[0] > latest_info["ma13"].values[0]
            and yst_info["close"].values[0] < yst_info["ma13"].values[0]
        ):
            print(f"{stock} 今日收盘价突破13日均线")
            print(f"{stock} ma_v_13: {m_v_13}, today_v: {today_v}, ratio: {ratio}")
            outputDf.loc[len(outputDf)] = {
                "stock": stock,
                "ratio": ratio
            }
    except Exception as e:
        print(
            f"Error processing stock '{stock}' when checking financial indicator: {e}"
        )
        continue

if not outputDf.empty:
    outputDf.sort_values(by="ratio", ascending=False, inplace=True)
    output_file = os.path.join(current_dir, "output", f"strength_stocks_{today}.csv")
    outputDf.to_csv(output_file, index=False)

end_time = pd.Timestamp.now()
print(f"Current time: {end_time}")
print(f"Time elapsed: {end_time - start_time}")
