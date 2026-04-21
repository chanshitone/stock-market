import os
import sys
from pathlib import Path
from unittest.mock import call

import pytest
import tushare as ts
import pandas as pd

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


def test_process_source_skips_when_no_pictures(monkeypatch, capsys):
    source = {
        "label": "brk",
        "picture_path": "input/picture/breakthrough/brk",
        "stock_output_prefix": "brk_stocks",
        "csv_output_prefix": "new_scanner_with_brk",
    }

    monkeypatch.setattr(phase1_scanner, "has_picture_inputs", lambda _: False)

    result = phase1_scanner.process_source(
        source,
        "2026-04-16_101010",
        "20260215",
        "20260416",
    )

    captured = capsys.readouterr()
    assert result is None
    assert "Skip brk: no pictures found" in captured.out


def test_main_processes_brk_and_gapsup_sources(monkeypatch):
    configure_calls = []
    process_calls = []

    monkeypatch.setattr(phase1_scanner, "configure_tushare", lambda _: configure_calls.append(True))
    monkeypatch.setattr(
        phase1_scanner.pd.Timestamp,
        "now",
        classmethod(lambda cls: pd.Timestamp("2026-04-16 10:10:10")),
    )

    def fake_process_source(source, timestamp, start_date, end_date):
        process_calls.append((source["label"], timestamp, start_date, end_date))
        return None

    monkeypatch.setattr(phase1_scanner, "process_source", fake_process_source)

    phase1_scanner.main()

    assert configure_calls == [True]
    assert process_calls == [
        ("brk", "2026-04-16_101010", "20260215", "20260416"),
        ("gapsup", "2026-04-16_101010", "20260215", "20260416"),
    ]
