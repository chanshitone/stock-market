import os
import pandas as pd
import sys

# 导入tushare
import pandas as pd

# Add the parent directory of adam_theory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from adam_theory.utils import draw_center_symmetry

# read the stock list from ./input/stock_holdings.txt
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "input", "stock_holdings.txt")
with open(file_path, "r") as f:
    stock_list = f.readlines()
    # remove the newline character
    stock_list = [stock.strip() for stock in stock_list]

# read ./input/all_company.xlsx
file_path = os.path.join(current_dir, "input", "all_company.xlsx")
with pd.ExcelFile(file_path) as xls:
    all_company_df = pd.read_excel(xls)

for stock in stock_list:
    ts_code = all_company_df[all_company_df["name"] == stock]["ts_code"].values
    ts_code = ts_code[0]
    draw_center_symmetry(ts_code, stock)
