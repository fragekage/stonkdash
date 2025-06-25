# update_dashboard.py

import os
import json
import requests
import sys
from datetime import datetime
import pytz
from dotenv import load_dotenv

# ─── Step 1: Skip if Market is Closed ──────────────────────────────────────────

def is_market_open():
    eastern = pytz.timezone('US/Eastern')
    now_et = datetime.now(eastern)
    # Only run on weekdays
    if now_et.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    # Only run between 9:30 AM and 4:00 PM ET
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now_et <= market_close

if not is_market_open():
    print("Market is closed. Skipping update.")
    sys.exit(0)

# ─── Step 2: Load API Keys ─────────────────────────────────────────────────────

load_dotenv()
TD_API_KEY = os.getenv("TD_API_KEY")
AV_API_KEY = os.getenv("AV_API_KEY")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA","SPY","QQQ","MGC","IEFA","NEE","D","CRWV"]
BASE_TD_URL = "https://api.twelvedata.com"
BASE_AV_URL = "https://www.alphavantage.co/query"

# ─── Step 3: Utility ───────────────────────────────────────────────────────────

def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

# ─── Step 4: Fetch Price ───────────────────────────────────────────────────────

def fetch_price_from_twelve(ticker):
    try:
        url = f"{BASE_TD_URL}/quote?symbol={ticker}&apikey={TD_API_KEY}"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        return safe_float(data.get("close"))  # Use "close" instead of missing "price"
    except Exception as e:
        print(f"Twelve Data price error for {ticker}: {e}")
        return None

# ─── Step 5: Fetch Fundamentals ────────────────────────────────────────────────

def fetch_fundamentals_from_av(ticker):
    try:
        url = f"{BASE_AV_URL}?function=OVERVIEW&symbol={ticker}&apikey={AV_API_KEY}"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()

        if not data or "Symbol" not in data:
            raise ValueError("No overview data returned")

        return {
            "EPS": safe_float(data.get("EPS")),
            "PE Ratio": safe_float(data.get("PERatio")),
            "PEG Ratio": safe_float(data.get("PEGRatio")),
            "Forward PE": safe_float(data.get("ForwardPE")),
        }
    except Exception as e:
        print(f"Alpha Vantage fundamentals error for {ticker}: {e}")
        return {
            "EPS": None,
            "PE Ratio": None,
            "PEG Ratio": None,
            "Forward PE": None,
        }

# ─── Step 6: Fetch All Data ────────────────────────────────────────────────────

def fetch_data():
    dashboard_data = []

    for ticker in TICKERS:
        print(f"Processing {ticker}...")
        price = fetch_price_from_twelve(ticker)
        fundamentals = fetch_fundamentals_from_av(ticker)

        row = {
            "Ticker": ticker,
            "Price": price,
            "EPS": fundamentals["EPS"],
            "PE Ratio": fundamentals["PE Ratio"],
            "PEG Ratio": fundamentals["PEG Ratio"],
            "Forward PE": fundamentals["Forward PE"],
            "Price to FCF": None,             # Not provided
            "1Y Return": None,                # Temporarily omitted
            "1Y Volatility": None,            # Temporarily omitted
            "Approx Sharpe Ratio": None       # Temporarily omitted
        }

        dashboard_data.append(row)

    return dashboard_data

# ─── Step 7: Save to File ──────────────────────────────────────────────────────

if __name__ == "__main__":
    data = fetch_data()
    if data:
        with open("ticker_dashboard_data.json", "w") as f:
            json.dump(data, f, indent=2)
        print("Dashboard data updated.")
    else:
        print("No data to write.")
