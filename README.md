# 🌿 Verdant Capital — Multi-Agent AI for Sustainable Finance

**An AI boardroom for sustainable investing.** Specialized agents debate every
investment, evidence is cited, corrupt data is refused, and a feedback layer
re-weights agent influence based on measured accuracy.

> Challenge entry: **Battle of Intelligence — C02 (Severe Class Imbalance)**
> with C04 (Out-of-Bounds Guard) built in. Mission: Sustainable Finance & Multi-Agent AI.

---

## 🏗️ Architecture

```
                    ┌──────────────────────────────────────┐
                    │  🛡️ GUARD (C04) — screens all data   │  reject → safe mode
                    └──────────────────┬───────────────────┘
                                     ▼
   ┌───────────────┐   ┌──────────────────────┐   ┌──────────────────┐
   │ 🌿 ESG Verifier│   │ 📈 Carbon & Market    │   │ 🎯 Portfolio      │
   │ RAG evidence,  │   │ Analyst — real prices │   │ Optimizer — caps  │
   │ greenwash score│   │ + carbon forecast     │   │ greenwashed @10%  │
   └───────┬───────┘   └──────────┬───────────┘   └────────┬─────────┘
           └──────────┬───────────┴────────────────────────┘
                      ▼
        ┌─────────────────────────────┐     disagreement > 15%?
        │ Orchestrator (LangGraph)    │ ──► ⚔️ DEBATE ROUND (max 2)
        └─────────────┬───────────────┘
                      ▼
        ┌─────────────────────────────┐
        │ 🏛️ CIO Synthesis — memo with │  citations, residual risks,
        │ evidence chain + allocation  │  honest confidence
        └─────────────┬───────────────┘
                      ▼
        ┌─────────────────────────────┐
        │ 📊 FEEDBACK LAYER (SQLite)   │  outcomes → accuracy →
        │ 30-day backtest timeline     │  agent influence weights
        └─────────────────────────────┘
```

## 📁 File Map

| Path | What it does |
|---|---|
| `app.py` | Streamlit dashboard (dark theme, 4 tabs: Boardroom / Carbon / Learning / Compliance Lab) |
| `config.py` | All knobs: LLM provider, tickers, thresholds |
| `agents/prompts.py` | Strict-JSON prompts for the 3 agents + CIO synthesis |
| `agents/llm.py` | Provider chain: **Gemini → OpenRouter free → mock**, disk-cached, never crashes a demo |
| `orchestrator/graph.py` | LangGraph: guard → agents → consensus → debate loop → optimizer → synthesis |
| `data/fetch_market.py` | Real prices + carbon proxy (KRBN) via yfinance |
| `data/carbon_forecast.py` | Prophet forecast + linear fallback + honest 30d backtest (MAPE) |
| `data/build_rag.py` | ESG PDFs → ChromaDB with cited retrieval |
| `data/feedback_store.py` | SQLite feedback layer → accuracy-weighted agent influence |
| `data/feedback_backtest.py` | Seeds 30 days → adaptive-weights timeline |
| `challenge/c02_rare_event.py` | 99:1 skew stress test, 5 seeds, PR-AUC evidence |
| `challenge/c04_oob_guard.py` | Out-of-bounds validation, 5 mandated edge cases + live guard |

## 🚀 Setup & Run (in order)

```bash
pip install -r requirements.txt
cp .env.example .env                 # paste GEMINI_API_KEY (aistudio.google.com/apikey)
                                     # optional backup: OPENROUTER_API_KEY (free, no card)

python -m data.fetch_market          # 1. real market + carbon data
python -m data.carbon_forecast       # 2. carbon forecast + backtest chart data
python -m data.feedback_backtest     # 3. 30-day adaptive-weights timeline
python -m challenge.c02_rare_event   # 4. C02 evidence (PR-AUC report)
python -m challenge.c04_oob_guard    # 5. C04 evidence (5 boundary cases)
streamlit run app.py                 # 🚀 the demo
```

**No API key?** Set `LLM_PROVIDER=mock` in `.env` — the entire pipeline runs offline
with labeled mock data. The dashboard ships with pre-generated evidence files.

## 🔑 Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `GEMINI_API_KEY` | — | Your primary brain (Google AI Studio, free tier) |
| `OPENROUTER_API_KEY` | — | Fallback brain (free key, no card). Free tier ≈20 req/min, ~50 req/day at $0 balance |
| `LLM_PROVIDER` | `auto` | `auto` → Gemini → OpenRouter → mock. `mock` forces offline |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Fast, strong structured output |

## 🎯 Challenge Evidence

### C02 — Severe Class Imbalance / Rare-Event Stress
- Greenwashing modeled as a **<1% positive rate** detection problem (25k samples, 1% positives)
- **Isolation Forest** anomaly detector, unsupervised fit (labels are scarce in reality)
- **5 seeds × 5,000 eval samples** → PR-AUC **0.958 ± 0.021** vs 0.010 random baseline
- The **accuracy trap is explicit**: approve-everything = 99% accuracy, zero value → we report PR-AUC
- Deployment-realistic metric: at a 1% audit budget, **~90% of flagged cases are true fraud (90× lift)**

### C04 — Out-of-Bounds & Hallucination Guard
- 5 mandated edge cases: negative solar irradiance, 200% carbon offsets, invalid lat/lon, corrupt price feed, confidence = 1.7
- **All 5 intercepted**: REJECTED (agents never see the data) or FLAGGED (forced low-confidence mode)
- The guard runs **live at the head of the orchestrator** — poison the price feed in
  `data_cache/price_stats.json` and the pipeline answers with a 5%-confidence safe-mode memo instead of garbage

## 🎬 Demo Script (4 minutes)

1. **(0:00)** Mandate: *"$100k, moderate risk, no greenwashing"* → 🚀 Convene the Boardroom.
2. **(0:40)** Point at agent cards: ESG Verifier citing RAG evidence; Analyst reading the carbon outlook.
3. **(1:20)** **⚔️ Debate moment:** two agents disagree on XOM (market bullish vs ESG greenwashing flag) — the Orchestrator resolves it live; optimizer caps it at 10%.
4. **(2:10)** CIO memo + allocation donut: every weight cites its evidence.
5. **(2:40)** 💨 Carbon tab: real forecast with honest backtest error.
6. **(3:00)** 📈 Learning tab: *"Day 5 the ESG agent flagged XOM before the market — watch its influence overtake the market agent's."*
7. **(3:20)** 🛡️ Compliance tab: PR-AUC under 99:1 + all 5 poisoned inputs intercepted.
8. **(3:35)** Close: *"Accurate, transparent, adaptive — and it refuses to answer when the data lies."*

## 🧯 Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: prophet` | Fine — linear fallback activates automatically (still runs) |
| Gemini quota/rate errors | Automatic fallback to OpenRouter free models (no action needed) |
| Dashboard sections say "Run `python -m ...`" | Run the pipelines in the Setup order above |
| Everything looks mocked | Check `.env`: `LLM_PROVIDER` should be `auto` + a valid `GEMINI_API_KEY` |
| `yfinance` fetch fails offline | Pre-generated `data_cache/*.json` files ship with the project |

## 🗺️ Hackathon Roadmap (48h)

| Hours | Deliverable |
|---|---|
| 0–3 | Setup + data flowing (done — repo scaffolded) |
| 3–10 | Data pipelines + RAG (done) |
| 10–20 | Agents producing strict JSON (done, mock-verified) |
| 20–28 | Orchestrator + debate loop (done, smoke-tested) |
| 28–34 | Optimizer + feedback backtest (done) |
| 34–42 | Dashboard polish + C02/C04 evidence (done) |
| 42–46 | Rehearse 3×, slides |
| 46–48 | Freeze + win 🏆 |
