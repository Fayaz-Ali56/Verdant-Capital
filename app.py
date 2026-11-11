"""Verdant Capital — Streamlit dashboard. Run: streamlit run app.py"""
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import config
from orchestrator.graph import build_graph, initial_state
import data.feedback_store as fb

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
    st.caption("⚠️ SIMULATED SCENARIO — " + json.load(open(tl_path)).get(
        "story", "agent hit-rates are scripted to demonstrate the re-weighting mechanism."))
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
    c1.metric("PR-AUC (5-seed mean)", f"{r['pr_auc_mean']:.3f}",
              f"± {r['pr_auc_std']:.3f} · {round(r['pr_auc_mean']/r['positive_rate'])}x random")
    c2.metric("Eval split", f"{r['eval_size']:,}", f"{r.get('positives_per_eval', 50)} positives (1%)")
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
    st.caption("⚠️ " + r.get("data_source", "Synthetic data."))
else:
    st.info("Run `python -m challenge.c02_rare_event` to generate the C02 stress-test evidence.")

with st.sidebar:
    st.header("Investment Mandate")
    capital = st.number_input("Capital (USD)", value=100_000, step=10_000)
    risk = st.selectbox("Risk profile", ["conservative", "moderate", "aggressive"])
    query = st.text_area("Mandate", "Max returns, low carbon exposure, no greenwashing")
    candidates = st.multiselect("Candidate assets", config.DEFAULT_CANDIDATES, config.DEFAULT_CANDIDATES)
    run = st.button("🚀 Convene the Boardroom", type="primary")

def _live_llm() -> bool:
    return config.LLM_PROVIDER != "mock" and bool(config.GEMINI_API_KEY or config.OPENROUTER_API_KEY)

if run:
    if not _live_llm():
        st.warning("🧪 MOCK MODE — no LLM key found (or LLM_PROVIDER=mock). Agent outputs below are "
                   "canned demo data, not real analysis. Add GEMINI_API_KEY to .env for live agents.")
    graph = build_graph()
    with st.spinner("Agents deliberating..."):
        result = graph.invoke(initial_state(query, candidates, capital, risk))

    st.subheader("🗳️ Agent Votes")
    for v in result["votes"]:
        with st.expander(f"{v['agent'].replace('_',' ').title()} — {v['ticker']} "
                         f"(confidence {v['confidence']:.0%})"):
            st.json(v["payload"])

    st.subheader("⚔️ The Debate")
    if result.get("critiques"):
        for c in result["critiques"]:
            st.warning(c)
    else:
        st.success("Agents were aligned on every ticker — no debate needed.")

    fw = result.get("feedback_weights", {})
    if fw:
        st.caption(f"Feedback-loop influence used in allocation: ESG Verifier ×{fw.get('esg_verifier', 1.0)}, "
                   f"Market Analyst ×{fw.get('market_analyst', 1.0)} "
                   f"(weights currently derive from the simulated backtest above).")

    st.subheader("📋 Final Investment Memo")
    memo = result["final_memo"]
    port = pd.DataFrame(memo.get("portfolio", []))
    if not port.empty:
        port["amount_usd"] = (port["weight"] * capital).round(0)
        left, right = st.columns([3, 2])
        with left:
            st.dataframe(port[["ticker", "weight", "amount_usd", "rationale"]],
                         use_container_width=True, hide_index=True)
        with right:
            st.plotly_chart(px.pie(port, names="ticker", values="weight", hole=0.4,
                                   title="Optimized Allocation"), use_container_width=True)
    m1, m2 = st.columns(2)
    m1.metric("Portfolio ESG credibility (recomputed)", memo.get("expected_esg_score"))
    m2.metric("Overall confidence", f"{memo.get('overall_confidence', 0):.0%}")
    with st.expander("Disagreements resolved / residual risks"):
        st.write("**Resolved:**", memo.get("disagreements_resolved", []))
        st.write("**Residual risks:**", memo.get("residual_risks", []))

    gr = result.get("guard_report", {})
    st.subheader("🛡️ Output Guard")
    if gr.get("status") == "PASSED":
        st.success("PASSED — the memo's portfolio satisfied every constraint as written by the LLM.")
    else:
        st.info("REPAIRED — the LLM's portfolio broke a rule, so the constrained allocator's weights "
                "were used instead: " + "; ".join(gr.get("violations", [])))
    st.caption("Checks: " + " · ".join(gr.get("checks_run", [])))
    if result.get("sanitize_issues"):
        with st.expander(f"{len(result['sanitize_issues'])} agent output(s) were out of range and clamped"):
            for i in result["sanitize_issues"]:
                st.write("•", i)

    rec_id = fb.save_recommendation(query, memo)
    st.info(f"💾 Recommendation #{rec_id} saved to the Feedback Layer. "
            "Real 30-day outcomes aren't recorded yet, so live weights don't change until they are.")
