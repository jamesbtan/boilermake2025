import requests
from dotenv import dotenv_values
from time import sleep

config = dotenv_values(".env")

resp = requests.get(f"https://newsapi.org/v2/everything?apiKey={config['NEWSAPI']}&from=2025-02-20&sources=bloomberg,fortune,business-insider,reuters,the-wall-street-journal")
json = resp.json()
articles = json['articles']
headlines = ["- " + x["title"] for x in articles]
headlines = '\n'.join(headlines)

resp = requests.get(f"https://api.congress.gov/v3/bill?api_key={config['CONGRESSGOV']}&limit=100&fromDateTime=2025-02-21T00:00:00Z")
json = resp.json()
newbills = ["- " + x["title"] for x in json['bills']]
newbills = '\n'.join(newbills)

tickers = [
  "FDC",
  "FEYE",
  "T",
  "DISCA",
  "PFE",
  "NFLX",
  "DIS",
  "BAC",
  "MSFT",
  "AAPL",
]
tickers = tickers[:5]

def get_ticker(t):
    resp = requests.get(f"https://api.polygon.io//v2/aggs/ticker/{t}/prev?apiKey={config['POLYGONAPI']}")
    json = resp.json()
    keys = ['o', 'c', 'h', 'l', 'n']
    print(json)
    stock = {k: json['results'][0][k] for k in keys}
    stock["ticker"] = json["ticker"]
    #sleep(15)
    return stock
stocks = [get_ticker(t) for t in tickers]
stocks = [f"- {s['ticker']} (open: {s['o']}, close: {s['c']}, high: {s['h']}, low: {s['l']}, transactions: {s['n']})" for s in stocks]
stocks = '\n'.join(stocks)

prompt = f"""# Introduction
You are acting as a top-tier financial trader.
You must make a statement of which stocks to buy and which to sell on certain days.

# Output
Please provide output in the following format:
```
[
    {{ "ticker": "AAPL", "count": -3 }},
    {{ "ticker": "MSFT", "count": 2 }},
]
```
Use positive counts to signify a buy, and negative counts for a sell.

# Provided information
You will receive the following information: recent news headlines, recently modified laws,
historical stock data from the previous day with tickers as well as
their open price, close price, highest price, lowest price, and number of transactions,
and currently held stock tickers with their quantities.

## Recent news headlines
{headlines}

## Recently modified laws
{newbills}

## Historical stock data
{stocks}

## Currently held stocks
"""

with open('prompt.txt', 'w') as f:
    f.write(prompt)
