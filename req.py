from datetime import datetime
from pathlib import Path
import progressbar
import requests
import time
import json
import os

logs_file = open("logs.txt", "a")

def logger(message: str):
    logs_file.write(f"{time.strftime('%x %X', time.localtime())}: {message}\n")
    logs_file.flush()

def get_quote(ticker: str, series: list[str], min, max: int) -> dict:
    # make the request to the chart endpoint
    url = f"http://localhost:7731/quote/{ticker}/{min}/{max}"
    req = requests.get(url, headers={"Series-Name": ",".join(series)})

    if req.status_code != 200:
        logger(f"Errored on retrieving chain quote for {ticker} with code {req.status_code} (error: {req.json()['payload']})")
        return None

    logger(f"Retrieved chain quote for {ticker}")
    return req.json()

ticker_dir = os.listdir("bin/")
bar = progressbar.ProgressBar(max_value=len(ticker_dir))
for i, ticker in enumerate(ticker_dir):
    with open(f"bin/{ticker}/series.json", "r") as f:
        series = json.load(f)

    names = [d["name"] for d in series]

    v = get_quote(ticker, names, 0.01, 9999)
    for opt in v["payload"]:
        e_dir = opt["symbol"][1 + len(ticker): 7 + len(ticker)]
        strike = opt["symbol"][8 + len(ticker):]
        today = datetime.today()
        month = str(today.month).zfill(2)
        day = str(today.day).zfill(2)
        hour = str(today.hour).zfill(2)
        minute = str(today.minute).zfill(2)

        path = f"bin/{ticker}/{e_dir}/{strike}/{opt['symbol']}/{month}/{day}/{hour}"
        Path(path).mkdir(parents=True, exist_ok=True)
        with open(f"{path}/{minute}.json", "w") as f:
            json.dump(opt, f)

        logger(f"Inserted {path}")

    bar.update(i+1)

    time.sleep(2)
