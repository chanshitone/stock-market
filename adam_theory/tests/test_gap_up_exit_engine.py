import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from gap_up_exit_engine import ExitConfig, Position, gap_up_decide_for_symbol


def test_same_day_entry_does_not_trigger_gap_down_stop():
    pos = Position(
        symbol="603083.SH",
        entry_date=pd.Timestamp("2026-04-21"),
        entry_price=159.85,
        stop_price=151.8575,
    )
    bars = pd.DataFrame(
        [
            {
                "symbol": "603083.SH",
                "date": pd.Timestamp("2026-04-21"),
                "open": 150.83,
                "high": 162.5,
                "low": 150.0,
                "close": 161.17,
                "volume": 1000,
                "ma13": 149.0,
            }
        ]
    )

    decision = gap_up_decide_for_symbol(
        bars,
        pos,
        asof=pd.Timestamp("2026-04-21"),
        cfg=ExitConfig(),
    )

    assert decision["action"] == "HOLD"
    assert decision["reason"] == "HOLD: no exit condition triggered"