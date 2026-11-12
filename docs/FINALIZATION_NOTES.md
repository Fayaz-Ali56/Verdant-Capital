# Verdant Capital — finalization notes

## Assignment mapping

- Hackathon track: Battle of Intelligence
- Mission / Pillar 2: Green Capital Allocation & Portfolio Intelligence
- C02: Severe Class Imbalance / Rare-Event Stress
- C06: Explainability & Feature Attribution
- C13: Cost-Sensitive Threshold Optimization

The Battle of Byte cards with the same numbers have different definitions and are not the challenge implementations claimed here.

## Work completed in this finalization

1. **Carbon market scenario integration**
   - The KRBN historical proxy projection is now passed into the portfolio optimizer.
   - It affects only KRBN, and only if KRBN is explicitly part of the selected candidate universe and has adequate price history / eligibility.
   - The 30-session proxy change is shrunk to 25% and capped at +/-5 annualized percentage points. This is a bounded scenario sensitivity, not a calibrated forecast or a carbon-credit spot-price quote.
   - KRBN is available as an optional historical-mode investment-universe selection; it is not selected by default.
   - The scenario and applied adjustment are written into the optimizer metrics and final memo.

2. **Portfolio allocation explanations**
   - Each eligible asset's memo audit now records allocation weight, expected-return contribution, marginal variance contribution, ESG position cap, ESG verdict/credibility, and any KRBN scenario adjustment.
   - Hard ESG exclusions and cash fallback remain enforced by the numerical optimizer.

3. **C13 optional PKR scenario**
   - C13 remains calculated in USD by default.
   - `--usd-pkr RATE` optionally adds a PKR conversion using a rate supplied by the operator. The report labels it as a user assumption, not a live exchange quote.
   - Example: `python -m challenge.c13_cost_sensitive --usd-pkr 280`

4. **Documentation accuracy**
   - README and challenge evaluation docs explicitly map the repository's C02/C06/C13 to Battle of Intelligence definitions.
   - Documentation distinguishes the KRBN ETF proxy from carbon-credit spot prices and explains when the proxy scenario can influence an allocation.
   - QA report now distinguishes historical QA results from this finalization environment's checks.

## Verification performed for this archive

- Python bytecode compilation: passed (`python -m compileall -q .`).
- C02/C06 challenge audit tests and C13 cost-sensitive tests: 15 passed, 1 UI-only test deselected because Streamlit is not installed in the packaging environment.
- Direct portfolio integration check: passed; KRBN adjustment capped at 5.0 percentage points, no adjustment applied to unrelated tickers, weights sum to 100%.
- C13 PKR conversion check: included in the passing tests.
- Full UI / LangGraph suite was not rerun in this environment because Streamlit and LangGraph are absent and outbound package installation was unavailable. See `QA_REPORT.md` for the prior full-environment QA evidence and its limitations.

## No interface redesign

The existing Streamlit interface and visual design were retained. Changes are in the optimizer, report outputs, tests and documentation.

## Important limitations

- C02/C06/C13 experiments use synthetic data; their metrics are not real-world fraud or ESG accuracy claims.
- Uploaded issuer reports are not independently authenticated. Page citations establish retrieval provenance, not truth.
- KRBN is a listed ETF proxy, not a spot carbon allowance / credit price.
- Portfolio outputs are decision-support simulations; no trades are executed and no investment advice is provided.
