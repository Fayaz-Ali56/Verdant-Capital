"""C13: select an economic operating point on validation data, then test once.

The C02 synthetic generator/model is reused; no real defaults or ESG losses
are measured. Costs are illustrative USD assumptions, not calibrated estimates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import train_test_split

import config
from challenge.c02_rare_event import run_trial
from data.files import write_json


def _inputs(labels, scores, audit_cost, missed_loss):
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    if (
        labels.ndim != 1
        or scores.ndim != 1
        or not len(labels)
        or len(labels) != len(scores)
        or not np.isin(labels, [0, 1]).all()
        or not np.isfinite(scores).all()
    ):
        raise ValueError("Use equally sized, nonempty binary labels and finite anomaly scores")
    if not all(np.isfinite(c) and 0 <= c <= 1e12 for c in (audit_cost, missed_loss)):
        raise ValueError("Costs must be finite USD amounts between 0 and 1 trillion")
    return labels.astype(int), scores


def _result(threshold, tp, fp, fn, tn, audit_cost, missed_loss):
    tp, fp, fn, tn = map(int, (tp, fp, fn, tn))
    audit_spend = (tp + fp) * audit_cost
    missed_spend = fn * missed_loss
    return {
        "threshold": float(threshold),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "flagged": tp + fp,
        "audit_cost_usd": float(audit_spend),
        "missed_loss_usd": float(missed_spend),
        "total_loss_usd": float(audit_spend + missed_spend),
        "precision": tp / (tp + fp) if tp + fp else 0.0,
        "recall": tp / (tp + fn) if tp + fn else 0.0,
    }


def cost_curve(labels, scores, audit_cost=100.0, missed_loss=10000.0):
    """All distinct score > threshold policies, including audit-none and audit-all.

    Sorting plus prefix sums gives exact tied-score decisions in O(n log n).
    Anomaly scores are not probabilities; no probability cutoff is assumed.
    """
    labels, scores = _inputs(labels, scores, audit_cost, missed_loss)
    order = np.argsort(scores, kind="stable")
    ordered = scores[order]
    positives = np.r_[0, np.cumsum(labels[order])]
    thresholds = np.r_[np.nextafter(ordered[0], -np.inf), np.unique(ordered)][::-1]
    if not np.isfinite(thresholds).all():
        raise ValueError("Scores must allow a finite audit-all threshold")
    unflagged = np.searchsorted(ordered, thresholds, side="right")
    total_positive = int(positives[-1])
    return [
        _result(
            t,
            total_positive - positives[k],
            len(labels) - k - total_positive + positives[k],
            positives[k],
            k - positives[k],
            audit_cost,
            missed_loss,
        )
        for t, k in zip(thresholds, unflagged, strict=False)
    ]


def select_threshold(labels, scores, audit_cost=100.0, missed_loss=10000.0):
    """Minimum validation loss; ties prefer fewer audits, then higher threshold."""
    return min(
        cost_curve(labels, scores, audit_cost, missed_loss),
        key=lambda row: (row["total_loss_usd"], row["flagged"], -row["threshold"]),
    )


def operating_point(labels, scores, threshold, audit_cost, missed_loss):
    labels, scores = _inputs(labels, scores, audit_cost, missed_loss)
    if not np.isfinite(threshold):
        raise ValueError("Threshold must be finite")
    flagged = scores > threshold
    return _result(
        threshold,
        np.sum(flagged & (labels == 1)),
        np.sum(flagged & (labels == 0)),
        np.sum(~flagged & (labels == 1)),
        np.sum(~flagged & (labels == 0)),
        audit_cost,
        missed_loss,
    )


def evaluate(
    audit_cost=100.0,
    missed_loss=10000.0,
    seed=7,
    n_train=20000,
    n_validation=5000,
    n_test=5000,
    n_estimators=200,
):
    _inputs([0, 1], [0.0, 1.0], audit_cost, missed_loss)
    trial = run_trial(
        seed=seed, n_train=n_train, n_eval=n_validation + n_test, n_estimators=n_estimators
    )
    validation, test = train_test_split(
        np.arange(len(trial.y_eval)), test_size=n_test, stratify=trial.y_eval, random_state=seed + 1
    )
    curve = cost_curve(trial.y_eval[validation], trial.scores[validation], audit_cost, missed_loss)
    selected = min(
        curve, key=lambda row: (row["total_loss_usd"], row["flagged"], -row["threshold"])
    )
    # Selection is complete before any test labels are used for operating metrics.
    labels, scores = trial.y_eval[test], trial.scores[test]
    policies = {
        "optimized": selected["threshold"],
        "default": 0.0,
        "audit_none": float(scores.max()),
        "audit_all": float(np.nextafter(scores.min(), -np.inf)),
    }
    results = {
        name: operating_point(labels, scores, threshold, audit_cost, missed_loss)
        for name, threshold in policies.items()
    }
    savings = results["default"]["total_loss_usd"] - results["optimized"]["total_loss_usd"]
    return {
        "challenge": "C13 Cost-Sensitive Threshold Optimization",
        "data_type": "synthetic",
        "currency": "USD",
        "seed": seed,
        "model": f"IsolationForest({n_estimators} trees, contamination=0.01); C02 specification",
        "splits": {"train": n_train, "validation": n_validation, "test": n_test},
        "positive_rate": 0.01,
        "cost_matrix_usd": {
            "tn": 0.0,
            "fp": float(audit_cost),
            "fn": float(missed_loss),
            "tp": float(audit_cost),
        },
        "cost_assumptions": "Illustrative USD per case: every flag incurs an audit; a true-positive audit prevents the modeled loss. No recovery revenue, residual loss, or audit-capacity limit modeled.",
        "loss_formula": "TP × audit cost + FP × audit cost + FN × missed loss; TN costs zero",
        "selection": "Exact minimum validation loss across all distinct score boundaries; ties prefer fewer audits then higher threshold. Flag iff anomaly score > threshold.",
        "selected_validation": selected,
        "validation_curve": curve,
        "test": results,
        "test_savings_vs_default_usd": float(savings),
        "limitations": [
            "Synthetic cases and assumed costs; no demonstrated real-world financial savings or default prediction.",
            "The validation minimum is not a guaranteed test or production minimum; negative test savings are retained.",
            "Independent synthetic splits share a generator; real deployment needs issuer/time splits and measured costs.",
            "C13 is a separate benchmark and does not change portfolio allocations or C02/C06 thresholds.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-cost", type=float, default=100.0, help="USD per flagged case")
    parser.add_argument(
        "--missed-loss", type=float, default=10000.0, help="USD per missed positive"
    )
    args = parser.parse_args()
    try:
        report = evaluate(args.audit_cost, args.missed_loss)
    except ValueError as error:
        parser.error(str(error))
    dest = Path(config.DATA_DIR) / "c13_report.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_json(dest, report)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "validation_curve"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
