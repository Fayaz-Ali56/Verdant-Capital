"""Carbon-ETF proxy forecast and dated holdout. NOT a carbon-credit spot forecast.

Run: python -m data.carbon_forecast
Forecast uncertainty is a heuristic interval, not a calibrated statistical guarantee.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

import config
from data.fetch_market import fetch, load_cached_prices
from data.files import write_json, write_text

HORIZON = 30  # trading sessions, not calendar days


def _load_prices():
    frame = load_cached_prices()
    if config.CARBON_TICKER in frame.columns and len(frame[config.CARBON_TICKER].dropna()) >= 65:
        return frame[config.CARBON_TICKER].dropna()
    fresh = fetch([config.CARBON_TICKER])
    return fresh[config.CARBON_TICKER].dropna()


def forecast(series, horizon=HORIZON):
    """Regularized recent log-linear trend; reproduces without Prophet."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    s = s[(s > 0) & np.isfinite(s)]
    if not isinstance(horizon, int) or not 1 <= horizon <= 252:
        raise ValueError("Forecast horizon must be between 1 and 252 trading sessions")
    if len(s) < 65:
        raise ValueError("At least 65 valid market observations are required")
    s = s.iloc[-180:]
    x = np.arange(len(s), dtype=float)
    logy = np.log(s.to_numpy())
    slope, _intercept = np.polyfit(x, logy, deg=1)
    daily_drift = float(np.clip(slope, -0.009, 0.009))
    projected = float(s.iloc[-1]) * np.exp(daily_drift * np.arange(1, horizon + 1))
    residual_vol = float(np.std(np.diff(logy) - daily_drift))
    offsets = np.arange(1, horizon + 1)
    # These are approximate volatility bands, NOT calibrated 80% intervals.
    spread = 1.28 * max(residual_vol, 0.0001) * np.sqrt(offsets)
    start = pd.Timestamp(s.index[-1])
    dates = pd.bdate_range(start + pd.offsets.BDay(1), periods=horizon)
    output = pd.DataFrame(
        {
            "ds": dates,
            "yhat": projected,
            "yhat_lower": projected * np.exp(-spread),
            "yhat_upper": projected * np.exp(spread),
        }
    )
    return output


def main():
    series = _load_prices()
    future = forecast(series)
    end = float(future["yhat"].iloc[-1])
    current = float(series.iloc[-1])
    pct = (end / current - 1) * 100
    holdout = series.iloc[-HORIZON:]
    try:
        predictions = forecast(series.iloc[:-HORIZON], horizon=HORIZON)
        mean_absolute_pct_error = float(
            np.mean(
                np.abs((holdout.to_numpy() - predictions["yhat"].to_numpy()) / holdout.to_numpy())
            )
            * 100
        )
    except (ValueError, ZeroDivisionError):
        mean_absolute_pct_error = None
    report = {
        "ticker": config.CARBON_TICKER,
        "instrument_type": "carbon-related ETF proxy",
        "engine": "regularized log-linear trend",
        "last_price": round(current, 4),
        "forecast_30d": round(end, 4),
        "forecast_trading_sessions": HORIZON,
        "change_pct_30d": round(pct, 3),
        "outlook": "rising" if pct > 1.5 else ("falling" if pct < -1.5 else "stable"),
        "backtest_mape_pct": round(mean_absolute_pct_error, 3)
        if mean_absolute_pct_error is not None
        else None,
        "market_data_as_of": str(pd.Timestamp(series.index[-1]).date()),
        "mode": "historical_market_data",
        "uncertainty": "heuristic volatility bands; not calibrated",
        "disclaimer": "KRBN is a listed ETF proxy, not the price of a specific carbon allowance or spot credit.",
    }
    dest = Path(config.DATA_DIR)
    dest.mkdir(parents=True, exist_ok=True)
    write_text(dest / "carbon_forecast.csv", future.to_csv(index=False))
    write_json(dest / "carbon_summary.json", report)
    print(json.dumps(report, indent=2))
    return report


def carbon_summary():
    path = Path(config.DATA_DIR) / "carbon_summary.json"
    if path.is_file():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            pass
    return {}


if __name__ == "__main__":
    main()
