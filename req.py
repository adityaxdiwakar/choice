import progressbar
import requests
import time
import json
import os

logs_file = open("logs.txt", "a")

def logger(message: str):
    logs_file.write(f"{time.strftime('%x %X', time.localtime())}: {message}\n")
    logs_file.flush()

def get_chart(ticker: str) -> dict:
    # make the request to the chart endpoint
    url = f"http://localhost:7731/series/{ticker}"
    req = requests.get(url)

    if req.status_code != 200:
        logger(f"Errored on retrieving charts for {ticker} with code {req.status_code} (error: {req.json()['payload']})")
        return None

    logger(f"Retrieved series for {ticker}")
    return req.json()

bar = progressbar.ProgressBar(max_value=11354)
c = 0
for ticker in os.listdir("bin/"):
    with open(f"bin/{ticker}/series.json", "r") as f:
        series = json.load(f)
    for s in series:
        s["name"] = s["name"].replace("/", "-")
        for strike in os.listdir(f"bin/{ticker}/{s['name']}"):
            if strike == "pairs.json":
                continue
            with open(f"bin/{ticker}/{s['name']}/{strike}/pair.json", "r") as f:
                data = json.load(f)

            call, put = data["callSymbol"], data["putSymbol"]
            call_data = get_chart(call)
            put_data = get_chart(put)
            with open(f"bin/{ticker}/{s['name']}/{strike}/call.json", "w") as f:
                json.dump(call_data, f)

            with open(f"bin/{ticker}/{s['name']}/{strike}/put.json", "w") as f:
                json.dump(put_data, f)

            c += 2
            bar.update(c)


