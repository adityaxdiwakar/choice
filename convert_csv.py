import progressbar
import shutil
import json
import gzip
import time
import os

count = 0
for root, dirs, files in os.walk("bin/"):
    count += len(files)

print(f"Have {count} files to convert")
bar = progressbar.ProgressBar(max_value=count * 2)

def add_obj_line(orig, data: str) -> str:
    orig += ","
    orig += str(data)
    return orig

def conv_str(str) -> float:
    try:
        return float(str)
    except:
        return 9999.99

c = 0
bin_dir = os.listdir("bin")
for ticker in bin_dir:
    for calendar in sorted(os.listdir(f"bin/{ticker}")):

        if calendar == "series.json":
            continue

        for strike in sorted(os.listdir(f"bin/{ticker}/{calendar}"), key=conv_str):
            if strike == "pairs.json":
                continue

            for direction in os.listdir(f"bin/{ticker}/{calendar}/{strike}"):
                if direction.endswith("csv"):
                    continue
                file_name = f"bin/{ticker}/{calendar}/{strike}/{direction}.csv"
                with open(file_name, "w") as f:
                    f.write("")

                opt_file = open(file_name, "a")

                for root, dirs, files in sorted(os.walk(f"bin/{ticker}/{calendar}/{strike}/{direction}")):

                    if files == []:
                        continue

                    for file in sorted(files):
                        (month, day, hour), minute = root.split("/")[-3:], file[:-5]

                        with open(f"bin/{ticker}/{calendar}/{strike}/{direction}/{month}/{day}/{hour}/{minute}.json", "r") as fin:
                            data = json.load(fin)

                        line = month
                        line = add_obj_line(line, day)
                        line = add_obj_line(line, hour)
                        line = add_obj_line(line, minute)
                        line = add_obj_line(line, data["symbol"])
                        line = add_obj_line(line, data["values"]["ASK"])
                        line = add_obj_line(line, data["values"]["BID"])
                        line = add_obj_line(line, data["values"]["DELTA"])
                        line = add_obj_line(line, data["values"]["GAMMA"])
                        line = add_obj_line(line, data["values"]["IMPLIED_VOLATILITY"])
                        line = add_obj_line(line, data["values"]["LAST"])
                        line = add_obj_line(line, data["values"]["OPEN_INT"])
                        line = add_obj_line(line, data["values"]["PROBABILITY_ITM"])
                        line = add_obj_line(line, data["values"]["RHO"])
                        line = add_obj_line(line, data["values"]["THETA"])
                        line = add_obj_line(line, data["values"]["VEGA"])
                        line = add_obj_line(line, data["values"]["VOLUME"])

                        opt_file.write(line + "\n")
                        c += 1
                        bar.update(c)

                file_name = f"bin/{ticker}/{calendar}/{strike}/{direction}/"
                shutil.rmtree(file_name)

                opt_file.close()

