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

# ---- 💨 Carbon Intelligence (always visible once forecast exists) ----
import os
fc_path = os.path.join(config.DATA_DIR, "carbon_forecast.csv")
sum_path = os.path.join(config.DATA_DIR, "carbon_summary.json")
if os.path.exists(fc_path) and os.path.exists(sum_path):
    import plotly.graph_objects as go
    fc = pd.read_csv(fc_path, parse_dates=["ds"])
    with open(sum_path) as f:
        cs = json.load(f)
    st.subheader("💨 Carbon Intelligence — 30-Day Carbon-Credit Forecast")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Carbon proxy", cs["ticker"])
    c2.metric("Last price", f"${cs['last_price']}")
    c3.metric("30d forecast", f"${cs['forecast_30d']}", f"{cs['change_pct_30d']}%")
    c4.metric("Outlook", cs["outlook"].upper())
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_upper"], line=dict(width=0),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_lower"], line=dict(width=0),
                             fill="tonexty", name="80% band",
                             fillcolor="rgba(46, 204, 113, 0.2)"))
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat"], name="Forecast",
                             line=dict(color="#2ecc71", width=3)))
    split = fc["ds"].max() - pd.Timedelta(days=30)
    fig.add_vline(x=split, line_dash="dash", annotation_text="forecast →")
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    if cs.get("backtest_mape_pct"):
        st.caption(f"Model: {cs['engine']} · honest 30-day backtest error: ±{cs['backtest_mape_pct']}%")
else:
    st.info("Run `python -m data.carbon_forecast` to generate the carbon forecast.")

# ---- 📊 Adaptive Feedback Loop (backtest killshot) ----
tl_path = os.path.join(config.DATA_DIR, "feedback_timeline.json")
if os.path.exists(tl_path):
    import plotly.graph_objects as go
    tl = json.load(open(tl_path))["days"]
    st.subheader("📊 Adaptive Feedback Loop — Agents Get Smarter")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[d["day"] for d in tl], y=[d["esg_weight"] for d in tl],
                             name="ESG Verifier influence", line=dict(color="#2ecc71", width=3)))
    fig.add_trace(go.Scatter(x=[d["day"] for d in tl], y=[d["mkt_weight"] for d in tl],
                             name="Market Analyst influence", line=dict(color="#3498db", width=3,
                             dash="dash")))
    fig.update_layout(height=300, yaxis_title="influence weight",
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Day 5: ESG Verifier flagged XOM greenwashing before the market caught on — "
               "the loop measurably re-weighted agent influence.")
else:
    st.info("Run `python -m data.feedback_backtest` to generate the adaptive-weights timeline.")

# ---- 🧪 C02 Rare-Event Stress Test ----
c02_path = os.path.join(config.DATA_DIR, "c02_report.json")
if os.path.exists(c02_path) and os.path.exists(os.path.join(config.DATA_DIR, "c02_pr_curve.json")):
    import plotly.graph_objects as go
    r = json.load(open(c02_path))
    curve = json.load(open(os.path.join(config.DATA_DIR, "c02_pr_curve.json")))
    st.subheader("🧪 C02 — Severe Class Imbalance Stress Test (99:1 skew)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PR-AUC", f"{r['pr_auc']:.3f}", f"{round(r['pr_auc']/r['positive_rate'],1)}x baseline")
    c2.metric("Eval split", f"{r['eval_size']:,}", f"1% positives")
    c3.metric("Accuracy trap", f"{r['majority_class_accuracy_trap']:.0%}", "useless model")
    c4.metric("Lift @1% audit", f"{r['lift_over_random']}x")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=curve["recall"], y=curve["precision"], fill="tozeroy",
                             name="Our detector", line=dict(color="#e74c3c", width=3)))
    fig.add_hline(y=r["positive_rate"], line_dash="dot",
                  annotation_text="random-guess baseline (1%)")
    fig.update_layout(height=300, xaxis_title="recall", yaxis_title="precision",
                      margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.success(r["verdict"])
else:
    st.info("Run `python -m challenge.c02_rare_event` to generate the C02 stress-test evidence.")

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
