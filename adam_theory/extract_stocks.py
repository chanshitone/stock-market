import easyocr
import os

# 初始化EasyOCR reader，指定支持的语言，例如中文('chinese')和英文('en')
reader = easyocr.Reader(["ch_sim", "en"])

# 读取并识别图片
current_dir = os.path.dirname(__file__)
# loop all the png sufix files under ./input
# clean the text in ./input/stock_holdings.txt
with open(os.path.join(current_dir, "input", "stock_holdings.txt"), "w") as f:
    pass
for image_path in os.listdir(os.path.join(current_dir, "input")):
    if image_path.endswith(".png"):
        result = reader.readtext(os.path.join(current_dir, "input", image_path))
        # 提取和记录识别结果
        with open(os.path.join(current_dir, "input", "stock_holdings.txt"), "a") as f:
            for bbox, text, prob in result:
                # print(f"Text: {text}, Probability: {prob}")
                # 只打印中文文本
                if (
                    text.isascii()
                    or text.isnumeric()
                    or text.startswith("融")
                    or text.startswith("创")
                ):
                    continue
                print(f"{text}")
                # write the text to ./input/stock_holdings.txt with append mode
                f.write(text + "\n")
