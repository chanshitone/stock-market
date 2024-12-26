# 导入tushare
import tushare as ts
from datetime import datetime
from constants import YOY_BENCHMARK


def check_finance_yoy(ts_code, name=None, benchmark=YOY_BENCHMARK):
    if name is None:
        name = ts_code

    # 初始化pro接口
    pro = ts.pro_api("8b8ed979c3736e2485771cea39630f5e083921c78ae181f5f1ec34f5")

    # 拉取数据
    df = pro.fina_indicator(
        **{
            "ts_code": ts_code,
            "ann_date": "",
            "start_date": "",
            "end_date": "",
            "period": "",
            "update_flag": "",
            "limit": "",
            "offset": "",
        },
        fields=[
            "ts_code",
            "ann_date",
            "end_date",
            "q_eps",
            "q_dtprofit",
            "q_sales_yoy",
        ],
    )
    # print(df.head(10))

    # 计算最近三季度的扣非净利润和eps的同比增长率
    df = df.drop_duplicates(subset="end_date").sort_values(
        by="end_date", ascending=False
    )

    latest_q_sales_yoy = df.iloc[0]["q_sales_yoy"]
    latest_q_dtprofit = df.iloc[0]["q_dtprofit"]
    latest_q_eps = df.iloc[0]["q_eps"]

    latest_q_dtprofit_date = df.iloc[0]["end_date"]
    date_obj = datetime.strptime(latest_q_dtprofit_date, "%Y%m%d")
    yoy_date_obj = date_obj.replace(year=date_obj.year - 1)
    yoy_date = yoy_date_obj.strftime("%Y%m%d")

    last_year_row = df[df["end_date"] == yoy_date].iloc[0]
    last_year_q_dtprofit = last_year_row["q_dtprofit"]
    last_year_q_eps = last_year_row["q_eps"]
    q_dtprofit_yoy = (latest_q_dtprofit - last_year_q_dtprofit) / abs(
        last_year_q_dtprofit
    )
    q_eps_yoy = (latest_q_eps - last_year_q_eps) / abs(last_year_q_eps)

    second_q_sales_yoy = df.iloc[1]["q_sales_yoy"]
    second_q_dtprofit = df.iloc[1]["q_dtprofit"]
    second_q_eps = df.iloc[1]["q_eps"]

    second_q_dtprofit_date = df.iloc[1]["end_date"]
    second_yoy_date_obj = datetime.strptime(second_q_dtprofit_date, "%Y%m%d")
    second_yoy_date_obj = second_yoy_date_obj.replace(year=second_yoy_date_obj.year - 1)
    second_yoy_date = second_yoy_date_obj.strftime("%Y%m%d")

    second_last_year_row = df[df["end_date"] == second_yoy_date].iloc[0]
    second_last_year_q_dtprofit = second_last_year_row["q_dtprofit"]
    second_last_year_q_eps = second_last_year_row["q_eps"]
    second_q_dtprofit_yoy = (second_q_dtprofit - second_last_year_q_dtprofit) / abs(
        second_last_year_q_dtprofit
    )
    second_q_eps_yoy = (second_q_eps - second_last_year_q_eps) / abs(
        second_last_year_q_eps
    )

    third_q_sales_yoy = df.iloc[2]["q_sales_yoy"]
    third_q_dtprofit = df.iloc[2]["q_dtprofit"]
    third_q_eps = df.iloc[2]["q_eps"]

    third_q_dtprofit_date = df.iloc[2]["end_date"]
    third_yoy_date_obj = datetime.strptime(third_q_dtprofit_date, "%Y%m%d")
    third_yoy_date_obj = third_yoy_date_obj.replace(year=third_yoy_date_obj.year - 1)
    third_yoy_date = third_yoy_date_obj.strftime("%Y%m%d")

    third_last_year_row = df[df["end_date"] == third_yoy_date].iloc[0]
    third_last_year_q_dtprofit = third_last_year_row["q_dtprofit"]
    third_last_year_q_eps = third_last_year_row["q_eps"]
    third_q_dtprofit_yoy = (third_q_dtprofit - third_last_year_q_dtprofit) / abs(
        third_last_year_q_dtprofit
    )
    third_q_eps_yoy = (third_q_eps - third_last_year_q_eps) / abs(third_last_year_q_eps)

    # print(
    #     f"{name} 最近三季度营业收入同比增长率: {latest_q_sales_yoy}%, {second_q_sales_yoy:}%, {third_q_sales_yoy:}%"
    # )
    # print(
    #     f"{name} 最近三季度扣非净利润同比增长率: {q_dtprofit_yoy:.2%}, {second_q_dtprofit_yoy:.2%}, {third_q_dtprofit_yoy:.2%}"
    # )
    # print(
    #     f"{name} 最近三季度每股收益同比增长率: {q_eps_yoy:.2%}, {second_q_eps_yoy:.2%}, {third_q_eps_yoy:.2%}"
    # )

    yoy_criteria = (
        latest_q_sales_yoy > benchmark
        and second_q_sales_yoy > benchmark
        and third_q_sales_yoy > benchmark
        and q_dtprofit_yoy > benchmark
        and second_q_dtprofit_yoy > benchmark
        and third_q_dtprofit_yoy > benchmark
        and q_eps_yoy > benchmark
        and second_q_eps_yoy > benchmark
        and third_q_eps_yoy > benchmark
    )

    growth_criteria = (
        latest_q_sales_yoy > 0
        and second_q_sales_yoy > 0
        and third_q_sales_yoy > 0
        and latest_q_sales_yoy > second_q_sales_yoy > third_q_sales_yoy
        and latest_q_dtprofit > 0
        and second_q_dtprofit > 0
        and third_q_dtprofit > 0
        and latest_q_dtprofit > second_q_dtprofit > third_q_dtprofit
        and latest_q_eps > 0
        and second_q_eps > 0
        and third_q_eps > 0
        and latest_q_eps > second_q_eps > third_q_eps
    )

    is_health = False
    if yoy_criteria or growth_criteria:
        # print(f"最近三季度扣非净利润和EPS同比增长率均大于{benchmark:.2%}")
        is_health = True

    return is_health


# check_finance_yoy("002970.SZ")
# check_finance_yoy("002351.SZ")
