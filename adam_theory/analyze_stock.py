import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from adam_theory.utils import draw_center_symmetry

ts_code = input("输入股票代码：")
stock = ts_code
draw_center_symmetry(ts_code, stock)
