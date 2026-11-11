"""Constrained, deterministic portfolio allocator.

This is the source of truth for weights. The LLM only writes the narrative; the guard
(orchestrator/guard.py) overwrites any LLM weights that break these rules.

Method (honest description - NOT full mean-variance):
  score  = feedback-weighted blend of ESG credibility and market view
  raw    = score^2 / annualised volatility   (risk-adjusted tilt, vol from real price stats)
  then hard constraints via iterative cap redistribution:
    - assets flagged as greenwashing share at most DIRTY_CAP of the portfolio
    - no single position above the risk-profile cap
    - any weight that cannot be placed legally goes to CASH
"""
from typing import Dict, List

DIRTY_CAP = 0.10
GREENWASH_RISK_LIMIT = 60
POSITION_CAP = {"conservative": 0.25, "moderate": 0.35, "aggressive": 0.45}
VIEW_SIGN = {"bullish": 1.0, "neutral": 0.0, "bearish": -1.0}


def is_dirty(esg_payload: dict) -> bool:
    return (esg_payload.get("greenwash_risk", 0) > GREENWASH_RISK_LIMIT
            or esg_payload.get("verdict") == "likely_greenwashing")


def combined_score(esg_payload: dict, mkt_payload: dict, w_esg: float = 1.0, w_mkt: float = 1.0) -> float:
    """0..1. ESG part = credibility/100. Market part = 0.5 + 0.5 * sign * confidence."""
    esg = esg_payload.get("esg_credibility", 50) / 100.0
    sign = VIEW_SIGN.get(mkt_payload.get("market_view", "neutral"), 0.0)
    mkt = 0.5 + 0.5 * sign * mkt_payload.get("confidence", 0.5)
    total = w_esg + w_mkt
    return (w_esg * esg + w_mkt * mkt) / total if total else 0.5


def _cap_redistribute(raw: Dict[str, float], budget: float, cap: float) -> Dict[str, float]:
    """Scale raw to sum to `budget`, no entry above `cap`; excess spills to uncapped names.
    Returns weights summing to <= budget (less only if every name is capped)."""
    if not raw or budget <= 0:
        return {t: 0.0 for t in raw}
    w = {t: 0.0 for t in raw}
    free = dict(raw)
    remaining = budget
    for _ in range(len(raw) + 1):
        total = sum(free.values())
        if total <= 0 or not free:
            break
        prop = {t: remaining * v / total for t, v in free.items()}
        over = [t for t, v in prop.items() if v > cap - w[t] + 1e-12]
        if not over:
            for t, v in prop.items():
                w[t] += v
            remaining = 0.0
            break
        for t in over:
            room = cap - w[t]
            w[t] += room
            remaining -= room
            free.pop(t)
    return w


def allocate(votes: List[dict], risk_profile: str, feedback_weights: Dict[str, float],
             price_stats: dict | None = None) -> Dict[str, float]:
    """Return {ticker: weight, 'CASH': weight} summing to 1.0."""
    price_stats = price_stats or {}
    esg = {v["ticker"]: v["payload"] for v in votes if v["agent"] == "esg_verifier"}
    mkt = {v["ticker"]: v["payload"] for v in votes if v["agent"] == "market_analyst"}
    w_esg = feedback_weights.get("esg_verifier", 1.0)
    w_mkt = feedback_weights.get("market_analyst", 1.0)
    cap = POSITION_CAP.get(risk_profile, 0.35)

    raw_clean, raw_dirty = {}, {}
    for t, e in esg.items():
        m = mkt.get(t, {})
        score = combined_score(e, m, w_esg, w_mkt)
        vol = price_stats.get(t, {}).get("vol_annual_pct") or 30.0
        raw = (score ** 2) / max(vol, 5.0)
        (raw_dirty if is_dirty(e) else raw_clean)[t] = raw

    # clean book gets 90% (or 100% if nothing is dirty); dirty book capped at DIRTY_CAP
    clean_budget = 1.0 - (DIRTY_CAP if raw_dirty else 0.0)
    if raw_clean:
        # make sure the cap is feasible, otherwise relax it just enough
        cap_eff = max(cap, clean_budget / len(raw_clean) + 1e-9)
        wc = _cap_redistribute(raw_clean, clean_budget, cap_eff)
    else:
        wc = {}
    wd = _cap_redistribute(raw_dirty, DIRTY_CAP, cap) if raw_dirty else {}

    weights = {**wc, **wd}
    weights = {t: round(w, 4) for t, w in weights.items() if w > 0}
    cash = round(1.0 - sum(weights.values()), 4)
    if cash > 1e-4:
        weights["CASH"] = cash
    return weights
