# Verdant Capital — C02, C06 & C13 Evaluation and Audit Evidence

## Objective and scope

The 3-agent Verdant Capital architecture evaluates sustainable-investment candidates through ESG, market and portfolio analysis. C02 and C06 are a **research audit laboratory** for the ESG Verifier, not a separate AI agent.

**This package does not automatically verify company greenwashing or approve loans.** Its labels and six document-feature values are **synthetically generated**. A real-world claim needs sourced reports, defensible feature extraction, independently verified labels, external validation and documented escalation policy.

## C02: severe rare-event stress

- Generator: 6 tabular features. Negative and positive feature values are sampled from different distributions. Generated positive is defined as synthetic suspicious disclosure (label 1), NOT verified fraud.
- Evaluation split: 20,000 training examples and 5,000 untouched test examples, containing exactly 4,950 negatives / 50 positives, repeated for seeds 7, 13, 21, 34, 55.
- Model: `IsolationForest(n_estimators=200, contamination=0.01)`; unsupervised fit on training feature values only. A larger `-decision_function()` means a greater anomaly score.
- Threshold: score > 0, determined by the training contamination parameter. Evaluation labels never choose this threshold.
- Results: PR-AUC (trapezoidal) and Average Precision (threshold-weighted, recommended primary number), precision/recall/F1/confusion matrix, top-1%-audit precision, random-ranking AP baseline ≈1%, and a majority-class 99%-accuracy caution.
- Anti-collapse gate: at least one true positive and at least one flagged sample in every evaluation seed.
- The generated positive class is unusually separable by construction. The numeric performance score **cannot be extrapolated to live companies**.
- Data leakage caution: do not tune test-time thresholds or make features using future events. For real data, split by time and issuer before evaluation and enforce source independence.

### Generated files

- `data_cache/c02_report.json`: cross-seed metrics, exact counts, confusion matrix, data provenance and notes
- `data_cache/c02_pr_curve.json`: first-seed PR curve with all points (others assessed numerically)

## C06: feature attribution

- Fit **the same C02 model specification** on seed 7 training data.
- Select three **distinct actual test-set rows**: true positive, false positive, false negative, taking the case nearest the decision boundary in each category. If a category is absent, a real held-out borderline row is substituted and explicitly named.
- Use `shap.Explainer(score_func, background, algorithm="permutation")` to explain the **anomaly score** itself, not a fictional fraud probability.
- Verify local additivity: `base_value + sum(SHAP_feature_values) ≈ anomaly_score` for each example.
- Positive SHAP contribution => pushes score upward / raises suspicion for this model; negative => lowers suspicion.
- Output three PNG horizontal feature-attribution charts and `data_cache/c06_report.json` with all feature values, thresholds, labels, decision classes, SHAP values and reconstruction values.
- SHAP is feature attribution, **not causality or proof** of greenwashing. A regulated real-world decision additionally requires reason codes, evidence sources, human-review policy and model documentation.

## C13: decision economics

The Risk Lab includes an explicit USD cost matrix, exact validation-loss threshold
search, held-out confusion matrix and audit-all/audit-none/default comparisons.
Costs are editable illustrative assumptions. See
[C13 methodology and reproduction](C13_DECISION_ECONOMICS.md) for the cost formula,
independent train/validation/test splits and scope limitations.

## Reproducible commands

From the root of the repository:

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements.txt
python -m challenge.c02_rare_event
python -m challenge.c06_explainability
python -m challenge.c13_cost_sensitive
python -m pytest -q tests/test_challenge_audit.py
streamlit run app.py
```

## Validation checklist

- Evaluation ratio exactly 99:1 across seeds.
- Source report accurately says **synthetic**.
- AP/PR-AUC higher than random-ranking baseline; first-seed confusion matrix exists.
- Model flags actual held-out positives, not just the negative majority.
- Every C06 case is a real held-out row, no invented false positives or false negatives.
- SHAP sum reconstructs the modeled score for each case.
- Dashboard shows PR curve + C02 metrics + three attribution charts without key errors.
- Demo is transparent about missing real-world validation.

## Remaining core project blockers

The core boardroom now has declared graph state fields, contradictory-signal review,
issuer and page-scoped retrieval, SciPy constraint-aware allocations and source-filtered
feedback weights. Its mathematical allocation report also includes deterministic
policy reason codes. C06 does **not** explain those end-to-end investment weights.
Real-world external validation, automated outcome-matching and deployed production
infrastructure remain outside this synthetic MVP.


## C04 and C15

C04 (`python -m challenge.c04_guard`): 6 injected out-of-bounds cases, 6 handled, 0 confident wrong predictions; the bare model returns a normal-looking score for the impossible ones. C15 (`python -m challenge.c15_impact`): net gain in PKR under stated assumptions on synthetic cases; not a realized saving.
