"""Verdant Capital — Streamlit dashboard. Run: streamlit run app.py"""
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import config
from orchestrator.graph import build_graph

st.set_page_config(page_title="Verdant Capital", page_icon="🌿", layout="wide")
st.title("🌿 Verdant Capital — Multi-Agent Sustainable Investing")
st.caption("ESG Verifier · Carbon & Market Analyst · Portfolio Optimizer · CIO Synthesis · Feedback Loop")

with st.sidebar:
    st.header("Investment Mandate")
    capital = st.number_input("Capital (USD)", value=100_000, step=10_000)
    risk = st.selectbox("Risk profile", ["conservative", "moderate", "aggressive"])
    query = st.text_area("Mandate", "Max returns, low carbon exposure, no greenwashing")
    candidates = st.multiselect("Candidate assets", config.DEFAULT_CANDIDATES, config.DEFAULT_CANDIDATES)
    run = st.button("🚀 Convene the Boardroom", type="primary")

if run:
    graph = build_graph()
    with st.spinner("Agents deliberating..."):
        result = graph.invoke({
            "query": query, "candidates": candidates, "capital": capital,
            "risk_profile": risk, "votes": [], "critiques": [], "debate_rounds": 0,
            "final_memo": None,
        })

    st.subheader("🗳️ Agent Votes")
    for v in result["votes"]:
        with st.expander(f"{v['agent'].replace('_',' ').title()} — {v['ticker']} "
                         f"(confidence {v['confidence']:.0%})"):
            st.json(v["payload"])

    if result.get("critiques"):
        st.subheader("⚔️ The Debate")
        for c in result["critiques"]:
            st.warning(c)

    st.subheader("📋 Final Investment Memo")
    memo = result["final_memo"]
    st.json(memo)

    port = pd.DataFrame(memo.get("portfolio", []))
    if not port.empty:
        fig = px.pie(port, names="ticker", values="weight", hole=0.4,
                     title="Optimized Allocation")
        st.plotly_chart(fig, use_container_width=True)

    st.info("💾 Recommendation logged to the Feedback Layer — outcomes will re-weight agent influence.")
