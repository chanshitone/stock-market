import difflib
import os
from typing import Iterable, List, Optional, Tuple

import easyocr
import pandas as pd

# PaddleOCR is optional (script must run without it)
try:
    from paddleocr import PaddleOCR  # type: ignore
except Exception:
    PaddleOCR = None

# Optional, used for preprocessing (EasyOCR already depends on these in most envs)
import numpy as np
from PIL import Image, ImageEnhance, ImageOps


def _load_company_names(base_dir: str) -> List[str]:
    excel_path = os.path.join(base_dir, "input", "all_company.xlsx")
    if not os.path.exists(excel_path):
        return []
    with pd.ExcelFile(excel_path) as xls:
        df = pd.read_excel(xls)
    name_col = "name" if "name" in df.columns else df.columns[0]
    return df[name_col].dropna().astype(str).str.strip().tolist()


def _best_match(token: str, vocab: List[str], cutoff: float = 0.75) -> Optional[str]:
    if not vocab:
        return None
    match = difflib.get_close_matches(token, vocab, n=1, cutoff=cutoff)
    return match[0] if match else None


def _preprocess_for_ocr(image_path: str) -> np.ndarray:
    """
    Lightweight preprocessing to improve EasyOCR on screenshots:
    - grayscale
    - autocontrast
    - upscale
    - mild sharpening/contrast
    """
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)
    img = img.convert("L")  # grayscale
    img = ImageOps.autocontrast(img)

    # upscale (helps small fonts)
    w, h = img.size
    img = img.resize((int(w * 2.0), int(h * 2.0)), Image.Resampling.LANCZOS)

    # contrast/sharpness
    img = ImageEnhance.Contrast(img).enhance(1.6)
    img = ImageEnhance.Sharpness(img).enhance(1.3)

    return np.array(img)


def _run_easyocr(reader: easyocr.Reader, image_path: str) -> Iterable[Tuple[str, float]]:
    img_arr = _preprocess_for_ocr(image_path)
    # decoder='beamsearch' can improve accuracy a bit (slower)
    for _, text, prob in reader.readtext(img_arr, decoder="beamsearch"):
        yield text, float(prob)


def _run_paddleocr(paddle_reader, image_path: str) -> Iterable[Tuple[str, float]]:
    result = paddle_reader.ocr(image_path, cls=True)
    if not result:
        return []
    for line in result[0]:
        text = line[1][0]
        prob = float(line[1][1])
        yield text, prob


def _build_readers() -> Tuple[Optional[object], easyocr.Reader]:
    paddle_reader = None
    if PaddleOCR is not None:
        try:
            paddle_reader = PaddleOCR(use_angle_cls=True, lang="ch")
        except Exception:
            paddle_reader = None

    easy_reader = easyocr.Reader(["ch_sim", "en"])
    return paddle_reader, easy_reader


def _iter_ocr_texts(
    paddle_reader: Optional[object], easy_reader: easyocr.Reader, image_path: str
) -> Iterable[Tuple[str, float]]:
    if paddle_reader:
        yield from _run_paddleocr(paddle_reader, image_path)
    yield from _run_easyocr(easy_reader, image_path)


def extract_stocks(picture_path: str, output_file_name: str) -> List[str]:
    current_dir = os.path.dirname(__file__)
    output_file = os.path.join(current_dir, "output", output_file_name)
    vocab = _load_company_names(current_dir)
    paddle_reader, easy_reader = _build_readers()

    stocks: List[str] = []
    with open(output_file, "w", encoding="utf-8"):
        pass

    for image_path in os.listdir(os.path.join(current_dir, picture_path)):
        if not image_path.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        full_path = os.path.join(current_dir, picture_path, image_path)
        for raw_text, prob in _iter_ocr_texts(paddle_reader, easy_reader, full_path):
            text = raw_text.strip().replace(" ", "")
            if not text or text.isascii() or text.isnumeric():
                continue
            if prob < 0.35:
                continue

            matched = _best_match(text, vocab)
            resolved = matched or text

            with open(output_file, "a", encoding="utf-8") as f:
                f.write(resolved + "\n")
            stocks.append(resolved)

            if not matched:
                print(f"Unmatched token (kept): {text}")

    return sorted(set(stocks))