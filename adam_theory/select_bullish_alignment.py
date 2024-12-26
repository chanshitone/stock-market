import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
import tushare as ts
import warnings
import pandas as pd

#start time
start_time = pd.Timestamp.now()
print(f"Current time: {start_time}")
warnings.filterwarnings("ignore", category=FutureWarning, module="tushare")
today = date.today()
end_date = today.strftime("%Y%m%d")
start_date = (today - timedelta(days=365)).strftime("%Y%m%d")

# read the stock list from ./input/all_company.xlsx
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "input", "all_company.xlsx")
all_company_df = pd.read_excel(file_path)

bullish_alignment_df = pd.DataFrame(
    columns=["ts_code", "name", "close", "ma50", "ma150", "ma200"]
)

# loop all the stocks in all_company_df
for index, row in all_company_df.iterrows():

    ts_code = row["ts_code"]
    name = row["name"]
    exchange = row["exchange"]
    if "ST" not in name and exchange not in ["SSE", "SZSE"]:
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
                print(f"{name} 多头排列")
                # add the stock to the bullish_alignment_df
                new_row = {
                    "ts_code": ts_code,
                    "name": name,
                    "close": latest_info["close"].values[0],
                    "ma50": latest_info["ma50"].values[0],
                    "ma150": latest_info["ma150"].values[0],
                    "ma200": latest_info["ma200"].values[0],
                }
                bullish_alignment_df = pd.concat(
                    [bullish_alignment_df, pd.DataFrame([new_row])],
                    ignore_index=True
                )

            else:
                print(f"{name} 不是多头排列")
        except Exception as e:
            print(f"Error processing {name}: {e}")

bullish_alignment_df.to_csv(
    os.path.join(current_dir, "output", f"{end_date}_bullish_alignment.csv"),
    index=False,
)

end_time = pd.Timestamp.now()
print(f"Current time: {end_time}")
print(f"Time elapsed: {end_time - start_time}")
