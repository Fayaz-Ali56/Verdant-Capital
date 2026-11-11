"""Run: LLM_PROVIDER=mock python -m pytest -q   (no API keys or network needed)"""
import os
os.environ["LLM_PROVIDER"] = "mock"

import math
import pytest
import config
from orchestrator.allocator import allocate, is_dirty, DIRTY_CAP, POSITION_CAP
from orchestrator.guard import sanitize_payload, guard_memo, validate_weights
from orchestrator.graph import build_graph, initial_state, find_conflicts


def _vote(agent, t, **p):
    return {"agent": agent, "ticker": t, "confidence": p.get("confidence", 0.7), "payload": p}


def _votes(spec):
    """spec: {ticker: (greenwash_risk, credibility, verdict, view)}"""
    out = []
    for t, (risk, cred, verdict, view) in spec.items():
        out.append(_vote("esg_verifier", t, greenwash_risk=risk, esg_credibility=cred, verdict=verdict))
        out.append(_vote("market_analyst", t, market_view=view, confidence=0.7))
    return out


FW = {"esg_verifier": 1.0, "market_analyst": 1.0}


def test_weights_sum_to_one_and_nonnegative():
    v = _votes({"A": (10, 80, "credible", "bullish"), "B": (20, 70, "credible", "neutral"),
                "C": (80, 30, "likely_greenwashing", "bullish")})
    w = allocate(v, "moderate", FW)
    assert math.isclose(sum(w.values()), 1.0, abs_tol=1e-3)
    assert all(x >= 0 for x in w.values())


def test_greenwash_cap_enforced_even_when_market_is_bullish():
    v = _votes({"A": (10, 80, "credible", "bearish"), "B": (20, 70, "credible", "bearish"),
                "DIRTY": (95, 5, "likely_greenwashing", "bullish")})
    w = allocate(v, "aggressive", FW)
    assert w.get("DIRTY", 0) <= DIRTY_CAP + 1e-3


def test_position_cap_respected():
    v = _votes({f"T{i}": (10, 60 + i, "credible", "bullish") for i in range(6)})
    w = allocate(v, "conservative", FW)
    assert max(w.values()) <= POSITION_CAP["conservative"] + 1e-3


def test_all_dirty_goes_mostly_to_cash():
    v = _votes({"X": (90, 10, "likely_greenwashing", "bullish"), "Y": (85, 15, "likely_greenwashing", "bullish")})
    w = allocate(v, "moderate", FW)
    assert w.get("CASH", 0) >= 0.89
    assert math.isclose(sum(w.values()), 1.0, abs_tol=1e-3)


def test_feedback_weight_shifts_allocation():
    v = _votes({"A": (10, 95, "credible", "bearish"), "B": (10, 40, "credible", "bullish"),
                "C": (10, 60, "credible", "neutral"), "D": (10, 60, "credible", "neutral")})
    esg_heavy = allocate(v, "aggressive", {"esg_verifier": 2.0, "market_analyst": 0.5})
    mkt_heavy = allocate(v, "aggressive", {"esg_verifier": 0.5, "market_analyst": 2.0})
    assert esg_heavy["A"] > mkt_heavy["A"]


# ---------------- guard
def test_sanitize_clamps_out_of_range_and_bad_enums():
    p, issues = sanitize_payload({"greenwash_risk": 250, "esg_credibility": -5, "confidence": 1.7,
                                  "verdict": "maybe"}, "esg", "ZZZ")
    assert p["greenwash_risk"] == 100 and p["esg_credibility"] == 0 and p["confidence"] == 1.0
    assert p["verdict"] == "unverified" and issues


def test_sanitize_survives_non_dict_and_nan():
    p, issues = sanitize_payload(["not", "a", "dict"], "market", "ZZZ")
    assert p["market_view"] == "neutral" and issues
    p2, _ = sanitize_payload({"confidence": float("nan"), "market_view": "bullish"}, "market", "ZZZ")
    assert 0.0 <= p2["confidence"] <= 1.0


def test_guard_repairs_hostile_memo():
    esg = {"A": {"greenwash_risk": 10, "esg_credibility": 80, "verdict": "credible"},
           "B": {"greenwash_risk": 90, "esg_credibility": 10, "verdict": "likely_greenwashing"}}
    alloc = {"A": 0.9, "B": 0.1}
    bad = {"portfolio": [{"ticker": "A", "weight": 0.2}, {"ticker": "B", "weight": 0.8}],
           "expected_esg_score": 999, "overall_confidence": 5}
    memo, rep = guard_memo(bad, alloc, esg, ["A", "B"], "aggressive")
    assert rep["status"] == "REPAIRED" and rep["violations"]
    w = {r["ticker"]: r["weight"] for r in memo["portfolio"]}
    assert w == alloc
    assert memo["expected_esg_score"] == pytest.approx(0.9 * 80 + 0.1 * 10, abs=0.1)
    assert memo["overall_confidence"] <= 1.0


def test_guard_rejects_unknown_ticker_and_nonfinite_weight():
    esg = {"A": {"greenwash_risk": 10, "esg_credibility": 80, "verdict": "credible"}}
    v = validate_weights({"A": 0.5, "HALLUCINATED": 0.5}, esg, ["A"], "moderate")
    assert any("not in the candidate universe" in x for x in v)
    v = validate_weights({"A": float("nan")}, esg, ["A"], "moderate")
    assert v


def test_guard_handles_garbage_memo():
    esg = {"A": {"greenwash_risk": 10, "esg_credibility": 80, "verdict": "credible"}}
    memo, rep = guard_memo("totally not json", {"A": 1.0}, esg, ["A"], "moderate")
    assert rep["status"] == "REPAIRED" and memo["portfolio"][0]["weight"] == 1.0


# ---------------- graph
def test_conflict_detection():
    v = _votes({"A": (80, 20, "likely_greenwashing", "bullish"), "B": (10, 90, "credible", "bearish"),
                "C": (10, 90, "credible", "bullish")})
    assert {c["ticker"] for c in find_conflicts(v)} == {"A", "B"}


def test_full_graph_debate_fires_and_state_is_kept():
    """Regression: undeclared state keys used to be silently dropped, so the debate never ran."""
    r = build_graph().invoke(initial_state("test", config.DEFAULT_CANDIDATES, 100_000, "moderate"))
    assert r["debate_rounds"] >= 1 and r["critiques"]
    assert r["optimizer_weights"] and r["guard_report"]
    w = {p["ticker"]: p["weight"] for p in r["final_memo"]["portfolio"]}
    assert math.isclose(sum(w.values()), 1.0, abs_tol=1e-3)
    assert w.get("XOM", 0) <= DIRTY_CAP + 1e-3


def test_debate_changes_the_vote():
    r = build_graph().invoke(initial_state("test", config.DEFAULT_CANDIDATES, 100_000, "moderate"))
    xom = [v for v in r["votes"] if v["agent"] == "market_analyst" and v["ticker"] == "XOM"][0]
    assert xom["payload"]["market_view"] != "bullish"
    assert r["disagreement"] == 0
