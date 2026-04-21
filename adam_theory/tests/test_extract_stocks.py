import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import extract_stocks as extract_stocks_module
from extract_stocks_new import extract_stocks as extract_stocks_new


def test_extract_stocks_skips_empty_folder_without_output(tmp_path, monkeypatch):
    base_dir = tmp_path / "adam_theory"
    picture_dir = base_dir / "input" / "picture" / "breakthrough" / "gap_up"
    picture_dir.mkdir(parents=True)

    original_file = extract_stocks_module.__file__
    monkeypatch.setattr(extract_stocks_module, "__file__", str(base_dir / "extract_stocks.py"))

    class FakeReader:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("EasyOCR should not be initialized for an empty folder")

    monkeypatch.setattr(extract_stocks_module.easyocr, "Reader", FakeReader)

    stocks = extract_stocks_module.extract_stocks(
        "input/picture/breakthrough/gap_up",
        "should_not_exist.txt",
    )

    assert stocks == []
    assert not (base_dir / "output" / "should_not_exist.txt").exists()

    monkeypatch.setattr(extract_stocks_module, "__file__", original_file)


def test_extract_stocks_brk(tmp_path):
    pytest.importorskip("easyocr")

    base_dir = Path(__file__).resolve().parent.parent
    img_dir = base_dir / "input" / "picture" / "breakthrough" / "brk"
    if not img_dir.exists() or not any(img_dir.iterdir()):
        pytest.skip("No breakthrough images available for test.")

    output_name = "test_brk_output.txt"
    output_path = base_dir / "output" / output_name
    if output_path.exists():
        output_path.unlink()

    stocks = extract_stocks_new("input/picture/breakthrough/brk", output_name)

    assert output_path.exists()
    lines = [line.strip() for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert set(lines) == set(stocks)
    assert stocks == sorted(set(stocks))

    if not stocks:
        pytest.xfail("OCR produced no symbols; check OCR models and sample images.")

    try:
        output_path.unlink()
    except FileNotFoundError:
        pass
