from extract_stocks import extract_stocks
from fanance_analyze import check_finance_yoy
import pandas as pd
import os
from utils import draw_center_symmetry


start_time = pd.Timestamp.now().strftime("%Y%m%d %H:%M:%S")
print(f"Daily report started at {start_time}")

today = pd.Timestamp.now().strftime("%Y%m%d")
# Extract stocks from gap up picture
daily_stocks = extract_stocks("input/picture", f"daily_stocks_{today}.txt")

# Analyze stocks
# read ./input/all_company.xlsx
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "input", "all_company.xlsx")
with pd.ExcelFile(file_path) as xls:
    all_company_df = pd.read_excel(xls)

health_stocks = []
not_found_stocks = []
for stock in daily_stocks:
    ts_code = all_company_df[all_company_df["name"] == stock]["ts_code"].values
    if len(ts_code) == 0:
        print(f"Warning: Stock '{stock}' not found in all_company_df")
        not_found_stocks.append(stock)
        continue
    ts_code = ts_code[0]
    try:
        is_health = check_finance_yoy(ts_code, stock)
        if is_health:
            print(f"{stock}")
            health_stocks.append(stock)
            draw_center_symmetry(ts_code, stock)
    except Exception as e:
        print(f"Error processing stock '{stock}' when checking financial indicator: {e}")
        continue

# write the health stocks to ./output/health_stocks.txt
if len(health_stocks) > 0:
    output_file = os.path.join(current_dir, "output", f"health_stocks_{today}.txt")
    with open(output_file, "w") as f:
        for health_stock in health_stocks:
            f.write(health_stock + "\n")
    

# write the not found stocks to ./output/not_found_stocks.txt
if len(not_found_stocks) > 0:
    output_file = os.path.join(current_dir, "output", f"not_found_stocks_{today}.txt")
    with open(output_file, "w") as f:
        for not_found_stock in not_found_stocks:
            f.write(not_found_stock + "\n")

end_time = pd.Timestamp.now().strftime("%Y%m%d %H:%M:%S")
print(f"Daily report finished at {end_time}")
print("time elapsed: ", pd.Timestamp(end_time) - pd.Timestamp(start_time))
