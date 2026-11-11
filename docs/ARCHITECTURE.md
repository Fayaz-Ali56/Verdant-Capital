# Architecture and Design Contract

## Requirements sources

The uploaded **Problem Statement & Working Procedure** specifies fragmented
climate/market data, ESG disclosures, verifiable sustainable investments,
climate-credit price volatility, risk-return optimization, transparent agent
collaboration and simulation. The original deployment concept proposed four
agents and an AWS/Mongo/Jenkins/Docker architecture.

The uploaded **A Complete Overview of Project** changes the system to three
agents (ESG Verifier, Carbon & Market Analyst, Portfolio Optimizer), a LangGraph
orchestrator, and a feedback memory layer. **This implementation adopts that
three-agent overview**; it treats regulatory risk as a constraint of the
optimizer and a review input to the ESG specialist.

## Three specialist boundaries

### ESG Verifier

Input: user-selected company ticker, issuer-scoped report chunks with source/page,
optional structured LLM analysis. Output: `esg_credibility`,
`greenwash_risk`, `verdict`, `confidence`, evidence citations, provenance.
Missing authenticated evidence produces an explicit `unverified` decision.
The demonstration uses marked fictional fixtures, not real allegations.

### Carbon & Market Analyst

Input: dated adjusted close market prices and KRBN ETF-proxy data. Output:
market direction based on historical 30-session returns, current data date,
uncertainty and source. A trend is not a causal carbon impact or forecast.

### Portfolio Optimizer

Input: ESG decisions, price covariance, available historical means,
risk preference, ESG constraints and provenance-filtered historical agent
influence. Output: long-only allocations across selected tickers plus `CASH`
that always sum to 100%. The LLM is not permitted to change these numbers.

## LangGraph states and routing

`GraphState` declares every communication channel. Steps:

1. `esg_verifier` retrieves issuer-specific ESG citations.
2. `market_analyst` computes provenance-tagged market results.
3. `check_consensus` identifies *incompatible conclusions* (high ESG risk but
   bullish market signal), not merely different confidence levels.
4. `critique` creates an evidence review, max one bounded round; it cannot
   override hard portfolio policy.
5. `portfolio_optimizer` computes allocations using SciPy SLSQP.
6. `synthesis` constructs a deterministic memo and validates weights.
7. `persist` stores a dated, non-executing recommendation in SQLite.

## Event-driven what-if replay

Dashboard scenario selection triggers a new execution of the boardroom with
hypothetical last-30-session price impacts. It recomputes the data, dispute,
portfolio and memo; users can compare baseline versus event allocations.
**This is a user-triggered event simulation, not real-time distributed
microservice orchestration.** Event effects and fictional issuers are invented
for demonstration and clearly marked.

## Data integrity

- Market statistics are derived from cached, dated yfinance closes.
- Carbon forecast is a proxy ETF price trend with heuristic uncertainty bands.
- Issuer-level RAG metadata: ticker, report filename, PDF page, citation.
- Unverified ESG scores do not become certified financial decisions.
- Feedback uses explicit `label_source`; live/market mode admits only
  `verified` outcomes, while demo uses its separate synthetic database.
- Numeric weights and source evidence are included in saved audit JSON.

## User experience

The Streamlit app has Boardroom, Risk Lab, Market & Memory, and Audit views.
It defaults to an offline fictional demo so the presentation works without
an API key. A banner identifies synthetic market/ESG data. Risk Lab shows
PR-AUC/AP and C06 plots directly from generated reports.

## Decision economics and operational boundary

C13 uses the C02 generator/model specification with separate train, validation
and test splits. Only validation labels choose the threshold; a fixed policy
is evaluated on test cases. Costs and savings are illustrative, not issuer losses.

Only the selected Streamlit workspace executes. The application is a trusted
local single-operator tool: it has no account authentication or tenant isolation.
The loopback server and XSRF/CORS defaults are not substitutes for an authenticated
reverse proxy in a deployment. Reports are atomically replaced; SQLite migrations
and writes use serialized transactions. See QA_REPORT.md for verified coverage.
