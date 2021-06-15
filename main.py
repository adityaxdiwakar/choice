from pathlib import Path
import progressbar
import requests
import time
import json

# open tickers.json file and extract tickers into list
with open("tickers.json", "r") as f:
    tickers = json.load(f)

logs_file = open("logs.txt", "a")

print(f"Initialized with {len(tickers)} to scan through, beginning now...")

def logger(message: str):
    logs_file.write(f"{time.strftime('%x %X', time.localtime())}: {message}\n")
    logs_file.flush()


def get_series(ticker: str) -> dict:
    # make the request to the series endpoint
    url = f"http://localhost:7731/series/{ticker}"
    req = requests.get(url)

    if req.status_code != 200:
        print(f"Error: Series for {ticker} resulted in {req.status_code} response (see logs)")
        logger("Errored on retrieving series for {ticker} with code {req.status_code} (error: {req.json()['payload'])}")
        time.sleep(0.5)
        return None

    logger(f"Retrieved series for {ticker} successfully!")
    return req.json()

bar = progressbar.ProgressBar(max_value=len(tickers))
series_valid = {}

for i, ticker in enumerate(tickers):
    v = get_series(ticker)
    if v != None:
        series_valid[ticker] = v["payload"]
    else:
        continue

    Path(f"bin/{ticker}").mkdir(parents=True, exist_ok=True)
    with open(f"bin/{ticker}/series.json", "w") as f:
        json.dump(v, f)

    bar.update(i)

    time.sleep(0.01)



print(len(series_valid))
