import mplfinance as mpf
import pandas as pd
import matplotlib.pyplot as plt

# 假设股票数据存储在 CSV 文件中
# 导入tushare
import tushare as ts

import pandas as pd
from datetime import datetime, timedelta


# 初始化pro接口

ts.set_token("8b8ed979c3736e2485771cea39630f5e083921c78ae181f5f1ec34f5")

pro = ts.pro_api()

ts_code = "002468.SZ"
ts_code = "600578.SH"
ts_code = "300408.SZ"

# 拉取数据
df = pro.daily(
    **{
        "ts_code": ts_code,
        "trade_date": "",
        "start_date": 20240905,
        "end_date": 20241105,
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
    ]
)

# 确保数据是按日期升序排列
df = df.sort_values(by="trade_date")

# 提取过去20天的数据
df_last_20_days = df.iloc[-32:]

# rename columns trade_date to Date, open to Open, high to High, low to Low, close to Close, vol to Volume
df_last_20_days.rename(
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

date_str = "20241105"

center_price = df_last_20_days.iloc[-1]["Close"]

temp_df = df_last_20_days.copy().iloc[:-1]

# 计算每一天的中心对称数据
for i in range(len(df_last_20_days)):
    row = df_last_20_days.iloc[-i]

    # 获取每一天的开盘价、最高价、最低价和收盘价
    open_price = row["Open"]
    high_price = row["High"]
    low_price = row["Low"]
    close_price = row["Close"]

    date_obj = datetime.strptime(date_str, "%Y%m%d")
    new_date_obj = date_obj + timedelta(days=i)
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
center_symmetry_df = pd.DataFrame(center_symmetry_data, index=df_last_20_days.index)

# merge the two dataframes
df_last_20_days = pd.concat([df_last_20_days, center_symmetry_df])

# 设置图表样式
style = mpf.make_mpf_style(base_mpf_style="charles")


# Ensure 'Date' column is set as the index and is a DatetimeIndex
if df_last_20_days.index.name != "Date":
    df_last_20_days.set_index("Date", inplace=True)

if not isinstance(df_last_20_days.index, pd.DatetimeIndex):
    df_last_20_days.index = pd.to_datetime(df_last_20_days.index)

# 使用 matplotlib 创建图表布局并显示两幅图
fig, axes = plt.subplots(sharex=True, figsize=(10, 8))

# 绘制原始 K 线图
mpf.plot(
    df_last_20_days,
    type="candle",
    style=style,
    ax=axes,
    ylabel="Price",
)

# # Ensure 'Date' column is set as the index and is a DatetimeIndex
# if center_symmetry_df.index.name != "Date":
#     center_symmetry_df.set_index("Date", inplace=True)

# if not isinstance(center_symmetry_df.index, pd.DatetimeIndex):
#     center_symmetry_df.index = pd.to_datetime(center_symmetry_df.index)

# # 在同一图表上绘制中心对称 K 线图
# mpf.plot(
#     center_symmetry_df,
#     type="candle",
#     style=style,
#     ax=axes[1],
#     ylabel="Price",
# )

fig.suptitle("Stock Price and Symmetry (Last 30 Days)")

# 显示图表
plt.tight_layout()
plt.show()
