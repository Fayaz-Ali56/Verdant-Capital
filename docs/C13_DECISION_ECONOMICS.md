# C13 — Cost-sensitive threshold optimization

## Financial assumptions

The question is whether a synthetic suspicious case should be flagged for manual
audit. Costs are illustrative USD **per case**, not estimated company losses.

| Actual outcome | Not flagged | Flagged for audit |
|---|---:|---:|
| Negative | TN: $0 | FP: $100 audit |
| Positive | FN: $10,000 loss | TP: $100 audit |

The example $100 audit can represent two analyst hours at $50/hour. The example
$10,000 missed loss can represent $25,000 exposure at 40% loss given default.
These are scenario assumptions, not sourced/calibrated estimates. Every flag
incurs audit overhead, including true positives. A true-positive audit is assumed
to prevent the modeled financial loss completely. No capacity limit, incomplete
intervention, recovery revenue or time discounting is modeled.

`Total economic loss = (TP + FP) × audit_cost + FN × missed_loss`

This is cost after the assumed benefit of successful intervention; prevented
loss is not subtracted again as revenue. Savings are the default policy's total
loss minus the selected policy's total loss, on the same test cases. Negative
savings remain visible. Costs can be changed in the Risk Lab form or CLI.

## Threshold selection and independent verification

1. Reuse the C02 six-feature synthetic generator and Isolation Forest specification
   (200 trees, contamination 1%, seed 7), with 20,000 training cases.
2. Split the remaining 10,000 cases into disjoint stratified validation and test
   sets of 5,000 each. Each has 50 positives and 4,950 negatives.
3. Train the model on training features only. Score validation and test features
   using `-decision_function`; higher means more anomalous, not a probability.
4. Enumerate every distinct validation score boundary, plus a boundary below
   the minimum, using the strict rule `score > threshold`. This includes audit-none
   and audit-all and never splits equal scores. Sorting and prefix sums make
   selection O(n log n), without an approximate grid.
5. Select the minimum validation loss. Equal losses prefer fewer audits, then
   the higher threshold. Test labels are not used to select a threshold.
6. Freeze the selected threshold and report its test confusion matrix and costs.
   Also report the C02 default threshold of zero, audit-none, and audit-all on
   the identical test set. The UI plots **validation** loss, not a test-optimized curve.

The validation minimum does not guarantee the lowest test or production loss.
This is a single-seed decision-economics experiment, not C02's five-seed aggregate.
C13 fits a separate model using the same specification; it does not modify the
C02/C06 reports, the investment portfolio, or real issuer assessments.

## Reproduce and present

From the project root, on Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m challenge.c13_cost_sensitive --audit-cost 100 --missed-loss 10000
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

On Linux use `.venv/bin/python` instead. CLI output is saved to
`data_cache/c13_report.json` (or `VERDANT_DATA_DIR`). The Risk Lab independently
computes/caches the experiment for the submitted form values and provides a JSON
download; it does not silently read a different CLI scenario. Reports contain
the financial matrix, assumptions, split sizes, validation curve, selected
threshold, four test policies, costs, confusion counts and limitations.

Pitch demonstration: explain the cost matrix, show the selected validation
minimum, then compare test loss and the additional audits/missed positives against
the default. Raising missed-positive losses can justify a lower threshold and
more audits; expensive audits can justify fewer flags. Use actual run results,
not hardcoded savings. Thresholds can be negative because these are anomaly
scores, not probabilities.

## Limits and production requirements

All labels/features are synthetic. The assumed loss is not a measured loss on
the historical ticker portfolio. Real deployment needs measured audit expense,
exposure/LGD and intervention effectiveness, issuer/time-separated datasets,
capacity constraints, prevalence/cost sensitivity and stability evaluation.
This demonstration does not approve loans or substantiate real financial savings.
