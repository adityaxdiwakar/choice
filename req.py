from datetime import datetime
from pathlib import Path
import progressbar
import subprocess
import jsonpatch
import requests
import signal
import time
import json
import os

month_map = {
    "JAN": "01",
    "FEB": "02",
    "MAR": "03",
    "APR": "04",
    "MAY": "05",
    "JUN": "06",
    "JUL": "07",
    "AUG": "08",
    "SEP": "09",
    "OCT": "10",
    "NOV": "11",
    "DEC": "12"
}

logs_file = open("logs.txt", "a")

def logger(message: str):
    logs_file.write(f"{time.strftime('%x %X', time.localtime())}: {message}\n")
    logs_file.flush()

def get_quote(ticker: str, series: list[str], min, max: int) -> dict:
    print(f"getting {ticker}")
    if not requests.get("http://localhost:7731/status").json()["payload"]:
        while True:
            time.sleep(0.5)
            if not requests.get("http://localhost:7731/status").json()["payload"]:
                continue
            else:
                break


    # make the request to the chart endpoint
    url = f"http://localhost:7731/quote/{ticker}/{min}/{max}"
    req = requests.get(url, headers={"Series-Name": ",".join(series)})

    if req.status_code != 200 or req.json()["payload"] == None or req.json()["payload"] == "OK.":
        logger(f"Errored on retrieving chain quote for {ticker} with code {req.status_code} (error: {req.json()['payload']})")
        return None

    logger(f"Retrieved chain quote for {ticker}")
    return req.json()

def add_obj_line(orig, data: str) -> str:
    orig += ","
    orig += str(data)
    return orig


def subscribe():
    print("Beginning subscriptions:")
    # subscribe first
    ticker_dir = os.listdir("bin/")
    for ticker in ticker_dir:
            if ticker != "SPY":
                continue
                #pass

            # open the file for that ticker to get the series
            with open(f"bin/{ticker}/series.json", "r") as f:
                series = json.load(f)


            names = [d["name"] for d in series]
            non_expired_names = []

            for name in names:
                name_spl = name.split(" ")
                day = int(name_spl[0])
                month = int(month_map[name_spl[1]])
                year = int(name_spl[2])

                today = datetime.today()
                int_date = year * 10000 + month * 100 + day
                int_today = (today.year % 100) * 10000 + today.month * 100 + today.day
                if int_today > int_date:
                    continue

                non_expired_names.append(name)

            v = get_quote( ticker, names, 0.01, 9999)
            print(f"| ->\tSubscribed to {ticker}")

# subscribe()

def write_to_csv(symbol: dict):
    ticker = symbol["symbol"]
    if "C" in ticker[-6:]:
        ticker = ticker[1:ticker.rfind("C") - 6]
    elif "P" in ticker[-6:]:
        ticker = ticker[1:ticker.rfind("P") - 6]

    orig_ticker = symbol["symbol"][1:]
    write_mode = "a"
    if not os.path.exists(f"bin/{ticker}/{orig_ticker}.csv"):
        write_mode = "w"

    for it in ['ASK', 'BID', 'DELTA', 'GAMMA', 'IMPLIED_VOLATILITY', 'LAST', 'MARK', 'MARK_CHANGE',
               'OPEN_INT', 'PROBABILITY_ITM', 'RHO', 'THETA', 'VEGA', 'VOLUME']:
        if it not in symbol["values"]:
            symbol["values"][it] = 0

    print(f"{'Writing to' : <20} {orig_ticker : >5}")
    line = str(round(time.time() * 1000))
    line = add_obj_line(line, symbol["symbol"])
    line = add_obj_line(line, symbol["values"]["BID"])
    line = add_obj_line(line, symbol["values"]["MARK"])
    line = add_obj_line(line, symbol["values"]["MARK_CHANGE"])
    line = add_obj_line(line, symbol["values"]["ASK"])
    line = add_obj_line(line, symbol["values"]["LAST"])
    line = add_obj_line(line, symbol["values"]["VOLUME"])
    line = add_obj_line(line, symbol["values"]["OPEN_INT"])
    line = add_obj_line(line, symbol["values"]["IMPLIED_VOLATILITY"])
    line = add_obj_line(line, symbol["values"]["PROBABILITY_ITM"])
    line = add_obj_line(line, symbol["values"]["DELTA"])
    line = add_obj_line(line, symbol["values"]["GAMMA"])
    line = add_obj_line(line, symbol["values"]["RHO"])
    line = add_obj_line(line, symbol["values"]["THETA"])

    line = add_obj_line(line, symbol["values"]["VEGA"])
    with open(f"bin/{ticker}/{orig_ticker}.csv", write_mode) as f:
        f.write(line + "\n")

with open("bin/dump.csv", "r") as f:
    dump = f.readlines()

print(len(dump))
first_line = dump[0]
repeat = None
for i, line in enumerate(dump[1:]):
    if line == first_line:
        repeat = i
        break

dump = dump[:repeat]
symbol_map = {}
count = 0
while True:
    #v = requests.get("http://localhost:7731/quotes")
    #payload = v.json()["payload"]
    if count == len(dump):
        break
    payload = [dump[count]]
    count += 1
    if payload == []:
        time.sleep(0.1)
        continue

    # this could have multiple patches but save after every iteration of this loop
    for meta_patch in payload:
        meta_patch_j = json.loads(meta_patch)
        for meta_patch_spl in meta_patch_j:
            header_id = meta_patch_spl["header"]["id"]

            if not header_id.startswith("OPTIONCHAINGET"):
                continue

            patch_by_idx = {}
            for patch in meta_patch_spl["body"]["patches"]:
                path = patch["path"]
                if path == "":
                    path = "!"
                else:
                    path = path[7:]
                    path = path[:path.find("/")]
                    patch["path"] = patch["path"][7 + len(path):]
                    path = int(path)

                if path not in patch_by_idx:
                    patch_by_idx[path] = []
                patch_by_idx[path].append(patch)

            if "!" in patch_by_idx:
                if header_id not in symbol_map:
                    symbol_map[header_id] = {}
                symbol_map[header_id] = jsonpatch.apply_patch(symbol_map[header_id], patch_by_idx["!"])

                for key in symbol_map:
                    for symbol in symbol_map[key]["items"]:
                        write_to_csv(symbol)

            for idx in patch_by_idx:
                if idx == "!":
                    continue

                try:
                    symbol_map[header_id]["items"][idx] = jsonpatch.apply_patch(symbol_map[header_id]["items"][idx],
                                                                                patch_by_idx[idx])

                    write_to_csv(symbol_map[header_id]["items"][idx])
                except Exception as e:
                    print(idx)
                    print(patch_by_idx[idx])
                    print(symbol_map[header_id]["items"][idx])
                    print(e)
                    time.sleep(1)
