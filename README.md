# 🌿 Verdant Capital — Multi-Agent AI for Sustainable Finance

A multi-agent "AI boardroom" that evaluates sustainable investments:
an **ESG Verifier** (RAG-based greenwashing detection), a **Carbon & Market Analyst**
(price + carbon-credit forecasting), and a **Portfolio Optimizer**, coordinated by a
LangGraph orchestrator with a debate round on disagreement — plus a **Feedback Layer**
that re-weights agent influence based on measured accuracy.

## Quick start
```bash
pip install -r requirements.txt
pip install scikit-learn   # C02 harness dependency
cp .env.example .env        # paste your GEMINI_API_KEY (aistudio.google.com/apikey)
# optional backup brain: OPENROUTER_API_KEY (free, no card: openrouter.ai/keys)
# LLM_PROVIDER=auto  -> Gemini -> OpenRouter free -> mock (never crashes a demo)
python -m data.fetch_market # pulls real prices + carbon-proxy data
python -m data.build_rag    # after dropping ESG PDFs into data_cache/pdfs/
python -m orchestrator.graph  # CLI smoke test
python -m data.carbon_forecast # carbon forecast + honest backtest
python -m data.feedback_backtest # 30-day adaptive-weights timeline
python -m challenge.c02_rare_event # C02 99:1 rare-event stress evidence
streamlit run app.py          # the demo
```

## Tests (no API keys needed)
```bash
LLM_PROVIDER=mock python -m pytest -q     # 13 tests: allocator, guard, debate, regression
```

## What's real vs simulated (say this out loud to judges)
| Piece | Status |
|---|---|
| Market prices, carbon-proxy forecast + holdout MAPE | Real (yfinance), needs internet |
| ESG verdicts | Real LLM over RAG evidence **if** you add ESG PDFs; otherwise "unverified" |
| Debate, allocator, output guard | Real, deterministic, tested |
| Feedback-loop history chart | **Simulated scenario** (scripted hit-rates) |
| C02 rare-event evidence | **Synthetic data** (harness + imbalance handling, not real-world accuracy) |

See `DEMO.md` for the full 4-minute script.

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
