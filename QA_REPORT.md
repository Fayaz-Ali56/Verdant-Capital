# Submission audit and QA report

**Date:** 2026-11-11. **Scope:** the complete retained project source, configuration,
documentation, benchmark assets and release tooling. This report describes a
verified local research demonstration, not production certification. The work
started from C13 commit `06a1add`; the submission commit contains this report.

## Readiness decision

The offline judge workflow passes the checks below. No known reproducible P0
failure remains in that tested workflow. Remaining issues are explicitly triaged
below. **The requested Lighthouse 90+ performance target was not achieved.**
Firefox/WebKit and real Windows execution are not claimed. Authentication and
tenant isolation are not implemented; this is a trusted single-operator tool.

## Reproduction and environment

- Linux x86_64, Python 3.12.14, pip 26.3; dependencies constrained by `requirements-lock.txt`.
- Ruff 0.17.4; Chromium 156.0.8078.79; Lighthouse 13.6.0; axe Playwright 4.14.0.
- A new `/tmp/verdant-clean-venv` was created without reusing the application's installed environment, then installed using `requirements-dev.txt` and the constraints file. Both the original and fresh environments passed the gate.
- `python scripts/check.py` runs dependency consistency, lint, format check, all tests, actual Streamlit AppTest smoke flows and Python compilation. This repository has no Node application build.
- Evidence: [browser results](docs/qa/browser-results.json), [Lighthouse measurements](docs/qa/lighthouse-summary.json), [dependency audit](docs/qa/dependency-audit.json), and [source inventory](docs/qa/source-inventory.json).

## Final audit pass (C04 / C15 additions)

Re-run in this pass: ruff (standard and extended rule sets), bandit (0 high; the one medium is a parameterized-placeholder query, annotated), vulture (clean), pip-audit (no known vulnerabilities), deptry (only the optional LLM/RAG packages that live in their own requirements files), 51 passing tests, the real Streamlit smoke flows, and a fuzz of the C04 guard and C15 formula. Fuzzing found and fixed two bugs (see CHANGELOG). A 6-thread concurrent C15 run returned identical results.

**Not re-run in this pass (no browser available in the audit environment):** the Chromium multi-viewport matrix, axe, and Lighthouse for the new C04/C15 view; Firefox/WebKit and real mobile devices remain unverified. The new view uses only native Streamlit components, but treat its accessibility and performance as unmeasured until `tools/browser_qa.cjs` is run on your machine. Light mode is not offered; the app is dark by design.

## Executed checks

| Area | Outcome | Evidence / limits |
|---|---|---|
| Fresh install | Passed | New Python 3.12 virtual environment; constrained install; `pip check` |
| Lint / formatting | Passed | Ruff check and format check across repository Python source |
| Full regression suite | **51 passed**, none skipped | Includes core, C02/C06, C13, presentation, adversarial and failure-recovery tests |
| Real UI smoke | Passed | Actual Streamlit AppTest, no fake framework; isolated temporary data |
| Compilation | Passed | App, configuration, agents, challenge, data, orchestration, UI, tools and scripts |
| C02 | Passed | Fresh five-seed CLI evaluation; synthetic 99:1 splits; no majority collapse |
| C06 | Passed | Fresh CLI; three actual held-out cases and additive reconstruction checks |
| C13 | Passed | Fresh CLI; validation-selected threshold; independently scored test confusion/costs |
| Feedback simulation | Passed twice | Repeat run replaces only its completed synthetic database; real feedback retained |
| LangGraph | Passed | Actual graph execution, deterministic memo and SQLite persistence |
| Chromium functional matrix | Passed | Four viewport sizes; review, navigation, C02/C06, C13 form update, cost-specific JSON download, market and audit views |
| Automated accessibility | Passed in tested states | Zero axe WCAG 2 A/AA and 2.1 AA findings on boardroom and C13 at all four sizes; no rules excluded |
| Keyboard / motion / overflow | Passed in tested states | Focus movement, valid skip destination, reduced motion on mobile, no document-level horizontal overflow |
| Browser errors | Zero in final matrix | Captured page exceptions and console errors; not a blanket claim about every optional external provider |
| Dependency vulnerability scan | Passed | pip-audit: no known vulnerabilities after upgrading pip; advisory results are time-dependent |
| Docker | Passed | Fresh constrained build with TLS verification, non-root UID 1000, HTTP health, browser review and actual LangGraph persistence |
| Source packaging | Passed | Tracked files only; regression excludes environment secrets, databases and untracked files; archive inspected before delivery |

The native AppTest runner prints Streamlit's documented missing-ScriptRunContext
warning on its controlling thread. It did not correspond to an app exception.
CLI output is intentional; debug logging is not inserted into the frontend.

## Adversarial and error-injection coverage

- NaN, infinity, negative/non-numeric capital; reserved `CASH` input and invalid risk settings.
- Infinite price histories, corrupt CSV, missing historical cache, empty candidate universe, zero/cash-only portfolios and long-only constraints.
- Exact 30-session price return intervals rather than the previous 29-interval calculation; date normalization and conflicting ticker columns.
- Invalid LLM narrative/flag shapes, missing evidence, mismatched assessment data; provider/solver failure containment without leaking a sensitive error string.
- Corrupt feedback JSON, corrupt SQLite file, invalid benchmark JSON structure; independent C13 remains usable when C02/C06 evidence is invalid.
- Concurrent first-use legacy migration/recommendation writes: 16 calls with 8 workers; no duplicate migration failure and unique recommendation identifiers.
- Concurrent repeated legacy outcome submissions: idempotent single outcome.
- 24 concurrent atomic report writes: complete readable JSON, no abandoned temporary files.
- Empty outcome-source filters cannot accidentally admit synthetic outcomes.
- C13 tied scores, every distinct boundary, audit-all/audit-none, zero costs, invalid costs, and changing cost ratios.
- C13 browser download after changing missed loss to $50,000: exported matrix must match the submitted scenario. Cost-specific labels, keys and filenames prevent a stale scenario download.
- Release fixture verifies that a tracked environment secret and database, and an untracked key file, do not enter the ZIP.

The browser matrix used 1440×1000, 820×1180, 390×844 and 320×740 viewports. These
are emulated dimensions on Linux Chromium, not physical-device or Safari tests.
The final complete matrix was rerun after restarting the app to clear stale
imported modules. Screenshots in `docs/screenshots/` are actual runtime captures.

## C13 verification example

Illustrative $100 audit / $10,000 missed-positive loss, seed 7, 20,000 training,
5,000 validation and 5,000 untouched test cases:

| Test policy | TP | FP | FN | TN | Total modeled loss |
|---|---:|---:|---:|---:|---:|
| Default threshold 0 | 47 | 5 | 3 | 4,945 | $35,200 |
| Validation-selected threshold | 49 | 30 | 1 | 4,920 | $17,900 |

The selected threshold was approximately −0.0315983. Savings of $17,300 are
**synthetic, assumption-dependent test results**, not real portfolio savings.
The algorithm never selects a threshold using test labels, and keeps negative
held-out savings visible for scenarios where they occur.

## Lighthouse: measured, not promised

Navigation audits used local HTTP, default Lighthouse desktop/mobile settings
and fresh browser contexts. These are cold-navigation lab measurements, not
warm-interaction scores. They include the Streamlit shell and frontend bundles.

| Category | Desktop | Mobile |
|---|---:|---:|
| Performance | **51** | **13** |
| Accessibility | **100** | **100** |
| Best practices | **100** | **100** |
| SEO | **82** | **82** |

The original desktop measurement was 35 performance / 96 accessibility. Lazy
workspaces and the lightweight allocation view reduced measured cold transfer
from approximately 7.9 MiB to 3.3 MiB. Accessible multiselect colors and a valid
skip-link target corrected the measured accessibility findings.

**Performance is still below target.** Large framework/protobuf/font bundles,
progressive layout shifts and simulated mobile throttling dominate. The cold
mobile run recorded approximately 21.4 seconds LCP and 1.189 CLS. Reaching a
reliable 90+ needs additional delivery/layout work and potentially a frontend
architecture change; this audit does not disguise that as a pass. SEO findings
include the framework entry's missing meta description and robots handling; this
local non-indexed workspace is not a marketing site.

Lighthouse accessibility and zero axe findings are useful automated evidence,
not a full WCAG AA certification. Manual screen-reader, full assistive-technology,
zoom/forced-colors and complete WCAG 2.2 testing remain unverified.

## Security and authentication boundary

- Default loopback binding; Compose publishes loopback only. XSRF/CORS enabled, usage telemetry off, detailed browser tracebacks disabled.
- Custom HTML escapes variable text. SQL values are parameterized. Optional model output is validated; citations come from registered source records. Optional provider calls have timeouts and bounded retries.
- Provider caches and generated JSON/CSV are atomically replaced. Source ZIPs do not contain `.git`, `.env` variants, PDFs, data caches, local databases or untracked files.
- Recognizable secret-pattern scanning and Python/JSON parsing are recorded in the source inventory tooling. This is heuristic inspection, not proof that arbitrary secrets can never exist.
- There is **no login, account authorization, tenant isolation or append-only/tamper-proof audit system**. Shared local SQLite records are visible to anyone with access to this app. Unauthenticated access to the intended local workspace is expected behavior, not a passed SaaS authentication test.
- Public or multi-user deployment is blocked until authentication, tenant-scoped storage, retention, rate limits and deployment security are designed and verified.

## Explicit remaining triage

| Priority | Item | Disposition |
|---|---|---|
| P1 | Cold-navigation performance below 90; especially mobile | Open; measured above. Offline desktop demo works, but no claim of meeting the performance requirement |
| P1 for deployment | No authentication / tenant isolation | Local-only boundary retained; do not expose directly to the Internet |
| P2 | Firefox and WebKit | Installations attempted separately; browser-CDN requests returned HTTP 403 `Domain forbidden`. Not executed |
| P2 | Windows/macOS/native devices | Commands and Windows/Ubuntu CI matrix supplied; actual host execution and GitHub Actions completion were not verified here |
| P2 | Optional provider-backed RAG | No live credentials/model download validation; schema/fallback behavior tested. Retrieved documents are not authenticated, and a changed/deleted PDF may require rebuilding the local index |
| P2 | Real market refresh | Existing user Windows run demonstrated downloads; this final audit uses offline tests and injected cache cases rather than claiming a new live-provider validation |
| P2 | Full WCAG certification | Automated and selected keyboard/motion checks only; manual assistive-technology coverage remains |
| Product scope | Real-world financial/ESG validity | Synthetic features/costs, heuristic confidence and uncalibrated forecasts; no external issuer/default validation or automatic future-outcome collection |
| Owner decision | Licensing | Proprietary — All Rights Reserved notice added; contributors retain their respective rights and third-party licenses remain separate |

No tests, assertions, security checks or TLS verification were disabled to make
these results pass. Browser install denials were recorded rather than bypassed.

## File review and delivery

All retained Python source, manifests, CI/container settings and project docs
were inspected; the audit removes unused prompts, abandoned helpers, obsolete
static specimens and the fake UI runner. The source inventory enumerates retained
tracked files with sizes, hashes and text line counts. Python ASTs and JSON
artifacts were parsed; binary screenshots/plots are treated as generated evidence,
not executable source. Installed third-party libraries were dependency-scanned,
not represented as line-by-line audited project code.

The release script packages only intended tracked source. Mutable `.env`, price
caches, PDFs, provider caches, SQLite state, temporary QA tools and installed
virtual environments are excluded. The archive contains the updated README,
QA report, changelog, environment template, source, tests, configs, attribution and
actual screenshots. GitHub `main` is the source of truth after the final push.


## Finalization patch — 2026-11-12

The hackathon review identified two mission-integration improvements, now included
in the source: (1) the dated KRBN ETF-proxy trend can enter the optimizer only
when KRBN is explicitly selected, using 25% shrinkage and a +/-5 annualized
percentage-point cap; and (2) the memo now records per-asset allocation
explanations, including ESG cap, ESG verdict, expected-return contribution,
variance contribution and any carbon-proxy adjustment. C13 also accepts an
optional user-supplied `--usd-pkr` scenario conversion while preserving USD as
the calculation basis. No UI redesign was made.

The assignment mapping is now explicit: this repository's C02/C06/C13 modules
implement the **Battle of Intelligence** definitions (rare-event stress,
explainability, cost-sensitive threshold optimization), not the different
Battle of Byte cards with the same numbers.

Patch verification in the packaging environment: `compileall` passed; direct
portfolio execution confirmed the carbon scenario is capped at 5.0 percentage
points and applies only to KRBN; the complete test suite could not be rerun here
because Streamlit and LangGraph are absent and package installation was blocked
by unavailable network access. The original QA measurements above are retained
as historical evidence, not represented as a fresh rerun of this patch.
