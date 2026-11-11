"""LangGraph three-specialist investment boardroom and pure-Python test runner.

Specialists are ESG Verifier, Market Analyst, and Portfolio Optimizer.
Evidence review and memo writing are deterministic orchestration steps,
not extra investment agents. No real trades are placed.
"""

import json
import math
import re
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd

import config
from agents.llm import chat_json
from agents.prompts import ESG_VERIFIER_PROMPT
from data.carbon_forecast import carbon_summary
from data.demo import REPORTS, price_frame
from data.demo import evidence as demo_evidence
from data.feedback_store import agent_weights, save_recommendation
from data.fetch_market import load_cached_prices, price_stats
from data.portfolio import optimize


class AgentVote(TypedDict):
    agent: str
    ticker: str
    confidence: float
    payload: dict


class GraphState(TypedDict, total=False):
    query: str
    candidates: list[str]
    capital: float
    risk_profile: str
    mode: str
    event: str
    strict_esg: bool
    votes: list[AgentVote]
    esg_evidence: dict[str, list[dict]]
    market_snapshot: dict[str, Any]
    disagreements: list[dict]
    debate_rounds: int
    critiques: list[dict]
    agent_influence: dict[str, float]
    optimizer_weights: dict[str, float]
    portfolio_metrics: dict[str, Any]
    final_memo: dict[str, Any]
    run_id: int
    engine: str


def _defaults(given: dict) -> GraphState:
    mode = given.get("mode", "demo")
    if mode not in {"demo", "market"}:
        raise ValueError("Mode must be demo or market")
    requested = given.get("candidates", [])
    if not isinstance(requested, (list, tuple)) or len(requested) > 20:
        raise ValueError("Choose at most 20 candidate tickers")
    candidates = list(dict.fromkeys(str(t).strip().upper() for t in requested if str(t).strip()))
    if any(t == "CASH" or not re.fullmatch(r"[A-Z0-9][A-Z0-9.^=\-]{0,19}", t) for t in candidates):
        raise ValueError("Use valid tickers; CASH is reserved for unallocated capital")
    capital = float(given.get("capital", 100000))
    if not math.isfinite(capital) or not 0 <= capital <= 100_000_000:
        raise ValueError("Capital must be a finite USD amount between 0 and 100 million")
    if given.get("risk_profile", "moderate") not in {"conservative", "moderate", "aggressive"}:
        raise ValueError("Unknown risk profile")
    if not isinstance(given.get("strict_esg", True), bool):
        raise ValueError("Strict ESG must be a boolean")
    if not candidates:
        # The only permissible portfolio in an empty universe is cash.
        candidates = []
    return {
        "mode": mode,
        "event": given.get("event", "baseline") if mode == "demo" else "baseline",
        "query": given.get("query", "Sustainable capital allocation"),
        "capital": capital,
        "risk_profile": given.get("risk_profile", "moderate"),
        "strict_esg": bool(given.get("strict_esg", True)),
        "candidates": candidates,
        "votes": [],
        "esg_evidence": {},
        "market_snapshot": {},
        "disagreements": [],
        "debate_rounds": 0,
        "critiques": [],
        "agent_influence": {},
        "optimizer_weights": {},
        "portfolio_metrics": {},
        "final_memo": {},
    }


def _validated_llm_esg(ticker, excerpts):
    user = json.dumps({"ticker": ticker, "documents": excerpts}, ensure_ascii=False)
    response, provenance = chat_json(ESG_VERIFIER_PROMPT, user, purpose="esg")
    if not response:
        return None, provenance
    try:
        verdict = response["verdict"]
        risk = response.get("greenwash_risk")
        cred = response.get("esg_credibility")
        conf = float(response.get("confidence", 0))
        if verdict not in {"credible", "mixed", "likely_greenwashing", "unverified"}:
            raise ValueError("invalid verdict")
        if risk is not None and not (0 <= float(risk) <= 100):
            raise ValueError("invalid risk")
        if cred is not None and not (0 <= float(cred) <= 100):
            raise ValueError("invalid credibility")
        if not 0 <= conf <= 1:
            raise ValueError("invalid confidence")
        if response.get("ticker", ticker).upper() != ticker:
            raise ValueError("issuer mismatch")
        if not isinstance(response.get("reasoning"), str) or len(response["reasoning"]) > 8000:
            raise ValueError("invalid reasoning")
        flags = response.get("red_flags", [])
        if (
            not isinstance(flags, list)
            or len(flags) > 30
            or not all(isinstance(f, str) for f in flags)
        ):
            raise ValueError("invalid red flags")
        if verdict != "unverified" and (risk is None or cred is None or conf == 0):
            raise ValueError("An assessed verdict requires both scores and supported confidence")
        if verdict == "unverified":
            risk, cred, conf = None, None, 0.0
        # Don't allow the model to invent citations; only registered sources are forwarded.
        response["evidence"] = [e["citation"] for e in excerpts]
        response["greenwash_risk"] = round(float(risk), 2) if risk is not None else None
        response["esg_credibility"] = round(float(cred), 2) if cred is not None else None
        response["confidence"] = conf
        return response, provenance
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        return None, "invalid_model_schema"


def run_esg_verifier(state: GraphState) -> dict:
    votes = [v for v in state.get("votes", []) if v["agent"] != "esg_verifier"]
    evidence_map = {}
    for ticker in state.get("candidates", []):
        if state.get("mode") == "demo":
            excerpts = demo_evidence(ticker)
            fixture = REPORTS.get(ticker)
            if fixture:
                payload = {
                    "ticker": ticker,
                    "greenwash_risk": fixture["risk"],
                    "esg_credibility": fixture["credibility"],
                    "verdict": fixture["verdict"],
                    "confidence": fixture["confidence"],
                    "evidence": [entry["citation"] for entry in excerpts],
                    "red_flags": fixture["flags"],
                    "reasoning": "Synthetic scenario specification only.",
                    "provenance": "synthetic_fixture",
                }
            else:
                payload = None
        else:
            from data.build_rag import query

            excerpts = query(ticker)
            payload = None
            if excerpts:
                payload, provider = _validated_llm_esg(ticker, excerpts)
                if payload:
                    payload["provenance"] = f"uploaded_reports_and_{provider}"
        if payload is None:
            payload = {
                "ticker": ticker,
                "greenwash_risk": None,
                "esg_credibility": None,
                "verdict": "unverified",
                "confidence": 0.0,
                "evidence": [e["citation"] for e in excerpts] if excerpts else [],
                "red_flags": ["No independently verified ESG classification available"],
                "reasoning": "Insufficient authenticated evidence or valid ESG analysis.",
                "provenance": "unverified",
            }
        evidence_map[ticker] = excerpts
        votes.append(
            {
                "agent": "esg_verifier",
                "ticker": ticker,
                "confidence": float(payload["confidence"]),
                "payload": payload,
            }
        )
    return {"votes": votes, "esg_evidence": evidence_map}


def _market_prices(mode, tickers, event="baseline"):
    if mode == "demo":
        return price_frame(
            tickers, event=event
        ), f"SYNTHETIC generated market history / event={event}"
    prices = load_cached_prices()
    return (
        prices,
        "Historical market data via yfinance (cached)" if not prices.empty else "unavailable",
    )


def run_market_analyst(state: GraphState) -> dict:
    tickers = state.get("candidates", [])
    prices, source = _market_prices(
        state.get("mode", "demo"), tickers, event=state.get("event", "baseline")
    )
    stats = price_stats(prices) if not prices.empty else {}
    carbon = carbon_summary() if state.get("mode") == "market" else {}
    votes = [v for v in state.get("votes", []) if v["agent"] != "market_analyst"]
    for ticker in tickers:
        row = stats.get(ticker)
        if not row or row.get("return_30d_pct") is None:
            view, confidence, explanation = "neutral", 0.0, "No sufficient dated price history."
        else:
            pct = float(row["return_30d_pct"])
            view = "bullish" if pct > 2 else ("bearish" if pct < -2 else "neutral")
            confidence = 0.60 if row.get("observations", 0) >= 90 else 0.40
            explanation = f"Historical 30-session price change: {pct:+.2f}%; not a return forecast."
        forecast_available = carbon.get("outlook") in {"rising", "falling", "stable"}
        payload = {
            "ticker": ticker,
            "market_view": view,
            "carbon_outlook": carbon["outlook"] if forecast_available else "unavailable",
            "reasoning": explanation,
            "confidence": confidence,
            "evidence": ([f"Cached prices as of {row['as_of']}"] if row else [])
            + (
                [f"KRBN ETF proxy as of {carbon['market_data_as_of']}"]
                if forecast_available
                else []
            ),
            "price_stats": row,
            "provenance": source,
        }
        votes.append(
            {
                "agent": "market_analyst",
                "ticker": ticker,
                "confidence": float(confidence),
                "payload": payload,
            }
        )
    weights = agent_weights(
        db_path=(
            Path(config.DATA_DIR) / "simulation_feedback.db"
            if state.get("mode") == "demo"
            else config.FEEDBACK_DB
        ),
        allowed_sources={"synthetic_demo"} if state.get("mode") == "demo" else {"verified"},
    )
    return {
        "votes": votes,
        "market_snapshot": {
            "source": source,
            "stats": stats,
            "carbon": carbon,
            "mode": state.get("mode"),
        },
        "agent_influence": weights,
    }


def check_consensus(state: GraphState) -> dict:
    esg = {
        v["ticker"]: v["payload"] for v in state.get("votes", []) if v["agent"] == "esg_verifier"
    }
    market = {
        v["ticker"]: v["payload"] for v in state.get("votes", []) if v["agent"] == "market_analyst"
    }
    disputes = []
    for ticker, a in esg.items():
        b = market.get(ticker, {})
        flagged = a.get("verdict") == "likely_greenwashing" or (
            a.get("greenwash_risk") is not None and a["greenwash_risk"] > 60
        )
        if flagged and b.get("market_view") == "bullish":
            disputes.append(
                {
                    "ticker": ticker,
                    "conflict": "market_upside_vs_esg_risk",
                    "esg_verdict": a["verdict"],
                    "market_view": b["market_view"],
                }
            )
    return {"disagreements": disputes}


def route_consensus(state: GraphState) -> str:
    return (
        "critique"
        if (state.get("disagreements") and state.get("debate_rounds", 0) < config.MAX_DEBATE_ROUNDS)
        else "optimizer"
    )


def run_critique_round(state: GraphState) -> dict:
    """Evidence-grounded, constraint-based resolution; no invented counterfactual facts."""
    critiques = list(state.get("critiques", []))
    for case in state.get("disagreements", []):
        ticker = case["ticker"]
        excerpts = state.get("esg_evidence", {}).get(ticker, [])
        critiques.append(
            {
                "ticker": ticker,
                "round": int(state.get("debate_rounds", 0)) + 1,
                "esg_case": f"ESG concerns documented in {len(excerpts)} available excerpts.",
                "market_case": "Historical price momentum alone does not verify sustainability claims.",
                "resolution": "Apply quantitative ESG exclusions/caps before allocating capital.",
                "citation": [e["citation"] for e in excerpts[:3]],
                "residual_uncertainty": "Neither market momentum nor language alone establishes fraud.",
            }
        )
    return {"critiques": critiques, "debate_rounds": int(state.get("debate_rounds", 0)) + 1}


def run_optimizer(state: GraphState) -> dict:
    tickers = state.get("candidates", [])
    prices, _ = _market_prices(
        state.get("mode", "demo"), tickers, event=state.get("event", "baseline")
    )
    esg = {
        v["ticker"]: v["payload"] for v in state.get("votes", []) if v["agent"] == "esg_verifier"
    }
    result = optimize(
        tickers,
        prices,
        esg,
        state.get("risk_profile", "moderate"),
        strict_esg=state.get("strict_esg", True),
        influence=state.get("agent_influence", {}),
    )
    return {"optimizer_weights": result["weights"], "portfolio_metrics": result}


def run_synthesis(state: GraphState) -> dict:
    weights = state.get("optimizer_weights", {})
    esg = {
        v["ticker"]: v["payload"] for v in state.get("votes", []) if v["agent"] == "esg_verifier"
    }
    market = {
        v["ticker"]: v["payload"] for v in state.get("votes", []) if v["agent"] == "market_analyst"
    }
    portfolio = []
    for ticker, weight in weights.items():
        e = esg.get(ticker, {})
        m = market.get(ticker, {})
        reason = (
            "Unallocated capital retained to respect safety/ESG constraints."
            if ticker == "CASH"
            else f"ESG: {e.get('verdict', 'unverified')}; historical market: {m.get('market_view', 'unavailable')}."
        )
        portfolio.append(
            {
                "ticker": ticker,
                "weight": float(weight),
                "dollars": round(float(state.get("capital", 0)) * float(weight), 2),
                "rationale": reason,
                "evidence": e.get("evidence", []),
            }
        )
    score = sum(
        (v["weight"] * esg.get(v["ticker"], {}).get("esg_credibility", 0))
        for v in portfolio
        if esg.get(v["ticker"], {}).get("esg_credibility") is not None
    )
    denom = sum(
        v["weight"]
        for v in portfolio
        if esg.get(v["ticker"], {}).get("esg_credibility") is not None
    )
    # Deterministic policy codes explain screening/exclusion decisions.
    # SHAP in C06 explains the separate rare-event score, not this portfolio.
    audit = []
    caps = state.get("portfolio_metrics", {}).get("esg_caps", {})
    for entry in portfolio:
        ticker = entry["ticker"]
        detail = esg.get(ticker, {})
        cap = caps.get(ticker, 1.0)
        if ticker == "CASH":
            reason = "CASH_SAFETY_RESERVE"
        elif cap == 0 and (
            detail.get("verdict") == "likely_greenwashing"
            or (detail.get("greenwash_risk") is not None and detail["greenwash_risk"] > 60)
        ):
            reason = "EXCLUDED_HIGH_ESG_RISK"
        elif cap == 0:
            reason = "EXCLUDED_MISSING_PRICE_HISTORY"
        elif detail.get("verdict") == "unverified":
            reason = "LIMITED_UNVERIFIED_ESG"
        elif entry["weight"] > 1e-8:
            reason = "ALLOCATED_CONSTRAINT_VALIDATED"
        else:
            reason = "ZERO_OPTIMAL_WEIGHT"
        audit.append(
            {
                "ticker": ticker,
                "policy_reason": reason,
                "weight": entry["weight"],
                "citations": entry["evidence"],
                "esg_verdict": detail.get("verdict", "not_applicable"),
                "historical_market_view": market.get(ticker, {}).get(
                    "market_view", "not_applicable"
                ),
            }
        )
    memo = {
        "mode": state.get("mode", "demo"),
        "event": state.get("event", "baseline"),
        "query": state.get("query", ""),
        "capital": state.get("capital", 0),
        "risk_profile": state.get("risk_profile"),
        "agents": ["esg_verifier", "market_analyst", "portfolio_optimizer"],
        "portfolio": portfolio,
        "decision_audit": audit,
        "allocation_method": "SciPy optimizer; immutable numeric outputs",
        "expected_esg_score": round(score / denom, 2) if denom > 0 else None,
        "optimizer_metrics": state.get("portfolio_metrics", {}),
        "conflicts": state.get("disagreements", []),
        "evidence_review": state.get("critiques", []),
        "agent_influence": state.get("agent_influence", {}),
        "data_provenance": state.get("market_snapshot", {}),
        "disclaimers": [
            "Decision-support simulation; no orders placed.",
            "ESG claims are not independently certified by the application.",
            "Demo assets and disclosures are fictional."
            if state.get("mode") == "demo"
            else "Cached prices may be stale; unverified ESG claims remain unverified.",
        ],
        "created_utc": str(pd.Timestamp.now(tz="UTC")),
    }
    # Defense-in-depth: reject inconsistent output instead of hiding a solver failure.
    if abs(sum(item["weight"] for item in portfolio) - 1) > 1e-5:
        raise ValueError("Unsafe portfolio weights: allocation does not sum to 100%")
    if not set(weights).issubset(set(state.get("candidates", [])) | {"CASH"}):
        raise ValueError("Unrequested asset in allocation")
    return {"final_memo": memo}


def run_persist(state: GraphState) -> dict:
    result = save_recommendation(
        state.get("query", ""), state["final_memo"], mode=state.get("mode", "market")
    )
    return {"run_id": result}


def build_graph():
    """Real LangGraph orchestration, available once requirements are installed."""
    from langgraph.graph import END, StateGraph

    graph = StateGraph(GraphState)
    graph.add_node("esg_verifier", run_esg_verifier)
    graph.add_node("market_analyst", run_market_analyst)
    graph.add_node("check_consensus", check_consensus)
    graph.add_node("critique", run_critique_round)
    graph.add_node("portfolio_optimizer", run_optimizer)
    graph.add_node("synthesis", run_synthesis)
    graph.add_node("persist", run_persist)
    graph.set_entry_point("esg_verifier")
    graph.add_edge("esg_verifier", "market_analyst")
    graph.add_edge("market_analyst", "check_consensus")
    graph.add_conditional_edges(
        "check_consensus",
        route_consensus,
        {"critique": "critique", "optimizer": "portfolio_optimizer"},
    )
    graph.add_edge("critique", "check_consensus")
    graph.add_edge("portfolio_optimizer", "synthesis")
    graph.add_edge("synthesis", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


def run_pipeline(inputs, persist=True):
    """Dependency-light, deterministic equivalent for offline tests and rehearsals."""
    state = _defaults(inputs)
    for node in (run_esg_verifier, run_market_analyst, check_consensus):
        state.update(node(state))
    while route_consensus(state) == "critique":
        state.update(run_critique_round(state))
        state.update(check_consensus(state))
    state.update(run_optimizer(state))
    state.update(run_synthesis(state))
    if persist:
        state.update(run_persist(state))
    state["engine"] = "deterministic local pipeline"
    return state


if __name__ == "__main__":
    inputs = {
        "query": "Sustainable investment, avoid greenwashing",
        "mode": "demo",
        "candidates": config.DEMO_CANDIDATES,
        "capital": 100000,
        "risk_profile": "moderate",
        "strict_esg": True,
    }
    try:
        initial = _defaults(inputs)
        result = build_graph().invoke(initial)
        result["engine"] = "LangGraph"
    except ImportError:
        print("[runtime] LangGraph is not installed; using deterministic test runner")
        result = run_pipeline(inputs)
    print(json.dumps({"engine": result["engine"], "final_memo": result["final_memo"]}, indent=2))
