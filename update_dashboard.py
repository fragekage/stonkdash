# update_dashboard.py

import os
import json
import requests
import sys
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import numpy as np

# ─── Step 1: Skip if Market is Closed ──────────────────────────────────────────

def is_market_open():
    eastern = pytz.timezone('US/Eastern')
    now_et = datetime.now(eastern)
    if now_et.weekday() >= 5:
        return False
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, microsecond=0)
    return market_open <= now_et <= market_close

if not is_market_open():
    print("Market is closed. Skipping update.")
    sys.exit(0)

# ─── Step 2: Load API Keys ─────────────────────────────────────────────────────

load_dotenv()
TI_API_KEY = os.getenv("TI_API_KEY")
AV_API_KEY = os.getenv("AV_API_KEY")

TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
    "SPY", "QQQ", "MGC", "IEFA", "NEE", "D", "CRWV"
]

BASE_TI_URL = "https://api.tiingo.com"
BASE_AV_URL = "https://www.alphavantage.co/query"
HISTORICAL_FILE = "historical_prices.json"
FUNDAMENTALS_FILE = "fundamentals_history.json"
DASHBOARD_FILE = "ticker_dashboard_data.json"

# ─── Step 3: Utility ───────────────────────────────────────────────────────────

def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def today_date_str():
    return datetime.today().strftime("%Y-%m-%d")

# ─── Step 4: Historical Price Store ────────────────────────────────────────────

def load_json_file(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ─── Step 5: Fetch Historical Backfill ─────────────────────────────────────────

def fetch_historical_backfill(ticker):
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    start = one_year_ago.strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    try:
        url = f"{BASE_TI_URL}/tiingo/daily/{ticker}/prices?startDate={start}&endDate={end}&token={TI_API_KEY}"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        prices = []
        for day in data:
            date = day.get("date", "")[:10]
            close = safe_float(day.get("close"))
            if close is not None:
                prices.append([date, close])
        print(f"Backfilled {len(prices)} days for {ticker}")
        return prices
    except Exception as e:
        print(f"Error backfilling {ticker}: {e}")
        return []

# ─── Step 6: Fetch Today's Latest Price ────────────────────────────────────────

def fetch_latest_close(ticker):
    try:
        url = f"{BASE_TI_URL}/iex/?tickers={ticker}&token={TI_API_KEY}"
        r = requests.get(url)
        r.raise_for_status()
        data = r.json()
        price = data[0].get("last")
        if price is None:
            raise ValueError(f"No 'last' price in response: {data}")
        return safe_float(price)
    except Exception as e:
        print(f"Tiingo latest price error for {ticker}: {e}")
        return None

# ─── Step 7: Update Historical Prices ──────────────────────────────────────────

def update_historical_prices(historical):
    today_str = today_date_str()
    updated = False

    for ticker in TICKERS:
        series = historical.get(ticker, [])
        dates = [entry[0] for entry in series]

        if len(series) < 200:
            print(f"{ticker}: insufficient history ({len(series)}). Backfilling...")
            series = fetch_historical_backfill(ticker)
            historical[ticker] = series
            updated = True
            continue

        if today_str not in dates:
            latest_price = fetch_latest_close(ticker)
            if latest_price:
                series.append([today_str, latest_price])
                historical[ticker] = series[-365:]
                updated = True

    return updated

# ─── Step 8: Compute Returns & Volatility ──────────────────────────────────────

def compute_1y_stats(series):
    if len(series) < 200:
        return None, None

    series_sorted = sorted(series)
    prices = np.array([price for _, price in series_sorted])
    daily_returns = np.diff(prices) / prices[:-1]
    volatility = np.std(daily_returns) * np.sqrt(252)
    total_return = (prices[-1] - prices[0]) / prices[0]
    return total_return, volatility

# ─── Step 9: Fetch Fundamentals ────────────────────────────────────────────────

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

# ─── Step 10: Fetch and Store All Data ─────────────────────────────────────────

def fetch_data():
    dashboard_data = []
    today_str = today_date_str()

    historical_prices = load_json_file(HISTORICAL_FILE)
    fundamentals_history = load_json_file(FUNDAMENTALS_FILE)

    if update_historical_prices(historical_prices):
        print("Historical prices updated.")
        save_json_file(HISTORICAL_FILE, historical_prices)
    else:
        print("No new price data needed today.")

    for ticker in TICKERS:
        print(f"Processing {ticker}...")
        series = historical_prices.get(ticker, [])
        series_sorted = sorted(series)
        price = series_sorted[-1][1] if series_sorted else None

        total_return, volatility = compute_1y_stats(series_sorted)
        sharpe = (total_return / volatility) if (total_return is not None and volatility and volatility > 0) else None

        fundamentals = fetch_fundamentals_from_av(ticker)

        # Create today's fundamentals record
        today_fundamentals = {
            "date": today_str,
            "EPS": fundamentals["EPS"],
            "PE Ratio": fundamentals["PE Ratio"],
            "PEG Ratio": fundamentals["PEG Ratio"],
            "Forward PE": fundamentals["Forward PE"],
            "Price to FCF": None,
            "1Y Return": total_return,
            "1Y Volatility": volatility,
            "Approx Sharpe Ratio": sharpe
        }

        # Append to history if new
        history_series = fundamentals_history.get(ticker, [])
        if not any(entry.get("date") == today_str for entry in history_series):
            history_series.append(today_fundamentals)
            fundamentals_history[ticker] = history_series

        # Add to dashboard
        row = {
            "Ticker": ticker,
            "Price": price,
            **today_fundamentals
        }

        dashboard_data.append(row)

    # Save updated fundamentals history
    save_json_file(FUNDAMENTALS_FILE, fundamentals_history)

    return dashboard_data

# ─── Step 11: Save to File ─────────────────────────────────────────────────────

if __name__ == "__main__":
    data = fetch_data()
    if data:
        save_json_file(DASHBOARD_FILE, data)
        print("Dashboard data updated.")
    else:
        print("No data to write.")
