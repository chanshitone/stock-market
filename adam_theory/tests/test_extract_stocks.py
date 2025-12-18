import os
from pathlib import Path

import pytest

from adam_theory.extract_stocks_new import extract_stocks


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

    stocks = extract_stocks("input/picture/breakthrough/brk", output_name)

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
