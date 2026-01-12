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
gap_up_stocks = extract_stocks(
    "input/picture/breakthrough/gap_up", f"gap_up_stocks_{today}.txt"
)

# Analyze stocks
current_dir = os.path.dirname(__file__)

outputDf = pd.DataFrame(columns=["stock", "ratio"])

for stock in gap_up_stocks:
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
        m_v_13 = latest_info["ma_v_13"].values[0]
        today_v = latest_info["vol"].values[0]
        ratio = today_v / m_v_13
        if ratio > 2.0:
            outputDf.loc[len(outputDf)] = {"stock": stock, "ratio": ratio}
    except Exception as e:
        print(
            f"Error processing stock '{stock}' when checking financial indicator: {e}"
        )
        continue

if not outputDf.empty:
    outputDf.sort_values(by="ratio", ascending=False, inplace=True)
    output_file = os.path.join(current_dir, "output", f"gap_up_with_volume_{today}.csv")
    outputDf.to_csv(output_file, index=False)

end_time = pd.Timestamp.now()
print(f"Current time: {end_time}")
print(f"Time elapsed: {end_time - start_time}")
