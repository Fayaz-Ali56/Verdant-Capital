"""Deterministic constrained portfolio optimizer. Does not place trades.

The LLM cannot edit these mathematically validated allocations. Missing ESG
verification is restricted, confirmed high-risk ESG claims are excluded under
strict mandates, and any infeasible investment remains in CASH.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize

RISK = {
    "conservative": {"penalty": 22.0, "max_asset": 0.35},
    "moderate": {"penalty": 11.0, "max_asset": 0.55},
    "aggressive": {"penalty": 5.5, "max_asset": 0.70},
}


def optimize(
    candidates,
    prices: pd.DataFrame,
    esg: dict,
    risk_profile: str = "moderate",
    strict_esg: bool = True,
    annual_cash_return: float = 0.0,
    influence: dict | None = None,
) -> dict:
    candidates = list(dict.fromkeys(str(t).upper().strip() for t in candidates if str(t).strip()))
    if "CASH" in candidates:
        raise ValueError("CASH is reserved for unallocated capital")
    if risk_profile not in RISK:
        raise ValueError("Unknown risk profile")
    if not math.isfinite(float(annual_cash_return)):
        raise ValueError("Cash return must be finite")
    policy = RISK.get(risk_profile, RISK["moderate"])
    influence = influence or {}
    if any(
        not math.isfinite(float(influence.get(name, 1.0)))
        for name in ("market_analyst", "esg_verifier")
    ):
        raise ValueError("Agent influence must be finite")
    market_influence = float(np.clip(influence.get("market_analyst", 1.0), 0.5, 1.5))
    esg_influence = float(np.clip(influence.get("esg_verifier", 1.0), 0.5, 1.5))
    applied_influence = {"esg_verifier": esg_influence, "market_analyst": market_influence}
    prices = prices.copy() if isinstance(prices, pd.DataFrame) else pd.DataFrame()
    if not prices.empty:
        prices.columns = [str(k).upper() for k in prices.columns]
        prices = prices.loc[:, ~prices.columns.duplicated(keep=False)]
    caps = {}
    for ticker in candidates:
        info = esg.get(ticker, {})
        risk = info.get("greenwash_risk")
        verdict = info.get("verdict", "unverified")
        bad = (isinstance(risk, (float, int)) and risk > 60) or verdict == "likely_greenwashing"
        if bad and strict_esg:
            caps[ticker] = 0.0
        elif risk is None or verdict == "unverified":
            caps[ticker] = 0.1 if strict_esg else 0.2
        else:
            caps[ticker] = policy["max_asset"]
    reliable = []
    for ticker in candidates:
        if ticker in prices.columns:
            series = pd.to_numeric(prices[ticker], errors="coerce").dropna()
            if len(series) >= 45 and series.gt(0).all() and np.isfinite(series).all():
                reliable.append(ticker)
            else:
                caps[ticker] = 0.0
        else:
            caps[ticker] = 0.0
    assets = [t for t in candidates if caps[t] > 0 and t in reliable]
    weights = {t: 0.0 for t in candidates}
    weights["CASH"] = 1.0
    note = "No eligible assets with sufficiently complete prices; allocation held in cash."
    if not assets:
        return {
            "weights": weights,
            "status": "cash_only",
            "reason": note,
            "expected_return_pct": 0.0,
            "volatility_pct": 0.0,
            "esg_caps": caps,
            "optimizer": "SciPy SLSQP",
            "influence_used": applied_influence,
        }

    hist = prices[assets].apply(pd.to_numeric, errors="coerce").dropna()
    returns = hist.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 30:
        return {
            "weights": weights,
            "status": "cash_only",
            "reason": "Insufficient common history.",
            "expected_return_pct": 0.0,
            "volatility_pct": 0.0,
            "esg_caps": caps,
            "optimizer": "SciPy SLSQP",
            "influence_used": applied_influence,
        }
    # Winsorize runaway estimates, shrink covariance toward diagonal and regularize.
    mu = np.clip(returns.mean().to_numpy() * 252, -0.3, 0.3)
    historical_mu = np.append(mu.copy(), annual_cash_return)
    raw_cov = returns.cov().to_numpy() * 252
    covariance = 0.8 * raw_cov + 0.2 * np.diag(np.diag(raw_cov))
    covariance += np.eye(len(assets)) * 1e-5
    # Performance feedback changes a SOFT preference, never a hard ESG exclusion.
    # Separate simulated labels from verified outcomes at the feedback-store boundary.
    mu = mu * market_influence
    soft_esg_penalty = np.array(
        [
            (max(0.0, 65.0 - float(esg.get(t, {}).get("esg_credibility") or 0)) / 100.0)
            * 0.06
            * esg_influence
            for t in assets
        ]
    )
    mu = np.append(mu - soft_esg_penalty, annual_cash_return)
    covariance = np.pad(covariance, ((0, 1), (0, 1)), constant_values=0)
    n = len(assets)
    bounds = [(0.0, caps[t]) for t in assets] + [(0.0, 1.0)]
    x0 = np.zeros(n + 1)
    x0[-1] = 1.0

    def loss(w):
        return float(policy["penalty"] * (w @ covariance @ w) / 2.0 - mu @ w)

    result = minimize(
        loss,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=[{"type": "eq", "fun": lambda w: float(w.sum() - 1)}],
        options={"maxiter": 500, "ftol": 1e-10},
    )
    if result.success and np.all(np.isfinite(result.x)):
        w = np.clip(result.x, 0.0, 1.0)
        if abs(sum(w) - 1) < 1e-5 and all(w[j] <= bounds[j][1] + 1e-6 for j in range(len(w))):
            note = "Long-only variance-penalized optimization with ESG position constraints."
            for j, ticker in enumerate(assets):
                weights[ticker] = float(w[j])
            weights["CASH"] = float(w[-1])
        else:
            note = "Optimizer produced invalid weights; safely retained cash."
    else:
        note = "Numerical solver failed; safely retained cash."

    # Any rounding correction is absorbed by cash rather than changing constrained assets.
    weights["CASH"] = max(0.0, 1.0 - sum(weights[t] for t in candidates))
    selection = np.array([weights[t] for t in assets] + [weights["CASH"]])
    variance = max(float(selection @ covariance @ selection), 0.0)
    return {
        "weights": weights,
        "status": "optimized" if "Long-only" in note else "cash_only",
        "reason": note,
        "expected_return_pct": round(float(historical_mu @ selection) * 100, 2),
        "adjusted_return_pct": round(float(mu @ selection) * 100, 2),
        "volatility_pct": round(math.sqrt(variance) * 100, 2),
        "esg_caps": caps,
        "optimizer": "SciPy SLSQP",
        "influence_used": applied_influence,
    }
