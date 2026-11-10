"""LangGraph orchestrator: agents vote -> consensus check -> DEBATE LOOP -> optimize -> CIO memo."""
import json, os
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

import config
from agents.prompts import ESG_VERIFIER_PROMPT, MARKET_ANALYST_PROMPT, SYNTHESIS_PROMPT
from agents.llm import chat_json


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
def run_esg_verifier(state: GraphState) -> dict:
    votes = [v for v in state.get("votes", []) if v["agent"] != "esg_verifier"]
    for ticker in state["candidates"]:
        evidence = _rag_evidence(ticker)
        msg = f"Company: {ticker}.\n\nRetrieved evidence:\n{evidence or '(no RAG store built — assess as unverified)'}"
        payload = chat_json(ESG_VERIFIER_PROMPT, msg, agent_tag="esg", ticker=ticker)
        votes.append(AgentVote(agent="esg_verifier", ticker=ticker,
                               confidence=payload.get("confidence", 0.5), payload=payload))
    return {"votes": votes}


def run_market_analyst(state: GraphState) -> dict:
    votes = [v for v in state.get("votes", []) if v["agent"] != "market_analyst"]
    stats = _market_stats()
    for ticker in state["candidates"]:
        msg = f"Company: {ticker}.\n\nPrice statistics: {json.dumps(stats.get(ticker, {}))}"
        payload = chat_json(MARKET_ANALYST_PROMPT, msg, agent_tag="market", ticker=ticker)
        votes.append(AgentVote(agent="market_analyst", ticker=ticker,
                               confidence=payload.get("confidence", 0.5), payload=payload))
    return {"votes": votes}


def check_consensus(state: GraphState) -> dict:
    by_ticker = {}
    for v in state["votes"]:
        by_ticker.setdefault(v["ticker"], []).append(v["confidence"])
    spreads = {t: max(cs) - min(cs) for t, cs in by_ticker.items() if len(cs) > 1}
    return {"disagreement": max(spreads.values()) if spreads else 0.0}


def route_consensus(state: GraphState) -> str:
    if state.get("disagreement", 0) <= config.DISAGREEMENT_THRESHOLD:
        return "optimize"
    if state.get("debate_rounds", 0) >= config.MAX_DEBATE_ROUNDS:
        return "optimize"
    return "critique"


def run_critique_round(state: GraphState) -> dict:
    """Only genuinely conflicting tickers enter the debate."""
    votes = list(state["votes"])
    critiques = list(state.get("critiques", []))
    esg = {v["ticker"]: v for v in votes if v["agent"] == "esg_verifier"}
    mkt = {v["ticker"]: v for v in votes if v["agent"] == "market_analyst"}
    for ticker in esg:
        gap = abs(esg[ticker]["confidence"] - mkt[ticker]["confidence"])
        verdict = esg[ticker]["payload"].get("verdict", "")
        view = mkt[ticker]["payload"].get("market_view", "")
        if (gap > config.DISAGREEMENT_THRESHOLD
                or ("greenwashing" in verdict and view == "bullish")
                or (verdict == "credible" and view == "bearish")):
            critiques.append(
                f"[round {state.get('debate_rounds', 0) + 1}] ⚔️ {ticker}: "
                f"ESG verdict={verdict} (conf {esg[ticker]['confidence']:.0%}) vs "
                f"market view={view} (conf {mkt[ticker]['confidence']:.0%})")
    return {"critiques": critiques,
            "debate_rounds": state.get("debate_rounds", 0) + 1}


def run_optimizer(state: GraphState) -> dict:
    """Hard constraint: greenwash-risk > 60 assets capped at 10% total. Swap in PyPortfolioOpt later."""
    esg = {v["ticker"]: v for v in state["votes"] if v["agent"] == "esg_verifier"}
    clean = [t for t, v in esg.items() if v["payload"].get("greenwash_risk", 0) <= 60]
    dirty = [t for t, v in esg.items() if v["payload"].get("greenwash_risk", 0) > 60]
    weights = {}
    if clean:
        for t in clean:
            weights[t] = 0.9 / len(clean)
    for t in dirty:
        weights[t] = 0.1 / max(len(dirty), 1)
    return {"optimizer_weights": weights}


def run_synthesis(state: GraphState) -> dict:
    user_msg = (f"Query: {state['query']}. Capital: {state['capital']}. "
                f"Risk: {state['risk_profile']}. Votes: {json.dumps(state['votes'])}. "
                f"Critiques: {state.get('critiques')}. Weights: {state.get('optimizer_weights')}.")
    return {"final_memo": chat_json(SYNTHESIS_PROMPT, user_msg, agent_tag="cio")}


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
    g.add_edge("critique", "esg_verifier")
    g.add_edge("optimizer", "synthesize")
    g.add_edge("synthesize", END)
    return g.compile()


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke({
        "query": "Invest sustainably, low carbon exposure, no greenwashing",
        "candidates": config.DEFAULT_CANDIDATES,
        "capital": 100_000, "risk_profile": "moderate",
        "votes": [], "critiques": [], "debate_rounds": 0, "final_memo": None,
    })
    print(json.dumps(result["final_memo"], indent=2))
