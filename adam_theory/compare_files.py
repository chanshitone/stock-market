# compare stock_holdings.txt and stock_holdings1.txt under ./input and print the differences

import os
import difflib


def compare_files(file1, file2):
    with open(file1, "r") as f1:
        lines1 = f1.readlines()
    with open(file2, "r") as f2:
        lines2 = f2.readlines()
    
    # compare the two files and print the lines not in file2
    d = difflib.Differ()
    diff = d.compare(lines1, lines2)
    print("".join(diff))


if __name__ == "__main__":
    current_dir = os.path.dirname(__file__)
    compare_files(
        os.path.join(current_dir, "input", "stock_holdings.txt"),
        os.path.join(current_dir, "input", "stock_holdings1.txt"),
    )
