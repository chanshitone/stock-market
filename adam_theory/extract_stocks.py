import os
import re

import easyocr


def extract_stocks(picture_path, output_file_name):
    """Extract digit strings from images under `picture_path`.

    Returns a de-duplicated, sorted list of numbers (as strings). If any 6-digit
    sequences are found, only those are kept (typical A-share stock codes).
    """

    reader = easyocr.Reader(["ch_sim", "en"])
    current_dir = os.path.dirname(__file__)

    output_file = os.path.join(current_dir, "output", output_file_name)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    # truncate output file
    open(output_file, "w", encoding="utf-8").close()

    image_dir = os.path.join(current_dir, picture_path)
    numbers: list[str] = []
    for image_name in os.listdir(image_dir):
        if not image_name.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        full_image_path = os.path.join(image_dir, image_name)
        result = reader.readtext(full_image_path)
        for _, text, _ in result:
            if not text:
                continue
            # collect all digit sequences from the token, e.g. "000001.SZ" -> ["000001"]
            numbers.extend(re.findall(r"\d+", str(text)))

    # Prefer 6-digit codes if present; otherwise keep whatever digits we found.
    six_digit = [n for n in numbers if len(n) == 6]
    picked = six_digit if six_digit else numbers
    picked = sorted(set(picked))

    with open(output_file, "a", encoding="utf-8") as f:
        for n in picked:
            f.write(n + "\n")

    return picked
