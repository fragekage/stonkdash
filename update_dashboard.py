import yfinance as yf
import json
import subprocess
from datetime import datetime

# 1. Define tickers to track
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA']

# 2. Fetch data
def fetch_data(tickers):
    data = []
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        info = stock.info
        entry = {
            "Ticker": ticker,
            "Beta": round(info.get("beta", 0), 2),
            "ROIC": round(info.get("returnOnCapitalEmployed", 0), 2),
            "PEG Ratio": round(info.get("pegRatio", 0), 2),
            "Forward PE": round(info.get("forwardPE", 0), 2),
            "Price to FCF": round(info.get("priceToFreeCashFlows", 0), 2)
        }
        data.append(entry)
    return data

# 3. Write to JSON file
def write_json(data, filepath="ticker_dashboard_data.json"):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

# 4. Git commit + push
def git_commit_push(message):
    subprocess.run(["git", "add", "ticker_dashboard_data.json"])
    subprocess.run(["git", "commit", "-m", message])
    subprocess.run(["git", "push"])

# === Run everything ===
if __name__ == "__main__":
    print("Fetching data...")
    data = fetch_data(tickers)
    write_json(data)
    print("Data written to ticker_dashboard_data.json")

    commit_message = f"Auto-update data: {datetime.now().isoformat(timespec='minutes')}"
    print("Committing and pushing...")
    git_commit_push(commit_message)

    print("✅ Dashboard data updated and pushed.")
