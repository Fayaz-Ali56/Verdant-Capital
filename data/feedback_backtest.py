"""Backtest killshot: seed the Feedback Layer with 30 days of decisions + outcomes,
then emit the adaptive-weights timeline for the dashboard.

Story arc: the ESG Verifier flags XOM greenwashing on day 5, before the market reacts.
The Market Analyst chases the fossil bounce and gets burned. From day 6 onward the
feedback loop rewards the ESG agent — its influence overtakes the market agent.
Outcomes use REAL forward returns when prices.csv exists, else synthetic.
Run: python -m data.feedback_backtest
"""
import json, os
import numpy as np
import pandas as pd
import config
import data.feedback_store as fb

DAYS = 30
SEED = 42
GREENWASHED = {"XOM"}
_MKT_BASE_ACC = {"NEE": .68, "XOM": .50, "TSLA": .58, "ENPH": .64, "ICLN": .66, "VEST": .60}
_ESG_SKILL = {"NEE": .82, "XOM": .30, "TSLA": .60, "ENPH": .80, "ICLN": .85, "VEST": .62}
# XOM flag-rate: before day 5 the esg agent (like everyone) misses it; after the flag, it stays vigilant
_XOM_FLAG_RATE = lambda day: 0.10 if day < 5 else 0.92

def _real_returns(tickers, days=DAYS):
    path = os.path.join(config.DATA_DIR, "prices.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)["Close"]
    out = {}
    for t in tickers:
        if t not in df.columns or df[t].dropna().shape[0] < days + 5:
            continue
        s = df[t].dropna()
        out[t] = float(s.shift(-days).div(s).iloc[0] - 1)
    return out or None

def main():
    fb.reset_outcomes()
    rng = np.random.default_rng(SEED)
    tickers = config.DEFAULT_CANDIDATES
    real = _real_returns(tickers)
    returns = real or {t: float(rng.normal(0.02, 0.08)) for t in tickers}
    direction = {t: ("bullish" if r > 0 else "bearish") for t, r in returns.items()}
    # XOM story: positive drift lures the market agent, then reality hits
    if "XOM" in direction:
        direction["XOM"] = "bearish"

    timeline = []
    for day in range(DAYS):
        esg_hits = mkt_hits = n = 0
        for t in tickers:
            is_gw = t in GREENWASHED
            if is_gw:
                flag_rate = _XOM_FLAG_RATE(day)
                esg_pred = "flag_greenwashing" if rng.random() < flag_rate else "pass"
                esg_correct = 1 if ((esg_pred == "flag_greenwashing") == is_gw) else 0
            else:
                esg_pred = "flag_greenwashing" if rng.random() > _ESG_SKILL[t] else "pass"
                esg_correct = 1 if esg_pred == "pass" else 0

            if t == "XOM" and day >= 5:
                mkt_pred = "bearish"          # chastened after the bounce trap
                mkt_correct = 1 if direction[t] == "bearish" else 0
            else:
                mkt_pred = direction[t] if rng.random() < _MKT_BASE_ACC[t] else                            ("bearish" if direction[t] == "bullish" else "bullish")
                mkt_correct = 1 if mkt_pred == direction[t] else 0
                if t == "XOM" and day < 5:    # chasing the bounce
                    mkt_pred = "bullish"
                    mkt_correct = 0

            fb.record_outcome(day + 1, t, "esg_verifier", esg_pred, returns[t], correct=esg_correct)
            fb.record_outcome(day + 1, t, "market_analyst", mkt_pred, returns[t], correct=mkt_correct)
            esg_hits += esg_correct; mkt_hits += mkt_correct; n += 1
        w = fb.agent_weights()
        timeline.append({"day": day + 1, "esg_acc": round(esg_hits / n, 3),
                         "mkt_acc": round(mkt_hits / n, 3),
                         "esg_weight": w.get("esg_verifier", 1.0),
                         "mkt_weight": w.get("market_analyst", 1.0)})

    story = ("SIMULATED SCENARIO: agent hit-rates are scripted (see _ESG_SKILL / _MKT_BASE_ACC) to "
             "demonstrate the re-weighting mechanism. Only the 30-day forward returns are real, and "
             "only when prices.csv exists. In this scenario the ESG Verifier flags XOM on day 5, the "
             "Market Analyst chases the fossil bounce and is wrong, and the loop re-weights influence.")
    with open(os.path.join(config.DATA_DIR, "feedback_timeline.json"), "w") as f:
        json.dump({"simulated": True, "returns_source": "real" if real else "synthetic",
                   "days": timeline, "story": story}, f, indent=2)
    for d in (timeline[3], timeline[5], timeline[10], timeline[29]):
        print(d)

if __name__ == "__main__":
    main()
