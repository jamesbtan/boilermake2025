import requests
from dotenv import dotenv_values

config = dotenv_values(".env")

resp = requests.get(f"https://newsapi.org/v2/everything?apiKey={config["NEWSAPI"]}&from=2025-02-20&sources=bloomberg,fortune,business-insider,reuters,the-wall-street-journal")
json = resp.json()
articles = json['articles']
headlines = ["- " + x["title"] for x in articles]
headlines = '\n'.join(headlines)

resp = requests.get(f"https://api.congress.gov/v3/bill?api_key={config["CONGRESSGOV"]}&limit=100&fromDateTime=2025-02-21T00:00:00Z")
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
stock tickers as well as their end-of-market prices for each day in the past two weeks,
and currently held stock tickers with their quantities.
Only use stocks which are listed in the historical data.

## Recent news headlines
{headlines}

## Recently modified laws
{newbills}

## Historical stock data

## Currently held stocks
"""

with open('prompt.txt', 'w') as f:
    f.write(prompt)
