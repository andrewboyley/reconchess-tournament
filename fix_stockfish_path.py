import glob
import os
import argparse
import re

parser = argparse.ArgumentParser(description="Fix stockfish path")
parser.add_argument(
    "path",
    default="/home/andrew/Documents/reconchess/COMS4033A-AI4-S2-2023-Improved Agent Submission-22228",
    type=str,
    help="Path to the submissions folder",
)
parser.add_argument(
    "--stockfish-path",
    default="/home/andrew/Documents/reconchess/stockfish",
    type=str,
    help="Path to the stockfish binary",
)
args = parser.parse_args()

stockfish_path = args.stockfish_path

# Get all directories (i.e. student submissions) in the submission directory
# student_submission_dirs = glob.glob(os.path.join(args.path, '*'))

change_count = 0
files = glob.glob(os.path.join(args.path, "**/*.py"),recursive=True)
print(f"Found {len(files)} files")
for filename in files:
    # Get the submission file name that ends in .py
    # filename = glob.glob(os.path.join(student_submission_dir, '*.py'))
    # If not an empty list, get the first value, else None
    # filename = filename[0] if len(filename) > 0 else None

    if filename is not None:
        with open(filename, "r") as f:
            lines = f.readlines()
        # print(filename)
        for i, line in enumerate(lines):
            # Replace chess.engine.SimpleEngine.popen_uci("*", setpgrp=True) with args.stockfish_path using a regex
            newline = re.sub(r'popen_uci\(.*\)', f'popen_uci("{stockfish_path}", setpgrp=True)', line)

            # Replace /opt/stockfish/stockfish with args.stockfish_path
            newline = re.sub(r"'.*\/opt\/stockfish\/stockfish'", f"'{stockfish_path}'", newline)
            newline = re.sub(r'".*\/opt\/stockfish\/stockfish"', f"'{stockfish_path}'", newline)

            # Replace stockfish_path='*' with stockfish_path=args.stockfish_path
            newline = re.sub(r'stockfish_path.*=.*', f'stockfish_path="{stockfish_path}"', newline)
            newline = re.sub(r'STOCKFISH_PATH.*=.*', f'STOCKFISH_PATH="{stockfish_path}"', newline)

            # print the change
            if newline != line:
                change_count += 1

            lines[i] = newline

        with open(filename, "w") as f:
            f.writelines(lines)

print(f"Changed {change_count} lines")
