"""LangGraph orchestrator: runs agents, detects disagreement, runs critique round, synthesizes.

Flow:
  START -> esg_verifier -> market_analyst -> check_consensus
       consensus OK -> optimizer -> synthesize -> END
       disagreement  -> critique round (agents see each other) -> back to check
"""
import json
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

import config
from agents.prompts import ESG_VERIFIER_PROMPT, MARKET_ANALYST_PROMPT, SYNTHESIS_PROMPT


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


# ---------------------------------------------------------------- LLM helpers
def _llm_json(system_prompt: str, user_msg: str, agent_tag: str, ticker: str = "") -> dict:
    """Call the LLM and parse strict JSON. Falls back to mock data if MOCK_MODE."""
    if config.MOCK_MODE:
        return _mock_payload(agent_tag, ticker)
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=config.OPENAI_API_KEY)
    resp = llm.invoke(
        [{"role": "system", "content": system_prompt},
         {"role": "user", "content": user_msg + "\n\nRespond with STRICT JSON only."}]
    )
    text = resp.content.strip().removeprefix("```json").removesuffix("```")
    return json.loads(text)


# Deterministic per-ticker mock profiles so the demo shows REAL disagreement.
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
    # synthesis
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


# ---------------------------------------------------------------- Nodes
def run_esg_verifier(state: GraphState) -> dict:
    votes = [v for v in state.get("votes", []) if v["agent"] != "esg_verifier"]
    for ticker in state["candidates"]:
        payload = _llm_json(ESG_VERIFIER_PROMPT,
                            f"Company: {ticker}. Evidence: (plug in RAG retrieval here)",
                            agent_tag="esg", ticker=ticker)
        votes.append(AgentVote(agent="esg_verifier", ticker=ticker,
                               confidence=payload.get("confidence", 0.5), payload=payload))
    return {"votes": votes}


def run_market_analyst(state: GraphState) -> dict:
    votes = [v for v in state.get("votes", []) if v["agent"] != "market_analyst"]
    for ticker in state["candidates"]:
        payload = _llm_json(MARKET_ANALYST_PROMPT,
                            f"Company: {ticker}. Price stats: (plug in fetch_market stats here)",
                            agent_tag="market", ticker=ticker)
        votes.append(AgentVote(agent="market_analyst", ticker=ticker,
                               confidence=payload.get("confidence", 0.5), payload=payload))
    return {"votes": votes}


def check_consensus(state: GraphState) -> dict:
    """Spread of per-ticker confidences across agents -> disagreement score."""
    by_ticker = {}
    for v in state["votes"]:
        by_ticker.setdefault(v["ticker"], []).append(v["confidence"])
    spreads = {t: max(cs) - min(cs) for t, cs in by_ticker.items() if len(cs) > 1}
    state["disagreement"] = max(spreads.values()) if spreads else 0.0
    return state


def route_consensus(state: GraphState) -> str:
    if state.get("disagreement", 0) <= config.DISAGREEMENT_THRESHOLD:
        return "optimize"
    if state.get("debate_rounds", 0) >= config.MAX_DEBATE_ROUNDS:
        return "optimize"
    return "critique"


def run_critique_round(state: GraphState) -> dict:
    """Each agent re-evaluates seeing the other's verdict — the debate moment."""
    votes = list(state["votes"])
    critiques = list(state.get("critiques", []))
    esg = {v["ticker"]: v for v in votes if v["agent"] == "esg_verifier"}
    mkt = {v["ticker"]: v for v in votes if v["agent"] == "market_analyst"}
    for ticker in esg:
        conf_gap = abs(esg[ticker]["confidence"] - mkt[ticker]["confidence"])
        verdict = esg[ticker]["payload"].get("verdict", "")
        view = mkt[ticker]["payload"].get("market_view", "")
        conflict = (conf_gap > config.DISAGREEMENT_THRESHOLD
                    or ("greenwashing" in verdict and view == "bullish")
                    or (verdict == "credible" and view == "bearish"))
        if conflict:
            critiques.append(
                f"[round {state.get('debate_rounds',0)+1}] ⚔️ {ticker}: "
                f"ESG verdict={verdict} (conf {esg[ticker]['confidence']:.0%}) vs "
                f"market view={view} (conf {mkt[ticker]['confidence']:.0%})"
            )
    return {"critiques": critiques,
            "debate_rounds": state.get("debate_rounds", 0) + 1}


def run_optimizer(state: GraphState) -> dict:
    """Simple constraint pass: cap greenwashed assets at 10%. Swap for PyPortfolioOpt later."""
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
    memo = _llm_json(SYNTHESIS_PROMPT, user_msg, agent_tag="cio")
    return {"final_memo": memo}


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
    g.add_edge("critique", "esg_verifier")   # debate loop back
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
