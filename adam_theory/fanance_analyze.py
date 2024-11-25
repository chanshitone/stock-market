
# 导入tushare
import tushare as ts
# 初始化pro接口
pro = ts.pro_api('8b8ed979c3736e2485771cea39630f5e083921c78ae181f5f1ec34f5')

# 拉取数据
df = pro.income(**{
    "ts_code": "002468.SZ",
    "ann_date": "",
    "f_ann_date": "",
    "start_date": "",
    "end_date": "",
    "period": 20240930,
    "report_type": "",
    "comp_type": "",
    "is_calc": "",
    "limit": "",
    "offset": ""
}, fields=[
    "ts_code",
    "ann_date",
    "f_ann_date",
    "end_date",
    "total_revenue",
    "revenue",
    "net_after_nr_lp_correct",
    "basic_eps",
    "end_type"
])
print(df)

        