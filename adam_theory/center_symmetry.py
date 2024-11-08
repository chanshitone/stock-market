import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt

# 导入tushare
import tushare as ts

import pandas as pd
from datetime import datetime, timedelta


# 初始化pro接口

ts.set_token("8b8ed979c3736e2485771cea39630f5e083921c78ae181f5f1ec34f5")

pro = ts.pro_api()

# ts_code = "002468.SZ"
# ts_code = "600578.SH"
# ts_code = "300408.SZ"
# ts_code = "300010.SZ"
# ts_code = "600830.SH"
# ts_code = "002979.SZ"
ts_code = input("请输入股票代码：")

end_date = datetime.today().strftime("%Y%m%d")
print(end_date)
start_date = (datetime.today() - timedelta(days=60)).strftime("%Y%m%d")

# 拉取数据
df = pro.daily(
    **{
        "ts_code": ts_code,
        "trade_date": "",
        "start_date": start_date,
        "end_date": end_date,
        "offset": "",
        "limit": "",
    },
    fields=[
        "ts_code",
        "trade_date",
        "open",
        "high",
        "low",
        "close",
        "pre_close",
        "change",
        "pct_chg",
        "vol",
        "amount",
    ],
)

# 确保数据是按日期升序排列
df = df.sort_values(by="trade_date")

# 提取过去20天的数据
df_last_30_days = df.iloc[-32:]
print(df_last_30_days)

# rename columns trade_date to Date, open to Open, high to High, low to Low, close to Close, vol to Volume
df_last_30_days.rename(
    columns={
        "trade_date": "Date",
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "vol": "Volume",
    },
    inplace=True,
)

# 创建一个空的列表，用于存储中心对称数据
center_symmetry_data = []

center_price = df_last_30_days.iloc[-1]["Close"]

temp_df = df_last_30_days.copy().sort_values(by="Date").iloc[:-1]

temp_df = temp_df.sort_values(by="Date", ascending=False)

# 计算每一天的中心对称数据
for i in range(len(temp_df)):
    row = temp_df.iloc[i]
    print(row)

    # 获取每一天的开盘价、最高价、最低价和收盘价
    open_price = row["Open"]
    high_price = row["High"]
    low_price = row["Low"]
    close_price = row["Close"]

    date_obj = datetime.strptime(end_date, "%Y%m%d")
    new_date_obj = date_obj + timedelta(days=i+1)
    new_date_str = new_date_obj.strftime("%Y%m%d")

    date = new_date_str

    # 计算中心对称的各个点
    center_symmetry_date = date
    center_symmetry_open = 2 * center_price - close_price
    center_symmetry_high = 2 * center_price - low_price
    center_symmetry_low = 2 * center_price - high_price
    center_symmetry_close = 2 * center_price - open_price

    # 将计算结果存储到列表中
    center_symmetry_data.append(
        {
            "Date": center_symmetry_date,
            "Open": center_symmetry_open,
            "High": center_symmetry_high,
            "Low": center_symmetry_low,
            "Close": center_symmetry_close,
            "Volume": 0,  # 这里的成交量设置为0，因为是生成的虚拟数据
        }
    )

# 将中心对称数据转换为 DataFrame
center_symmetry_df = pd.DataFrame(center_symmetry_data)

print(center_symmetry_df)

# sort the center_symmetry_df by Date
center_symmetry_df = center_symmetry_df.sort_values(by="Date")

# first 10 days lowest Low price and highest High price in center_symmetry_df
lowest_low_price_10_days = center_symmetry_df.head(10)["Low"].min()
potential_lost_percent_10_days = (
    (lowest_low_price_10_days - center_price) / center_price * 100
)
highest_high_price_10_days = center_symmetry_df.head(10)["High"].max()
potential_profit_percent_10_days = (
    (highest_high_price_10_days - center_price) / center_price * 100
)

# 20 days lowest Low price and highest High price in center_symmetry_df
lowest_low_price_20_days = center_symmetry_df.head(20)["Low"].min()
potential_lost_percent_20_days = (
    (lowest_low_price_20_days - center_price) / center_price * 100
)
highest_high_price_20_days = center_symmetry_df.head(20)["High"].max()
potential_profit_percent_20_days = (
    (highest_high_price_20_days - center_price) / center_price * 100
)

# 30 days lowest Low price and highest High price in center_symmetry_df
lowest_low_price_30_days = center_symmetry_df["Low"].min()
potential_lost_percent_30_days = (
    (lowest_low_price_30_days - center_price) / center_price * 100
)
highest_high_price_30_days = center_symmetry_df["High"].max()
potential_profit_percent_30_days = (
    (highest_high_price_30_days - center_price) / center_price * 100
)

# merge the two dataframes
df_last_30_days = pd.concat([df_last_30_days, center_symmetry_df])

# 确保数据是按日期升序排列
df_last_30_days = df_last_30_days.sort_values(by="Date")

# 设置图表样式
style = mpf.make_mpf_style(base_mpf_style="charles")


# Ensure 'Date' column is set as the index and is a DatetimeIndex
if df_last_30_days.index.name != "Date":
    df_last_30_days.set_index("Date", inplace=True)

if not isinstance(df_last_30_days.index, pd.DatetimeIndex):
    df_last_30_days.index = pd.to_datetime(df_last_30_days.index)

fig, ax = plt.subplots(figsize=(8, 6))
# create folder if not exist C:\Users\chans\OneDrive\Desktop\中心对称图\{end_date}
import os

output_dir = f"C:\\Users\\chans\\OneDrive\\Desktop\\中心对称图\\{end_date}"
os.makedirs(output_dir, exist_ok=True)

# 绘制原始 K 线图
mpf.plot(
    df_last_30_days,
    type="candle",
    style=style,
    ax=ax,
    ylabel="Price",
)

fig.suptitle(f"{ts_code} Center Symmetry (Last 30 Days)")

# add comment to the plot
plt.text(
    0.5,
    0.05,
    f"""
    current_price: {center_price}
    L_10D: {lowest_low_price_10_days:.2f}, PL_10D: {potential_lost_percent_10_days:.2f}%, H_10D: {highest_high_price_10_days:.2f}, PP_10D: {potential_profit_percent_10_days:.2f}%
    L_20D: {lowest_low_price_20_days:.2f}, PL_20D: {potential_lost_percent_20_days:.2f}%, H_20D: {highest_high_price_20_days:.2f}, PP_20D: {potential_profit_percent_20_days:.2f}%
    L_30D: {lowest_low_price_30_days:.2f}, PL_30D: {potential_lost_percent_30_days:.2f}%, H_30D: {highest_high_price_30_days:.2f}, PP_30D: {potential_profit_percent_30_days:.2f}%
    """,
    horizontalalignment="center",
    verticalalignment="center",
    transform=ax.transAxes,
    fontsize=10,
    color="red",
)

# save the plot to a file to C:\Users\chans\OneDrive\Desktop\中心对称图\{end_date}\{ts_code}_center_symmetry.png
plt.tight_layout()
plt.savefig(f"{output_dir}/{ts_code}_center_symmetry.png")

# 显示图表
plt.show()
