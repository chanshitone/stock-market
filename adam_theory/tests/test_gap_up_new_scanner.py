import sys
from pathlib import Path

import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from gap_up_new_scanner import add_excel_formulas


def test_add_excel_formulas_populates_threshold_and_flags():
    output_df = pd.DataFrame(
        [
            {
                "stock": "603083",
                "075_v": 75.0,
                "b_price": 167.85,
                "v_ful": "",
                "p_ful": "",
                "can_b": "",
                "status": "",
                "reason": "",
                "close": 159.85,
                "gap": 10.0,
                "volumn": 100.0,
            }
        ]
    )

    result = add_excel_formulas(output_df)

    assert result.columns.tolist() == [
        "stock",
        "075_v",
        "b_price",
        "v_ful",
        "p_ful",
        "can_b",
        "status",
        "reason",
        "close",
        "gap",
        "volumn",
    ]
    assert result.at[0, "075_v"] == pytest.approx(75.0)
    assert result.at[0, "b_price"] == pytest.approx(167.85)
    assert result.at[0, "v_ful"] == ""
    assert result.at[0, "p_ful"] == ""
    assert result.at[0, "can_b"] == "=AND(D2=1,E2=1)"