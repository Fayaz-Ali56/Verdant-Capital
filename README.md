# 🌿 Verdant Capital — Multi-Agent AI for Sustainable Finance

A multi-agent "AI boardroom" that evaluates sustainable investments:
an **ESG Verifier** (RAG-based greenwashing detection), a **Carbon & Market Analyst**
(price + carbon-credit forecasting), and a **Portfolio Optimizer**, coordinated by a
LangGraph orchestrator with a debate round on disagreement — plus a **Feedback Layer**
that re-weights agent influence based on measured accuracy.

## Quick start
```bash
pip install -r requirements.txt
cp .env.example .env        # add your OPENAI_API_KEY (or keep MOCK_MODE=true)
python -m data.fetch_market # pulls real prices + carbon-proxy data
python -m data.build_rag    # after dropping ESG PDFs into data_cache/pdfs/
python -m orchestrator.graph  # CLI smoke test
streamlit run app.py          # the demo
```

## Demo flow (4 min)
1. Enter mandate: capital, risk, "no greenwashing".
2. Watch the agents vote + the debate round live.
3. Final memo with evidence chain + allocation chart.
4. Show the feedback backtest: agent influence weights improving over time.

## Hackathon roadmap
- H0–3: setup + data flowing
- H3–10: RAG store + data pipelines
- H10–20: 3 agents producing strict JSON
- H20–28: orchestrator + debate loop
- H28–34: optimizer + feedback backtest
- H34–42: dashboard polish
- H42–48: rehearse, freeze, win.
