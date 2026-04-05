import tushare as ts
import pandas as pd
import os
from env_config import get_tushare_pro

pro = get_tushare_pro(ts)

data = pro.query(
    "stock_basic",
    exchange="",
    list_status="L",
    fields="ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type",
)

# print the first 5 rows of the data
print(data.head())

# update the stock list monthly
current_dir = os.path.dirname(__file__)
output_file = os.path.join(current_dir, "input", "all_company.xlsx")
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    data.to_excel(writer, index=False)



