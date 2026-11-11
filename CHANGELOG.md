# Changelog

## Final audit pass — 2026-11-11

### Added

- C04 out-of-bounds guard (`challenge/c04_guard.py`): hard rejection of impossible values, soft low-confidence flag for extreme ones, before/after evidence against the bare model.
- C15 net financial impact in PKR (`challenge/c15_impact.py`) with a finite-input formula and portfolio scaling.
- Risk Lab view for both, with loading states; 19 new regression tests (70 total); `docs/DEMO_SCRIPT.md`.

### Fixed

- Guard crashed with `OverflowError` on astronomically large integers (found by fuzzing); now rejected cleanly.
- C15 formula accepted NaN; now rejects non-finite inputs.
- C02 class-balance check used `assert` (removed under `python -O`); now raises `ValueError`.
- Documented the parameterized-placeholder SQL in `feedback_store` for scanners.

### Changed

- Tabular numerals on metrics, bordered data tables.

## Submission candidate — 2026-11-11

### Added

- C13 explicit USD cost matrix, exact validation threshold selection, independent test confusion matrix, baseline policies and JSON evidence.
- Adversarial regressions for malformed inputs, caches, provider payloads, concurrent migrations and idempotent outcomes.
- Failure-injected real Streamlit flows, optional multi-viewport browser/axe runner, cross-platform check command, and constrained development dependencies.
- Actual runtime screenshots, QA evidence and licensing/attribution status.

### Changed

- Editorial dark studio with a prominent mandate action, lazy workspace navigation, direct C13 selection, accessible allocation strip, purposeful motion and reduced-motion support.
- Historical return display separated from the optimizer's ESG-adjusted objective.
- Exact 30/90-session offsets; corrupted/missing price caches fail closed.
- Finite capital/influence validation, reserved cash symbol, stronger ESG response shape validation, safe recoverable UI failures.
- Serialized SQLite migration/write transactions and duplicate-outcome protection for legacy schemas.
- Atomic report/provider-cache writes and non-destructive simulation database replacement.
- Local-only default binding, enabled XSRF/CORS, disabled telemetry and traceback display, constrained container install and sanitized source-only packaging.

### Removed

- Fake Streamlit smoke framework, obsolete static design specimen, stale release instructions and unused analyst/review prompts.
- Heavy boardroom donut rendering; the same weights now have a lightweight labeled allocation graphic and ledger.

### Known limits

- Synthetic benchmark validity, optional provider/RAG validation, shared single-operator storage, pending licensing, framework performance and unavailable browser coverage are explicitly triaged in QA_REPORT.md.
