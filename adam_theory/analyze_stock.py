import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from adam_theory.utils import draw_center_symmetry, normalize_ts_code

ts_code = input("输入股票代码：")
norm = normalize_ts_code(ts_code)
if not norm:
	raise ValueError(f"Invalid stock code: {ts_code}")

stock = ts_code
draw_center_symmetry(norm, stock)
