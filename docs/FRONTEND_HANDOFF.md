# Studio handoff

The functional application is `app.py`. Screenshots in `docs/screenshots/` are
captures of the running Streamlit application, not static HTML specimens.

- Boardroom: a visible review action, actual allocation strip/ledger, risk estimates, policy results, specialist evidence and audit export.
- Risk Lab: choose C02/C06 detection/explanations or C13 decision economics. Hidden evaluations do not execute.
- Market intelligence: explicitly dated cache/proxy inputs and simulated feedback.
- Audit trail: shared local recommendation register and current policy reasons.

`ui/theme.css` owns the dark palette, typography, focus, interaction, responsive
rules and motion. `ui/presentation.py` escapes values entering custom HTML.
Native Streamlit controls provide keyboard interaction. Every graphic has a
textual interpretation; color is not the sole indicator of decisions.

Real review work displays a skeleton and a live status. Reduced-motion mode
removes shimmer and transitions. Empty, missing-data, corrupt-report and failed
persistence states provide recovery guidance without displaying provider errors.

Run `python scripts/check.py`, then the optional `tools/browser_qa.cjs` against
a running app. See QA_REPORT.md for actual results and browser/framework limits.
