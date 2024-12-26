import os
import pandas as pd
import sys

# 导入tushare
import pandas as pd

# Add the parent directory of adam_theory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from adam_theory.fanance_analyze import check_finance_yoy

# print current time
start_time = pd.Timestamp.now()
print(f"Current time: {start_time}")
# read the stock list from ./input/stock_holdings.txt
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "input", "stock_holdings.txt")
with open(file_path, "r") as f:
    stock_list = f.readlines()
    # remove the newline character
    stock_list = [stock.strip() for stock in stock_list]
    # remove duplicate stocks
    stock_list = list(set(stock_list))

# read ./input/all_company.xlsx
file_path = os.path.join(current_dir, "input", "all_company.xlsx")
with pd.ExcelFile(file_path) as xls:
    all_company_df = pd.read_excel(xls)

health_stocks = []
for stock in stock_list:
    ts_code = all_company_df[all_company_df["name"] == stock]["ts_code"].values
    if len(ts_code) == 0:
        print(f"Warning: Stock '{stock}' not found in all_company_df")
        continue
    ts_code = ts_code[0]
    try:
        is_health = check_finance_yoy(ts_code, stock)
        if is_health:
            print(f"{stock}")
            health_stocks.append(stock)
    except Exception as e:
        print(f"Error processing stock '{stock}' when checking financial indicator: {e}")
        continue

# write the health stocks to ./output/health_stocks.txt
output_file = os.path.join(current_dir, "output", "health_stocks.txt")
with open(output_file, "w") as f:
    for stock in health_stocks:
        f.write(stock + "\n")

# print current time
end_time = pd.Timestamp.now()
print(f"Current time: {end_time}")
print(f"Time elapsed: {end_time - start_time}")