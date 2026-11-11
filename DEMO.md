# 4-Minute Demo Script — Verdant Capital

**Before you go on stage (do this once, with internet):**
```bash
python -m data.fetch_market && python -m data.carbon_forecast
python -m data.feedback_backtest && python -m challenge.c02_rare_event
streamlit run app.py        # click "Convene the Boardroom" ONCE so the LLM cache is warm
```
Responses are cached on disk, so the second run is instant and survives a dead Wi-Fi.
Keep `LLM_PROVIDER=auto`; if every provider fails the app falls back to mock mode and shows a **MOCK MODE** banner — never present mock output as live analysis.

| Time | What you do | What you say |
|---|---|---|
| 0:00 | Show the page header + carbon forecast chart | "Sustainable investing has three problems: greenwashing, volatile carbon prices, and no way to trust an AI's allocation. We built a boardroom of agents that debate each other." |
| 0:30 | Click **Convene the Boardroom** | "An ESG Verifier checks disclosures against retrieved evidence; a Market Analyst reads price and carbon signals." |
| 1:15 | Scroll to **The Debate** | "They disagreed on XOM — the market agent was bullish, the ESG agent flagged greenwashing. The analyst had to hold or revise, and it revised. The debate changed the outcome." |
| 2:00 | Final memo + allocation | "Weights come from a constrained allocator, not from the LLM's guess: greenwashing-flagged assets are capped at 10%, with position caps by risk profile." |
| 2:30 | **Output Guard** panel | "LLMs ignore rules. Our guard validates every output — ranges, sums, caps, hallucinated tickers — and repairs violations. Here it is, live." |
| 3:00 | Adaptive Feedback Loop chart | "Each recommendation is stored and scored; accuracy re-weights each agent's influence. **This chart is a simulated scenario** — real outcomes need 30 days to accrue — but the mechanism is live and drives the allocation." |
| 3:30 | C02 panel | "Greenwashing is a <1% rare-event problem. At 99:1, 'approve everything' scores 99% accuracy and is useless, so we report PR-AUC over 5 seeds. **On synthetic disclosure data** it's 0.96 vs a 0.01 random baseline; at a 1% audit budget, 9 in 10 flags are true positives." |
| 3:50 | Close | "Make every investment decision smarter, more transparent, and more sustainable." |

## Questions judges will ask — honest answers
- **"Is the C02 result real?"** — It's a synthetic benchmark; it proves the 99:1 evaluation harness and that the detector doesn't collapse. Next step: train/evaluate on a labelled corpus of SEC/EU greenwashing rulings.
- **"Is the feedback loop real?"** — The mechanism is: outcomes → accuracy → influence weights → allocation. The 30-day history shown is simulated; live outcomes accrue as recommendations age.
- **"Is this mean-variance optimisation?"** — No. It's a volatility-adjusted score tilt with hard constraints. Honest and explainable; full MVO is future work.
- **"Carbon forecast accuracy?"** — The dashboard shows the honest 30-day holdout error (MAPE). KRBN is an ETF proxy for carbon credits, not the EU ETS spot price.
