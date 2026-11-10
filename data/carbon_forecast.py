"""Carbon-credit price forecasting. Run: python -m data.carbon_forecast

Uses Prophet if available; falls back to a robust linear-trend model so the
pipeline NEVER breaks on install day. Saves forecast + summary for the dashboard
and feeds the carbon outlook into the Market Analyst agent.
"""
import json, os
import pandas as pd
import config

DAYS = 30

def _load_prices() -> pd.Series:
    path = os.path.join(config.DATA_DIR, "prices.csv")
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if config.CARBON_TICKER in df.columns:
            return df[config.CARBON_TICKER].dropna()
    import yfinance as yf
    s = yf.download(config.CARBON_TICKER, period="1y", auto_adjust=True)["Close"]
    return s.dropna()

def _prophet_forecast(series: pd.Series):
    from prophet import Prophet
    df = pd.DataFrame({"ds": series.index, "y": series.values})
    m = Prophet(daily_seasonality=False, weekly_seasonality=True,
                yearly_seasonality=True, interval_width=0.8)
    m.fit(df)
    future = m.make_future_dataframe(periods=DAYS)
    fc = m.predict(future)
    return fc[["ds", "yhat", "yhat_lower", "yhat_upper"]], "prophet"

def _linear_fallback(series: pd.Series):
    """Weighted linear trend + 20d rolling volatility bands. Good enough to demo."""
    import numpy as np
    x = np.arange(len(series), dtype=float)
    w = np.linspace(0.5, 1.0, len(series))          # recent data weighs more
    a, b = np.polyfit(x, series.values, 1, w=w)
    future_x = np.arange(len(series), len(series) + DAYS, dtype=float)
    yhat = a * future_x + b
    resid = series.values - (a * x + b)
    band = float(np.nanstd(resid[-60:])) * 1.28
    last_date = series.index[-1]
    fut_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=DAYS)
    hist = pd.DataFrame({"ds": series.index, "yhat": a * x + b,
                         "yhat_lower": a * x + b - band, "yhat_upper": a * x + b + band})
    fut = pd.DataFrame({"ds": fut_dates, "yhat": yhat,
                        "yhat_lower": yhat - band, "yhat_upper": yhat + band})
    return pd.concat([hist, fut], ignore_index=True), "linear-trend"

def _backtest_mape(series: pd.Series, horizon: int = 30):
    """Honest accuracy number: fit on all but last `horizon` days, score the holdout."""
    if len(series) < horizon + 60:
        return None
    train, test = series.iloc[:-horizon], series.iloc[-horizon:]
    try:
        fc, _ = _prophet_forecast(train)
    except Exception:
        fc, _ = _linear_fallback(train)
    pred = fc.set_index("ds")["yhat"].reindex(test.index).ffill()
    mape = float(((test - pred).abs() / test).mean() * 100)
    return round(mape, 2)

def main():
    series = _load_prices()
    try:
        fc, engine = _prophet_forecast(series)
    except Exception as e:
        print(f"[carbon] Prophet unavailable ({type(e).__name__}) -> linear fallback")
        fc, engine = _linear_fallback(series)

    hist_last = float(series.iloc[-1])
    fut = fc[fc["ds"] > series.index[-1]]
    fut_last = float(fut["yhat"].iloc[-1])
    change_pct = round((fut_last / hist_last - 1) * 100, 2)
    outlook = "rising" if change_pct > 1.5 else ("falling" if change_pct < -1.5 else "stable")

    mape = _backtest_mape(series)
    summary = {"engine": engine, "ticker": config.CARBON_TICKER,
               "last_price": round(hist_last, 2),
               "forecast_30d": round(fut_last, 2),
               "change_pct_30d": change_pct,
               "outlook": outlook,
               "backtest_mape_pct": mape,
               "computed": str(pd.Timestamp.now().date())}

    os.makedirs(config.DATA_DIR, exist_ok=True)
    fc.to_csv(os.path.join(config.DATA_DIR, "carbon_forecast.csv"), index=False)
    with open(os.path.join(config.DATA_DIR, "carbon_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))

def carbon_summary() -> dict:
    path = os.path.join(config.DATA_DIR, "carbon_summary.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

if __name__ == "__main__":
    main()
