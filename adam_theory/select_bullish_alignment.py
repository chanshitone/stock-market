import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import tushare as ts
import warnings
import pandas as pd
from utils import normalize_ts_code

# start time
start_time = pd.Timestamp.now()
print(f"Current time: {start_time}")
warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
today = date.today()
end_date = today.strftime("%Y%m%d")
start_date = (today - timedelta(days=365)).strftime("%Y%m%d")

# read the stock list from ./output/all_company.xlsx
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "output", "daily_stocks_20250414_232127.txt")
# read the stock list from ./output/health_stocks.txt
with open(file_path, "r") as f:
    stock_list = f.readlines()
    # remove the newline character
    stock_list = [stock.strip() for stock in stock_list]
    # remove duplicate stocks
    stock_list = list(set(stock_list))

# loop all the stocks
for stock in stock_list:

    ts_code = normalize_ts_code(stock)
    if not ts_code:
        print(f"Warning: Cannot normalize stock code: '{stock}'")
        continue
    df = ts.pro_bar(
        ts_code=ts_code,
        adj="qfq",
        start_date=start_date,
        end_date=end_date,
        ma=[50, 150, 200],
    )

    try:
        latest_info = df.head(1)
        if (
            latest_info["close"].values[0] > latest_info["ma50"].values[0]
            and latest_info["ma50"].values[0] > latest_info["ma150"].values[0]
            and latest_info["ma150"].values[0] > latest_info["ma200"].values[0]
        ):
            print(f"{stock} 多头排列")
        else:
            print(f"{stock} 空头排列")
    except Exception as e:
        print(f"Error processing {stock}: {e}")


end_time = pd.Timestamp.now()
print(f"Current time: {end_time}")
print(f"Time elapsed: {end_time - start_time}")
# Save the results to a file
output_file = os.path.join(current_dir, "output", "bullish_alignment_results.txt")
