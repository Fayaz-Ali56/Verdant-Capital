"""Output guard: validates agent payloads and the final memo, and repairs violations.

Why: LLMs return out-of-range scores, weights that don't sum to 1, or ignore the
10% greenwashing cap stated in the prompt. Prompts are requests, not guarantees.
This module makes the rules enforced rather than hoped-for, and reports every
violation so it can be shown on the dashboard.
"""
import math
from typing import Dict, List, Tuple

from orchestrator.allocator import DIRTY_CAP, POSITION_CAP, is_dirty

TOL = 1e-6


def _num(x, default):
    try:
        f = float(x)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def sanitize_payload(payload, agent_tag: str, ticker: str) -> Tuple[dict, List[str]]:
    """Coerce an agent payload into legal ranges. Returns (clean_payload, issues)."""
    issues: List[str] = []
    if not isinstance(payload, dict):
        issues.append(f"{agent_tag}:{ticker} payload was {type(payload).__name__}, not an object")
        payload = {}
    p = dict(payload)
    p["ticker"] = ticker

    def fix(key, lo, hi, default):
        raw = p.get(key, None)
        val = _num(raw, default)
        clamped = _clamp(val, lo, hi)
        if raw is None or clamped != val or val != raw:
            if raw is not None and (clamped != val):
                issues.append(f"{agent_tag}:{ticker} {key}={raw!r} out of [{lo},{hi}] -> {clamped}")
            elif raw is None:
                issues.append(f"{agent_tag}:{ticker} {key} missing -> {default}")
        p[key] = clamped

    fix("confidence", 0.0, 1.0, 0.5)
    if agent_tag == "esg":
        fix("greenwash_risk", 0, 100, 50)
        fix("esg_credibility", 0, 100, 50)
        if p.get("verdict") not in ("credible", "mixed", "likely_greenwashing", "unverified"):
            issues.append(f"esg:{ticker} invalid verdict {p.get('verdict')!r} -> unverified")
            p["verdict"] = "unverified"
        p.setdefault("evidence", [])
        p.setdefault("red_flags", [])
    elif agent_tag == "market":
        if p.get("market_view") not in ("bullish", "neutral", "bearish"):
            issues.append(f"market:{ticker} invalid market_view {p.get('market_view')!r} -> neutral")
            p["market_view"] = "neutral"
        if p.get("carbon_outlook") not in ("rising", "stable", "falling"):
            p["carbon_outlook"] = "stable"
        p.setdefault("evidence", [])
        p.setdefault("reasoning", "")
    return p, issues


def validate_weights(weights: Dict[str, float], esg_by_ticker: Dict[str, dict],
                     universe: List[str], risk_profile: str) -> List[str]:
    """Return a list of violations (empty list = legal portfolio)."""
    v: List[str] = []
    cap = POSITION_CAP.get(risk_profile, 0.35)
    total = 0.0
    for t, w in weights.items():
        if t != "CASH" and t not in universe:
            v.append(f"{t} is not in the candidate universe")
        if not isinstance(w, (int, float)) or not math.isfinite(w) or w < -TOL or w > 1 + TOL:
            v.append(f"{t} weight {w!r} outside [0,1]")
            continue
        total += w
    if abs(total - 1.0) > 1e-3:
        v.append(f"weights sum to {total:.4f}, expected 1.0")
    dirty_total = sum(w for t, w in weights.items() if t in esg_by_ticker and is_dirty(esg_by_ticker[t]))
    if dirty_total > DIRTY_CAP + 1e-3:
        v.append(f"greenwash-flagged assets hold {dirty_total:.1%} (limit {DIRTY_CAP:.0%})")
    n_clean = sum(1 for t in esg_by_ticker if not is_dirty(esg_by_ticker[t]))
    eff_cap = max(cap, (1.0 - (DIRTY_CAP if n_clean < len(esg_by_ticker) else 0)) / max(n_clean, 1) + 1e-6)
    for t, w in weights.items():
        if t != "CASH" and isinstance(w, (int, float)) and w > eff_cap + 1e-3:
            v.append(f"{t} at {w:.1%} exceeds position cap {eff_cap:.0%}")
    return v


def guard_memo(memo, allocator_weights: Dict[str, float], esg_by_ticker: Dict[str, dict],
               universe: List[str], risk_profile: str) -> Tuple[dict, dict]:
    """Validate the LLM memo. If its portfolio is illegal (or missing) replace it with the
    allocator's weights, keeping the LLM's rationales where tickers match.
    Always recompute expected_esg_score from the final weights (never trust the LLM's number)."""
    report = {"violations": [], "repaired": False, "checks_run": [
        "weights in [0,1]", "weights sum to 1", "tickers in universe",
        f"greenwash-flagged <= {DIRTY_CAP:.0%}", "per-position cap", "score/confidence ranges"]}
    if not isinstance(memo, dict):
        report["violations"].append("memo was not a JSON object")
        memo = {}
    memo = dict(memo)

    llm_port = memo.get("portfolio") if isinstance(memo.get("portfolio"), list) else []
    llm_weights: Dict[str, float] = {}
    for row in llm_port:
        if isinstance(row, dict) and "ticker" in row:
            llm_weights[str(row["ticker"])] = _num(row.get("weight"), float("nan"))
    if not llm_weights:
        report["violations"].append("memo portfolio missing or empty")
    else:
        report["violations"] += validate_weights(llm_weights, esg_by_ticker, universe, risk_profile)
        if not report["violations"]:
            keys = set(llm_weights) | set(allocator_weights)
            dev = max(abs(llm_weights.get(k, 0.0) - allocator_weights.get(k, 0.0)) for k in keys)
            if dev > 0.02:
                report["violations"].append(
                    f"LLM weights deviate from the allocator by up to {dev*100:.1f} pp "
                    f"(allocator is the source of truth)")

    if report["violations"]:
        report["repaired"] = True
        rationale = {str(r.get("ticker")): r.get("rationale", "") for r in llm_port if isinstance(r, dict)}
        memo["portfolio"] = [
            {"ticker": t, "weight": w,
             "rationale": rationale.get(t) or ("Held as cash: no legal home for this weight" if t == "CASH"
                                               else "Weight set by constrained allocator")}
            for t, w in allocator_weights.items()]
        final_weights = allocator_weights
    else:
        final_weights = llm_weights

    # recompute, never trust the LLM's own arithmetic
    score = sum(w * esg_by_ticker[t].get("esg_credibility", 50)
                for t, w in final_weights.items() if t in esg_by_ticker)
    memo["expected_esg_score"] = round(score, 1)
    llm_conf = _num(memo.get("overall_confidence"), 0.5)
    if not 0.0 <= llm_conf <= 1.0:
        report["violations"].append(f"overall_confidence {llm_conf} out of range -> clamped")
    memo["overall_confidence"] = round(_clamp(llm_conf, 0.0, 1.0), 2)
    for k in ("disagreements_resolved", "residual_risks"):
        if not isinstance(memo.get(k), list):
            memo[k] = []
    report["status"] = ("REPAIRED" if report["repaired"] else "PASSED")
    return memo, report
