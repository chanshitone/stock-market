import os
import sys
from pathlib import Path

import pytest
import tushare as ts

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import phase1_scanner


def test_fetch_pro_bar_real_api():
    token = os.getenv("TUSHARE_TOKEN")
    if not token:   
        ts.set_token("8b8ed979c3736e2485771cea39630f5e083921c78ae181f5f1ec34f5")

    df = phase1_scanner.fetch_pro_bar(
        "600897.SH",
        start_date="20260101",
        end_date="20260131",
    )

    print(df)

    assert df is not None
    assert not df.empty
    assert "ma_v_5" in df.columns
    assert (df["ts_code"] == "600897.SH").all()
