# update_dashboard.py

import os
import json
import requests
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import yfinance as yf

# Load API key from .env or GitHub environment
load_dotenv()
TD_API_KEY = os.getenv("TD_API_KEY")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

BASE_URL = "https://api.twelvedata.com"

# Helper to calculate 1Y return and volatility
def get_1y_stats(ticker):
    t = yf.Ticker(ticker)
    hist = t.history(period="1y")
    if hist.empty or len(hist) < 252:
        return None, None

    prices = hist['Close']
    daily_returns = prices.pct_change().dropna()
    volatility = np.std(daily_returns) * np.sqrt(252)
    total_return = (prices[-1] - prices[0]) / prices[0]
    return total_return, volatility

# Fetch financial ratios from Twelve Data
def fetch_twelve_data(symbol):
    url = f"{BASE_URL}/fundamentals?symbol={symbol}&apikey={TD_API_KEY}"
    r = requests.get(url)
    if r.status_code != 200:
        raise ValueError(f"Twelve Data error for {symbol}: {r.status_code}")
    return r.json()

# Fetch price from Twelve Data
def fetch_price(symbol):
    url = f"{BASE_URL}/price?symbol={symbol}&apikey={TD_API_KEY}"
    r = requests.get(url)
    if r.status_code != 200:
        raise ValueError(f"Price fetch error for {symbol}: {r.status_code}")
    return float(r.json().get("price"))

# Main fetch function
def fetch_data():
    dashboard_data = []
    for symbol in TICKERS:
        try:
            ratios = fetch_twelve_data(symbol)
            price = fetch_price(symbol)
            total_return, volatility = get_1y_stats(symbol)
            sharpe = total_return / volatility if total_return and volatility else None

            fundamentals = ratios.get("fundamentals", {})
            row = {
                "Ticker": symbol,
                "Price": price,
                "EPS": float(fundamentals.get("EPS", {}).get("value", None)),
                "PE Ratio": float(fundamentals.get("PE_ratio", {}).get("value", None)),
                "PEG Ratio": float(fundamentals.get("PEG_ratio", {}).get("value", None)),
                "Forward PE": float(fundamentals.get("Forward_PE_ratio", {}).get("value", None)),
                "Price to FCF": float(fundamentals.get("Price_to_Free_Cash_Flow", {}).get("value", None)),
                "1Y Return": total_return,
                "1Y Volatility": volatility,
                "Approx Sharpe Ratio": sharpe
            }
            dashboard_data.append(row)
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    return dashboard_data

# Save JSON
if __name__ == "__main__":
    data = fetch_data()
    with open("ticker_dashboard_data.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Dashboard data updated.")
