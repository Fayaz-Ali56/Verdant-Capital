"""Fetch real market + carbon-price data. Run: python -m data.fetch_market"""
import os
import yfinance as yf
import pandas as pd
import config

os.makedirs(config.DATA_DIR, exist_ok=True)

def fetch(tickers, period="1y"):
    df = yf.download(tickers, period=period, auto_adjust=True)["Close"]
    return df

def price_stats(df: pd.DataFrame) -> dict:
    out = {}
    for col in df.columns:
        s = df[col].dropna()
        if len(s) < 30:
            continue
        rets = s.pct_change().dropna()
        out[col] = {
            "last": round(float(s.iloc[-1]), 2),
            "return_30d_pct": round(float((s.iloc[-1] / s.iloc[-30] - 1) * 100), 2),
            "vol_annual_pct": round(float(rets.std() * (252 ** 0.5) * 100), 2),
            "trend_90d": "up" if s.iloc[-1] > s.iloc[-90] else "down",
        }
    return out

def main():
    tickers = list(config.DEFAULT_CANDIDATES) + [config.CARBON_TICKER]
    df = fetch(tickers)
    df = df.dropna(axis=1, how="all")
    if df.empty or len(df) < 60:
        raise SystemExit("❌ No market data downloaded (check internet / yfinance). "
                         "Nothing was written, so any earlier good files are untouched.")
    missing = [t for t in tickers if t not in df.columns]
    if missing:
        print("⚠️  No data for:", ", ".join(missing))
    df.to_csv(os.path.join(config.DATA_DIR, "prices.csv"))
    stats = price_stats(df)
    with open(os.path.join(config.DATA_DIR, "price_stats.json"), "w") as f:
        import json; json.dump(stats, f, indent=2)
    print("Saved prices.csv + price_stats.json for:", ", ".join(stats.keys()))

if __name__ == "__main__":
    main()
