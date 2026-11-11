"""Verdant Capital — Multi-Agent Sustainable Investing (Dashboard v2)
Run: streamlit run app.py
"""
import json, os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import config

st.set_page_config(page_title="Verdant Capital", page_icon="🌿", layout="wide")

# ----------------------------- THEME -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');
html, body, [data-testid="stAppViewContainer"] {
    background: radial-gradient(1200px 600px at 80% -10%, #10331f 0%, #0a1a12 45%, #060d09 100%);
    color: #e8f5ec; font-family: 'Sora', sans-serif;
}
[data-testid="stSidebar"] { background: #0c1710; border-right: 1px solid #1f3d2b; }
h1, h2, h3 { font-family: 'Sora', sans-serif; }
.hero { padding: 1.2rem 1.5rem; border-radius: 18px; margin-bottom: 1rem;
    background: linear-gradient(100deg, rgba(46,204,113,.22), rgba(52,152,219,.12) 60%, transparent);
    border: 1px solid rgba(46,204,113,.35); }
.hero h1 { margin: 0; font-size: 2rem; font-weight: 800; }
.hero p { margin: .2rem 0 0; color: #9fd4b2; font-size: .95rem; }
.agent-card { border-radius: 14px; padding: .9rem 1rem; margin-bottom: .6rem;
    border: 1px solid #1f3d2b; background: rgba(20,40,28,.55); min-height: 150px; }
.agent-card h4 { margin: 0 0 .3rem; font-size: 1rem; }
.badge { display: inline-block; padding: .1rem .55rem; border-radius: 999px;
    font-size: .72rem; font-weight: 600; }
.badge-red { background: rgba(231,76,60,.25); color: #ff9d94; border: 1px solid #e74c3c66; }
.badge-green { background: rgba(46,204,113,.22); color: #7fe6a8; border: 1px solid #2ecc7166; }
.badge-amber { background: rgba(243,156,18,.22); color: #ffd28a; border: 1px solid #f39c1266; }
.confbar { height: 8px; border-radius: 6px; background: #14261b; overflow: hidden; margin-top: .4rem; }
.confbar > div { height: 100%; border-radius: 6px; }
.memo-box { border-radius: 16px; padding: 1.1rem 1.3rem; border: 1px solid #2ecc7144;
    background: rgba(15,35,22,.6); }
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { border-radius: 10px 10px 0 0; padding: .5rem 1.1rem;
    background: #0e1c13; border: 1px solid #1f3d2b; border-bottom: none; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🌿 Verdant Capital</h1>'
            '<p>An AI boardroom for sustainable investing — agents debate, evidence is cited, '
            'and the system remembers how its own calls performed.</p></div>', unsafe_allow_html=True)

AGENTS = {"esg_verifier": ("🌿", "ESG Verifier", "#2ecc71"),
          "market_analyst": ("📈", "Carbon & Market Analyst", "#3498db"),
          "optimizer": ("🎯", "Portfolio Optimizer", "#f39c12"),
          "cio": ("🏛️", "Chief Investment Officer", "#9b59b6")}

def verdict_badge(v):
    v = str(v).lower()
    cls = "badge-green" if any(k in v for k in ("credible", "bullish", "rising", "pass")) else \
          "badge-red" if any(k in v for k in ("greenwash", "bearish", "falling", "flag", "reject")) else "badge-amber"
    return f'<span class="badge {cls}">{v.upper()}</span>'

def agent_card(vote):
    emoji, name, color = AGENTS.get(vote["agent"], ("🤖", vote["agent"], "#888"))
    p = vote["payload"]
    headline = p.get("verdict") or p.get("market_view") or "vote"
    sub = p.get("reasoning") or p.get("evidence", [""])[0] or ""
    conf = vote.get("confidence", 0.5)
    st.markdown(f'<div class="agent-card"><h4>{emoji} {name} · {vote["ticker"]} {verdict_badge(headline)}</h4>'
                f'<div style="font-size:.82rem;color:#bfe6cd">{sub}</div>'
                f'<div class="confbar"><div style="width:{conf*100:.0f}%;background:{color}"></div></div>'
                f'<div style="font-size:.72rem;color:#7ba88c;margin-top:.15rem">confidence {conf:.0%}</div>'
                f'</div>', unsafe_allow_html=True)

# ----------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.header("🧭 Investment Mandate")
    capital = st.number_input("Capital (USD)", value=100_000, step=10_000)
    risk = st.selectbox("Risk profile", ["conservative", "moderate", "aggressive"])
    query = st.text_area("Mandate", "Max returns, low carbon exposure, no greenwashing")
    candidates = st.multiselect("Candidate assets", config.DEFAULT_CANDIDATES, config.DEFAULT_CANDIDATES)
    run = st.button("🚀 Convene the Boardroom", type="primary", use_container_width=True)
    st.caption("LLM provider: " + config.LLM_PROVIDER)

tab_board, tab_carbon, tab_learning, tab_lab = st.tabs(
    ["🧭 Boardroom", "💨 Carbon Intelligence", "📈 Adaptive Learning", "🛡️ Compliance Lab"])

# ============================= BOARDROOM =============================
with tab_board:
    if run:
        from orchestrator.graph import build_graph
        with st.spinner("Agents deliberating..."):
            result = build_graph().invoke({
                "query": query, "candidates": candidates, "capital": capital,
                "risk_profile": risk, "votes": [], "critiques": [], "debate_rounds": 0,
                "final_memo": None})
        if result.get("guard", {}).get("safe_mode"):
            st.error("🛡️ Data Quality Guard TRIGGERED — analysis suspended at low confidence.")
            for r in result["guard"]["rejections"] + result["guard"]["flags"]:
                st.warning(f"`{r['field']}` = {r['value']} → {r['rule']}")
        cols = st.columns(2)
        votes = result["votes"]
        for i, v in enumerate(votes):
            with cols[i % 2]:
                agent_card(v)
        if result.get("critiques"):
            st.subheader("⚔️ The Debate")
            for c in result["critiques"]:
                st.warning(c)
        st.subheader("🏛️ Final Investment Memo")
        memo = result["final_memo"]
        st.markdown(f'<div class="memo-box">', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Overall confidence", f"{memo.get('overall_confidence', 0):.0%}")
        m2.metric("Expected ESG score", memo.get("expected_esg_score", "—"))
        m3.metric("Residual risks", len(memo.get("residual_risks", [])))
        st.json(memo)
        st.markdown('</div>', unsafe_allow_html=True)
        port = pd.DataFrame(memo.get("portfolio", []))
        if not port.empty:
            fig = px.pie(port, names="ticker", values="weight", hole=0.45,
                         title="Optimized Allocation", color_discrete_sequence=px.colors.sequential.Greens_r)
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)
        with open(os.path.join(config.DATA_DIR, "last_run.json"), "w") as f:
            json.dump({"memo": memo, "votes": votes, "critiques": result.get("critiques", [])}, f, default=str)
    else:
        prev = os.path.join(config.DATA_DIR, "last_run.json")
        st.info("Set the mandate on the left, then press **🚀 Convene the Boardroom**.")
        if os.path.exists(prev):
            st.caption("Last boardroom session on file — re-run to refresh.")

# ============================= CARBON =============================
with tab_carbon:
    fc_path = os.path.join(config.DATA_DIR, "carbon_forecast.csv")
    sum_path = os.path.join(config.DATA_DIR, "carbon_summary.json")
    if os.path.exists(fc_path) and os.path.exists(sum_path):
        fc = pd.read_csv(fc_path, parse_dates=["ds"])
        cs = json.load(open(sum_path))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Carbon proxy", cs["ticker"])
        c2.metric("Last price", f"${cs['last_price']}")
        c3.metric("30d forecast", f"${cs['forecast_30d']}", f"{cs['change_pct_30d']}%")
        c4.metric("Outlook", cs["outlook"].upper())
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_upper"], line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_lower"], line=dict(width=0), fill="tonexty",
                                 name="80% band", fillcolor="rgba(46,204,113,.18)"))
        fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat"], name="Forecast", line=dict(color="#2ecc71", width=3)))
        fig.add_vline(x=fc["ds"].max() - pd.Timedelta(days=30), line_dash="dash", annotation_text="forecast →")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        if cs.get("backtest_mape_pct"):
            st.caption(f"Model: {cs['engine']} · honest 30-day backtest error: ±{cs['backtest_mape_pct']}%")
    else:
        st.info("Run `python -m data.carbon_forecast` to generate the carbon forecast.")

# ============================= LEARNING =============================
with tab_learning:
    tl_path = os.path.join(config.DATA_DIR, "feedback_timeline.json")
    if os.path.exists(tl_path):
        tl = json.load(open(tl_path))["days"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[d["day"] for d in tl], y=[d["esg_weight"] for d in tl],
                                 name="🌿 ESG Verifier influence", line=dict(color="#2ecc71", width=3)))
        fig.add_trace(go.Scatter(x=[d["day"] for d in tl], y=[d["mkt_weight"] for d in tl],
                                 name="📈 Market Analyst influence",
                                 line=dict(color="#3498db", width=3, dash="dash")))
        fig.update_layout(height=360, yaxis_title="influence weight",
                          margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Day 5: ESG Verifier flagged XOM greenwashing before the market caught on — "
                   "the feedback loop re-weighted agent influence.")
    else:
        st.info("Run `python -m data.feedback_backtest` to generate the timeline.")

# ============================= COMPLIANCE LAB =============================
with tab_lab:
    c02_path = os.path.join(config.DATA_DIR, "c02_report.json")
    st.markdown("#### 🧪 C02 — Severe Class Imbalance (99:1 Rare-Event Stress)")
    if os.path.exists(c02_path) and os.path.exists(os.path.join(config.DATA_DIR, "c02_pr_curve.json")):
        r = json.load(open(c02_path)); curve = json.load(open(os.path.join(config.DATA_DIR, "c02_pr_curve.json")))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PR-AUC (5 seeds)", f"{r['pr_auc_mean']:.3f} ± {r['pr_auc_std']:.3f}",
                  f"{round(r['pr_auc_mean']/r['positive_rate'],1)}x baseline")
        c2.metric("Eval split", r["methodology"].split(" x ")[1].split(" eval")[0], "1% positives")
        c3.metric("Accuracy trap", f"{r['majority_class_accuracy_trap']:.0%}", "useless model")
        c4.metric("Lift @1% audit", f"{r['lift_over_random']}x")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=curve["recall"], y=curve["precision"], fill="tozeroy",
                                 name="Our detector", line=dict(color="#e74c3c", width=3)))
        fig.add_hline(y=r["positive_rate"], line_dash="dot", annotation_text="random-guess baseline (1%)")
        fig.update_layout(height=300, xaxis_title="recall", yaxis_title="precision",
                          margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.success(r["verdict"])
    else:
        st.info("Run `python -m challenge.c02_rare_event`")

    st.divider()
    st.markdown("#### 🛡️ C04 — Out-of-Bounds & Hallucination Guard")
    c04_path = os.path.join(config.DATA_DIR, "c04_report.json")
    if os.path.exists(c04_path):
        r4 = json.load(open(c04_path))
        for c in r4["cases"]:
            icon = "🔴" if "REJECTED" in c["outcome"] else "🟡"
            with st.expander(f"{icon} {c['case']}"):
                st.json(c["payload"])
                st.write(c["outcome"])
                for d in c["detail"]["rejections"] + c["detail"]["flags"]:
                    st.caption(f"⚠️ `{d['field']}` = {d['value']} → {d['rule']}")
        st.success(r4["verdict"] + " The guard also runs live at the head of the orchestrator: corrupt "
                   "market feeds force safe-mode before any agent reasons on them.")
    else:
        st.info("Run `python -m challenge.c04_oob_guard`")
