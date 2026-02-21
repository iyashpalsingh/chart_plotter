#parser_txt.py

import os
from config import TEMP_CSV

cancel_flag = False

def parse_txt_line(line):
    parts = line.strip().split()
    if len(parts) < 3:
        return None

    row = {"Timestamp": parts[0] + " " + parts[1]}

    for p in parts[2:]:
        if "=" in p:
            k, v = p.split("=", 1)
            try:
                row[k] = float(v)
            except:
                row[k] = v
    return row


def stream_txt_to_csv(path, progress_callback=None):
    total = os.path.getsize(path)
    read = 0
    header_written = False

    with open(path, "rb") as fin, open(TEMP_CSV, "w", encoding="utf-8") as fout:

        for raw in fin:
            read += len(raw)

            line = raw.decode("utf-8", "ignore")
            row = parse_txt_line(line)

            if not row:
                continue

            if not header_written:
                fout.write(",".join(row.keys()) + "\n")
                header_written = True

            fout.write(",".join(str(v) for v in row.values()) + "\n")

            if progress_callback:
                progress_callback(read, total)

    return True