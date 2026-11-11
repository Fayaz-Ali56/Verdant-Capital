"""Explicitly fictional ESG disclosures and synthetic prices for reproducible demos.

No real company or instrument is assessed or accused by these fixtures.
"""

import hashlib

import numpy as np
import pandas as pd

REPORTS = {
    "SOLR": {
        "issuer": "Solara Works (fictional)",
        "credibility": 84,
        "risk": 16,
        "verdict": "credible",
        "confidence": 0.86,
        "evidence": [
            "Synthetic disclosure: operational emissions declined 18% against a stated 2021 baseline.",
            "Synthetic disclosure: electricity procurement documentation includes a third-party assurance summary.",
        ],
        "flags": [],
    },
    "WIND": {
        "issuer": "Windward Grid (fictional)",
        "credibility": None,
        "risk": None,
        "verdict": "unverified",
        "confidence": 0.2,
        "evidence": [
            "Synthetic disclosure: target lacks an independently verified emissions baseline."
        ],
        "flags": ["Missing independent verification; classification remains unverified."],
    },
    "FOSS": {
        "issuer": "Fossilix Energy (fictional)",
        "credibility": 24,
        "risk": 86,
        "verdict": "likely_greenwashing",
        "confidence": 0.81,
        "evidence": [
            "Synthetic disclosure: net-zero commitment gives no reference-year baseline.",
            "Synthetic disclosure: planned capital expenditure is not tied to the stated target.",
        ],
        "flags": ["Missing baseline", "No documented capital allocation backing the claim"],
    },
}


def evidence(ticker: str):
    p = REPORTS.get(ticker)
    if not p:
        return []
    return [
        {
            "ticker": ticker,
            "source": f"SYNTHETIC_FIXTURE_{ticker}.txt",
            "page": 1,
            "text": text,
            "mode": "synthetic",
            "issuer": p["issuer"],
            "citation": f"[SYNTHETIC_FIXTURE_{ticker}.txt p.1]",
        }
        for text in p["evidence"]
    ]


def price_frame(tickers=None, periods: int = 260, event: str = "baseline") -> pd.DataFrame:
    """Stable per-asset random seeds ensure reproducible history in all UI paths."""
    tickers = list(REPORTS if tickers is None else tickers)
    if not isinstance(periods, int) or periods < 1:
        raise ValueError("Periods must be a positive integer")
    prices = {}
    for t in tickers:
        seed = int.from_bytes(hashlib.sha256(t.encode()).digest()[:4], "big")
        rng = np.random.default_rng(seed)
        drift = {"SOLR": 0.00055, "WIND": 0.00040, "FOSS": 0.0011}.get(t, 0.0002)
        vol = {"SOLR": 0.011, "WIND": 0.014, "FOSS": 0.018}.get(t, 0.016)
        prices[t] = 100 * np.exp(np.cumsum(rng.normal(drift, vol, periods)))
    frame = pd.DataFrame(prices, index=pd.bdate_range(end="2026-11-10", periods=periods))
    if event not in {"baseline", "carbon_price_spike", "policy_tightening", "market_selloff"}:
        raise ValueError("Unknown synthetic event scenario")
    if event != "baseline":
        # Fictional event impact, confined to the last 30 trading observations.
        effects = {
            "carbon_price_spike": {"SOLR": 0.07, "WIND": 0.04, "FOSS": -0.20},
            "policy_tightening": {"SOLR": 0.04, "WIND": 0.06, "FOSS": -0.16},
            "market_selloff": {"SOLR": -0.40, "WIND": -0.32, "FOSS": -0.45},
        }
        length = min(30, periods)
        fractions = np.linspace(0.0, 1.0, length)
        for ticker in frame.columns:
            multiplier = 1 + effects[event].get(ticker, 0) * fractions
            frame.loc[frame.index[-length:], ticker] *= multiplier
    return frame
