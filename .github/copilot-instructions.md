## Scope
- Scripts live under [adam_theory](adam_theory) and target daily A-share momentum screening; assume agents orchestrate standalone Python entrypoints rather than a long-running service.
- Most jobs depend on OCR outputs from EasyOCR plus Tushare fundamentals; expect batch style workflows that mutate files inside input and output folders.

## Data Sources
- Stock metadata comes from [adam_theory/input/all_company.xlsx](adam_theory/input/all_company.xlsx), refreshed via [adam_theory/get_stock_list.py](adam_theory/get_stock_list.py) which writes the Excel with Tushare stock_basic.
- Gap-up watchlists are images stored in [adam_theory/input/picture](adam_theory/input/picture); [adam_theory/extract_stocks.py](adam_theory/extract_stocks.py) OCRs them into name lists while deduping and storing to timestamped text files.
- Financial ratios and price history are fetched via Tushare pro_api or pro_bar; every script expects a valid token (currently hardcoded) and obeys rate limits manually.

## Key Workflows
- [adam_theory/daily_report.py](adam_theory/daily_report.py) runs end-to-end: OCR pictures, filter healthy stocks using [adam_theory/fanance_analyze.py](adam_theory/fanance_analyze.py), draw symmetry charts via [adam_theory/utils.py](adam_theory/utils.py), and persist health and missing lists.
- [adam_theory/new_scanner.py](adam_theory/new_scanner.py) focuses on breakout confirmation: scans breakthrough images, hits pro_bar with ma_v_5, filters on volume ratio plus intraday strength, and exports CSV.
- [adam_theory/sel_strenthen_line.py](adam_theory/sel_strenthen_line.py) checks repeated closes above the 13-day moving average with volume diagnostics for gap-up follow-through.
- [adam_theory/select_bullish_alignment.py](adam_theory/select_bullish_alignment.py) reviews saved watchlists to confirm multi-MA bullish alignment for medium-term setups.
- [adam_theory/center_symmetry.py](adam_theory/center_symmetry.py) and [adam_theory/analyze_stock.py](adam_theory/analyze_stock.py) wrap draw_center_symmetry for batch or interactive chart production.

## Shared Patterns
- Always map human-readable names to ts_code via the all_company dataframe before calling Tushare; missing names should warn and skip rather than halt.
- Use pandas ExcelFile context managers for the shared workbook to avoid locking file handles.
- Respect Tushare throttles by counting calls and sleeping once thresholds (49 or 199 per minute depending on endpoint) are reached.
- All scanners normalise volume through moving-average columns returned by pro_bar (ma_v_5, ma_v_13); compute ratios then sort descending before persistence.

## Environment
- EasyOCR downloads detection models on first use; ensure torch and torchvision are installed and GPU availability is handled externally.
- Matplotlib plots in draw_center_symmetry rely on SimHei fonts for Chinese text and save to the OneDrive path under Desktop; adjust fonts or output dirs via that helper to change behaviour globally.
- Dependencies include tushare, pandas, mplfinance, matplotlib, easyocr, openpyxl; align any new scripts with these libraries to keep environments consistent.

## Output and Storage
- OCR outputs land in [adam_theory/output](adam_theory/output) with filenames embedded with run timestamps or dates; downstream scripts expect these archives for historical review.
- Charts from draw_center_symmetry save to C:\Users\chans\OneDrive\Desktop\中心对称图\{trade_date}; update utils if portability is required when running on other machines.
- CSV exports sort by strongest volume ratios to simplify manual inspection; prefer appending columns rather than reshaping the existing CSV format.

## Productivity Tips
- When adding scanners, factor shared logic (Tushare fetch, name resolution, throttling) into helpers in utils to reduce duplication.
- Prefer running scripts from inside the adam_theory directory so sys.path manipulations still resolve sibling modules.
- Keep token management centralised; consider reading from environment variables to avoid committing secrets in future iterations.
- Before large batch runs, refresh all_company.xlsx to capture new listings and retirements.
- Validate EasyOCR text output against sample images to confirm formatting before feeding into Tushare-driven loops.
