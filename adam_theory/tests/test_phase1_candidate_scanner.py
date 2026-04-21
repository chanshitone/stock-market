import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import phase1_candidate_scanner


def build_bars(latest_close: float = 11.2) -> pd.DataFrame:
    latest_date = datetime.strptime("20250410", "%Y%m%d")
    rows = [
        {
            "trade_date": "20250410",
            "ma_v_5": 100.0,
            "vol": 220.0,
            "close": latest_close,
            "low": 10.0,
            "high": 11.5,
        }
    ]
    for index in range(1, 14):
        trade_date = (latest_date - timedelta(days=index)).strftime("%Y%m%d")
        rows.append(
            {
                "trade_date": trade_date,
                "ma_v_5": 95.0,
                "vol": 90.0,
                "close": 9.5 + index * 0.05,
                "low": 9.0,
                "high": 10.8,
            }
        )
    return pd.DataFrame(rows)


def test_evaluate_phase1_rule_returns_metrics_for_matching_setup():
    result = phase1_candidate_scanner.evaluate_phase1_rule(build_bars())

    assert result is not None
    assert result["trade_date"] == "20250410"
    assert result["ratio"] == pytest.approx(2.2)
    assert result["close_strength"] == pytest.approx(0.8)
    assert result["highest_high_13"] == pytest.approx(10.8)


def test_evaluate_phase1_rule_rejects_close_below_prior_high():
    result = phase1_candidate_scanner.evaluate_phase1_rule(build_bars(latest_close=10.7))

    assert result is None