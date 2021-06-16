from pathlib import Path
import urllib.parse
import progressbar
import requests
import time
import json

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

# open tickers.json file and extract tickers into list
with open("tickers.json", "r") as f:
    tickers = json.load(f)[:5]

tickers.append("SPY")
tickers.append("GLD")

logs_file = open("logs.txt", "a")

print(f"Initialized with {len(tickers)} to scan through, beginning now...")

def logger(message: str):
    logs_file.write(f"{time.strftime('%x %X', time.localtime())}: {message}\n")
    logs_file.flush()

    s 

def get_series(ticker: str) -> dict:
    # make the request to the series endpoint
    url = f"http://localhost:7731/series/{ticker}"
    req = requests.get(url)

    if req.status_code != 200:
        logger(f"Errored on retrieving series for {ticker} with code {req.status_code} (error: {req.json()['payload']})")
        time.sleep(0.5)
        return None

    logger(f"Retrieved series for {ticker}")
    return req.json()

bar = progressbar.ProgressBar(max_value=len(tickers))
series_valid = {}
count = 0

for i, ticker in enumerate(tickers):
    v = get_series(ticker)
    if v != None:
        series_valid[ticker] = v["payload"]
        count += len(v["payload"])
    else:
        continue

    Path(f"bin/{ticker}").mkdir(parents=True, exist_ok=True)
    with open(f"bin/{ticker}/series.json", "w") as f:
        json.dump(v["payload"], f, indent=2)

    bar.update(i)


def get_chain(ticker: str, series: str) -> dict:
    # make the request to the chain endpoint
    url = f"http://localhost:7731/chain/{ticker}"
    req = requests.get(url, headers={"Series-Name": series})

    if req.status_code != 200 or req.json()["payload"] == None:
        logger(f"Errored on retrieving chain data for {ticker} (series: {series}) with code {req.status_code} (error: {req.json()['payload']})")
        time.sleep(0.5)
        return None

    logger(f"Retrieved series for {ticker} (series: {series})")
    return req.json()

bar = progressbar.ProgressBar(max_value=count)
count = 0
s_count = 0
chains_valid = {}
for ticker in series_valid:
    v = series_valid[ticker]
    chains_valid[ticker] = {}
    for series in v:
        v = get_chain(ticker, series["name"])
        if v != None:
            chains_valid[ticker][series["name"]] = v["payload"][0]["optionPairs"]
            s_count += len(v["payload"][0]["optionPairs"])
        else:
            continue

        dir_series = series["name"].replace("/", "-")
        dir_series = dir_series.split(" ")
        dir_series = dir_series[2] + month_map[dir_series[1]] + dir_series[0].zfill(2)

        Path(f"bin/{ticker}/{dir_series}").mkdir(parents=True, exist_ok=True)
        with open(f"bin/{ticker}/{dir_series}/pairs.json", "w") as f:
            json.dump(v["payload"][0], f, indent=2)

        count += 1
        bar.update(count)

logger(f"Done, completed {count} chains to get {s_count} strikes meaning {s_count * 2} securities")
