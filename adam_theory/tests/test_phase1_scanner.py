import os
import sys
from pathlib import Path

import pytest
import tushare as ts

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from env_config import get_tushare_token
import phase1_scanner


def test_fetch_pro_bar_real_api():
    token = get_tushare_token(required=False)
    if not token:
        pytest.skip("TUSHARE_TOKEN is not configured")

    ts.set_token(token)

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
