"""LangGraph orchestrator: agents vote -> consensus check -> DEBATE LOOP -> optimize -> CIO memo."""
import json, os
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

import config
from agents.prompts import (ESG_VERIFIER_PROMPT, MARKET_ANALYST_PROMPT,
                            SYNTHESIS_PROMPT, REBUTTAL_PROMPT)
from agents.llm import chat_json
from orchestrator.allocator import allocate, is_dirty
from orchestrator.guard import sanitize_payload, guard_memo


class AgentVote(TypedDict):
    agent: str
    ticker: str
    confidence: float
    payload: dict


class GraphState(TypedDict):
    query: str
    candidates: List[str]
    capital: float
    risk_profile: str
    votes: List[AgentVote]
    critiques: List[str]
    debate_rounds: int
    final_memo: Optional[dict]
    # every key a node returns MUST be declared here, or LangGraph silently drops it
    conflicts: List[dict]
    disagreement: int
    optimizer_weights: dict
    feedback_weights: dict
    guard_report: dict
    sanitize_issues: List[str]


# ------------------------------------------------ mock data (offline / fallback)
_MOCK_PROFILES = {
    "NEE":  {"greenwash_risk": 22, "esg_credibility": 81, "verdict": "credible",      "view": "bullish",  "conf": 0.82},
    "XOM":  {"greenwash_risk": 78, "esg_credibility": 35, "verdict": "likely_greenwashing", "view": "bullish", "conf": 0.88},
    "TSLA": {"greenwash_risk": 55, "esg_credibility": 60, "verdict": "mixed",         "view": "bearish",  "conf": 0.58},
    "ENPH": {"greenwash_risk": 30, "esg_credibility": 76, "verdict": "credible",      "view": "neutral",  "conf": 0.71},
    "ICLN": {"greenwash_risk": 15, "esg_credibility": 84, "verdict": "credible",      "view": "bullish",  "conf": 0.77},
    "VEST": {"greenwash_risk": 48, "esg_credibility": 58, "verdict": "mixed",         "view": "bearish",  "conf": 0.64},
}

def _mock_payload(agent_tag: str, ticker: str = "") -> dict:
    prof = _MOCK_PROFILES.get(ticker, {"greenwash_risk": 50, "esg_credibility": 55,
                                       "verdict": "mixed", "view": "neutral", "conf": 0.6})
    if agent_tag == "esg":
        return {"ticker": ticker, "greenwash_risk": prof["greenwash_risk"],
                "esg_credibility": prof["esg_credibility"], "verdict": prof["verdict"],
                "confidence": round(prof["conf"] * (0.6 if prof["greenwash_risk"] > 60 else 1.0), 2),
                "evidence": [f"[MOCK] {ticker}: evidence chunk from RAG store"],
                "red_flags": ["[MOCK] pledge without third-party verification"]
                             if prof["greenwash_risk"] > 50 else []}
    if agent_tag == "market":
        return {"ticker": ticker, "market_view": prof["view"], "carbon_outlook": "rising",
                "reasoning": f"[MOCK] carbon proxy up; {ticker} sensitivity per fetched stats.",
                "confidence": prof["conf"], "evidence": [f"[MOCK] {config.CARBON_TICKER} trend: +2.1% / 30d"]}
    if agent_tag == "rebuttal":
        keep = {"bullish": "neutral", "bearish": "neutral", "neutral": "neutral"}
        return {"ticker": ticker, "revised_view": keep[prof["view"]],
                "revised_confidence": round(prof["conf"] * 0.6, 2),
                "concession": f"[MOCK] Accepts the ESG challenge on {ticker}: transition/reputational "
                              f"risk is material, so the directional call is downgraded to neutral."}
    clean = [t for t, p in _MOCK_PROFILES.items() if p["greenwash_risk"] <= 60]
    dirty = [t for t, p in _MOCK_PROFILES.items() if p["greenwash_risk"] > 60]
    port = ([{"ticker": t, "weight": round(0.9 / len(clean), 3),
              "rationale": "[MOCK] credible ESG profile + supportive market view"} for t in clean] +
            [{"ticker": t, "weight": round(0.1 / max(len(dirty), 1), 3),
              "rationale": "[MOCK] capped at 10%: greenwash risk too high"} for t in dirty])
    return {"portfolio": port, "expected_esg_score": 74,
            "disagreements_resolved": ["[MOCK] XOM: market bullish vs ESG red flags -> capped at 10%"],
            "residual_risks": ["[MOCK] carbon forecast uncertainty"],
            "overall_confidence": 0.72}


# ------------------------------------------------ evidence loaders (degrade gracefully)
def _rag_evidence(ticker: str, k: int = 5) -> str:
    """Retrieve ESG evidence chunks from the RAG store. Empty string if store not built."""
    try:
        from data.build_rag import query
        chunks = query(f"{ticker} ESG sustainability carbon emissions net zero", k=k)
        return "\n".join(f"[{src}] {doc[:400]}" for doc, src in chunks)
    except Exception:
        return ""


def _market_stats() -> dict:
    path = os.path.join(config.DATA_DIR, "price_stats.json")
    stats = {}
    if os.path.exists(path):
        with open(path) as f:
            stats = json.load(f)
    try:
        from data.carbon_forecast import carbon_summary
        stats["_carbon_forecast"] = carbon_summary()
    except Exception:
        pass
    return stats


# ------------------------------------------------ nodes
def _upsert(votes, agent, ticker, payload):
    votes = [v for v in votes if not (v["agent"] == agent and v["ticker"] == ticker)]
    votes.append(AgentVote(agent=agent, ticker=ticker,
                           confidence=payload.get("confidence", 0.5), payload=payload))
    return votes


def run_esg_verifier(state: GraphState) -> dict:
    votes, issues = list(state.get("votes", [])), list(state.get("sanitize_issues", []))
    for ticker in state["candidates"]:
        evidence = _rag_evidence(ticker)
        msg = f"Company: {ticker}.\n\nRetrieved evidence:\n{evidence or '(no RAG store built — assess as unverified)'}"
        raw = chat_json(ESG_VERIFIER_PROMPT, msg, agent_tag="esg", ticker=ticker)
        payload, iss = sanitize_payload(raw, "esg", ticker)
        issues += iss
        votes = _upsert(votes, "esg_verifier", ticker, payload)
    return {"votes": votes, "sanitize_issues": issues}


def run_market_analyst(state: GraphState) -> dict:
    votes, issues = list(state.get("votes", [])), list(state.get("sanitize_issues", []))
    stats = _market_stats()
    carbon = json.dumps(stats.get("_carbon_forecast", {}))
    for ticker in state["candidates"]:
        msg = (f"Company: {ticker}.\n\nPrice statistics: {json.dumps(stats.get(ticker, {}))}\n"
               f"Carbon-market forecast: {carbon}")
        raw = chat_json(MARKET_ANALYST_PROMPT, msg, agent_tag="market", ticker=ticker)
        payload, iss = sanitize_payload(raw, "market", ticker)
        issues += iss
        votes = _upsert(votes, "market_analyst", ticker, payload)
    return {"votes": votes, "sanitize_issues": issues}


def find_conflicts(votes: List[AgentVote]) -> List[dict]:
    """A real disagreement = the two agents point in opposite directions on a ticker.
    (Comparing the two agents' raw confidence numbers is apples-to-oranges, so we don't.)"""
    esg = {v["ticker"]: v["payload"] for v in votes if v["agent"] == "esg_verifier"}
    mkt = {v["ticker"]: v["payload"] for v in votes if v["agent"] == "market_analyst"}
    out = []
    for t, e in esg.items():
        m = mkt.get(t)
        if not m:
            continue
        view = m.get("market_view")
        if is_dirty(e) and view == "bullish":
            out.append({"ticker": t, "kind": "bullish_on_greenwasher"})
        elif e.get("verdict") == "credible" and view == "bearish":
            out.append({"ticker": t, "kind": "bearish_on_credible"})
    return out


def check_consensus(state: GraphState) -> dict:
    conflicts = find_conflicts(state["votes"])
    return {"conflicts": conflicts, "disagreement": len(conflicts)}


def route_consensus(state: GraphState) -> str:
    if state.get("disagreement", 0) == 0:
        return "optimize"
    if state.get("debate_rounds", 0) >= config.MAX_DEBATE_ROUNDS:
        return "optimize"
    return "critique"


def run_critique_round(state: GraphState) -> dict:
    """The debate: ESG challenges the Market Analyst on each conflicted ticker; the analyst
    must hold or revise. The revised vote replaces the old one, so the debate changes the outcome."""
    votes = list(state["votes"])
    critiques = list(state.get("critiques", []))
    issues = list(state.get("sanitize_issues", []))
    rnd = state.get("debate_rounds", 0) + 1
    esg = {v["ticker"]: v["payload"] for v in votes if v["agent"] == "esg_verifier"}
    mkt = {v["ticker"]: v for v in votes if v["agent"] == "market_analyst"}
    for c in state.get("conflicts", []):
        t = c["ticker"]
        e, m = esg[t], mkt[t]["payload"]
        challenge = (f"ESG Verifier on {t}: verdict={e.get('verdict')}, greenwash_risk={e.get('greenwash_risk')}, "
                     f"red_flags={e.get('red_flags')}, evidence={e.get('evidence')}.")
        mine = (f"Your current view on {t}: {m.get('market_view')} "
                f"(confidence {m.get('confidence')}), reasoning: {m.get('reasoning')}")
        reb = chat_json(REBUTTAL_PROMPT, f"{challenge}\n\n{mine}", agent_tag="rebuttal", ticker=t)
        new_view = reb.get("revised_view", m.get("market_view")) if isinstance(reb, dict) else m.get("market_view")
        new_conf = reb.get("revised_confidence", m.get("confidence")) if isinstance(reb, dict) else m.get("confidence")
        revised, iss = sanitize_payload({**m, "market_view": new_view, "confidence": new_conf}, "market", t)
        issues += iss
        votes = _upsert(votes, "market_analyst", t, revised)
        changed = revised["market_view"] != m.get("market_view")
        outcome = (f"Market Analyst revised {m.get('market_view')} → {revised['market_view']} "
                   f"({m.get('confidence', 0):.0%} → {revised['confidence']:.0%})") if changed \
            else f"Market Analyst held {m.get('market_view')}"
        why = (reb or {}).get("concession", "") if isinstance(reb, dict) else ""
        critiques.append(f"[round {rnd}] ⚔️ {t}: ESG={e.get('verdict')} (risk {e.get('greenwash_risk')}) vs "
                         f"market={m.get('market_view')}. {outcome}. {why}")
    return {"votes": votes, "critiques": critiques, "debate_rounds": rnd, "sanitize_issues": issues}


def run_optimizer(state: GraphState) -> dict:
    """Feedback-weighted, volatility-adjusted allocation with hard constraints (see allocator.py)."""
    try:
        import data.feedback_store as fb
        fw = fb.agent_weights()
    except Exception:
        fw = {"esg_verifier": 1.0, "market_analyst": 1.0}
    stats = _market_stats()
    weights = allocate(state["votes"], state.get("risk_profile", "moderate"), fw, stats)
    return {"optimizer_weights": weights, "feedback_weights": fw}


def run_synthesis(state: GraphState) -> dict:
    user_msg = (f"Query: {state['query']}. Capital: {state['capital']}. "
                f"Risk: {state['risk_profile']}. Votes: {json.dumps(state['votes'])}. "
                f"Critiques: {state.get('critiques')}. Weights: {state.get('optimizer_weights')}.")
    memo = chat_json(SYNTHESIS_PROMPT, user_msg, agent_tag="cio")
    esg = {v["ticker"]: v["payload"] for v in state["votes"] if v["agent"] == "esg_verifier"}
    memo, report = guard_memo(memo, state["optimizer_weights"], esg,
                              state["candidates"], state.get("risk_profile", "moderate"))
    return {"final_memo": memo, "guard_report": report}


def build_graph():
    g = StateGraph(GraphState)
    g.add_node("esg_verifier", run_esg_verifier)
    g.add_node("market_analyst", run_market_analyst)
    g.add_node("check_consensus", check_consensus)
    g.add_node("critique", run_critique_round)
    g.add_node("optimizer", run_optimizer)
    g.add_node("synthesize", run_synthesis)
    g.set_entry_point("esg_verifier")
    g.add_edge("esg_verifier", "market_analyst")
    g.add_edge("market_analyst", "check_consensus")
    g.add_conditional_edges("check_consensus", route_consensus,
                            {"critique": "critique", "optimize": "optimizer"})
    g.add_edge("critique", "check_consensus")      # re-check after the debate
    g.add_edge("optimizer", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


def initial_state(query, candidates, capital, risk_profile):
    return {"query": query, "candidates": list(candidates), "capital": capital,
            "risk_profile": risk_profile, "votes": [], "critiques": [], "debate_rounds": 0,
            "final_memo": None, "conflicts": [], "disagreement": 0, "optimizer_weights": {},
            "feedback_weights": {}, "guard_report": {}, "sanitize_issues": []}


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke(initial_state("Invest sustainably, low carbon exposure, no greenwashing",
                                        config.DEFAULT_CANDIDATES, 100_000, "moderate"))
    print("debate rounds:", result["debate_rounds"])
    for c in result["critiques"]:
        print(" ", c)
    print("guard:", result["guard_report"].get("status"), result["guard_report"].get("violations"))
    print(json.dumps(result["final_memo"], indent=2))
