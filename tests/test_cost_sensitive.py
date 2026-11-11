"""Economic threshold selection must not tune on held-out outcomes."""

import numpy as np
import pytest

from challenge.c13_cost_sensitive import cost_curve, evaluate, select_threshold


def test_exact_search_matches_all_decision_boundaries_with_ties():
    labels = np.array([0, 1, 0, 1, 0])
    scores = np.array([0.9, 0.8, 0.8, 0.1, -0.2])
    curve = cost_curve(labels, scores, audit_cost=100, missed_loss=1000)
    for row in curve:
        flagged = scores > row["threshold"]
        tp = int(np.sum(flagged & (labels == 1)))
        fp = int(np.sum(flagged & (labels == 0)))
        fn = int(np.sum(~flagged & (labels == 1)))
        assert (row["tp"], row["fp"], row["fn"]) == (tp, fp, fn)
        assert row["total_loss_usd"] == (tp + fp) * 100 + fn * 1000
    assert curve[0]["flagged"] == 0
    assert curve[-1]["flagged"] == len(labels)
    selected = select_threshold(labels, scores, 100, 1000)
    assert selected["total_loss_usd"] == min(r["total_loss_usd"] for r in curve)


def test_cost_ratio_changes_policy_and_ties_prefer_fewer_audits():
    labels, scores = [0, 1], [0.9, 0.2]
    assert select_threshold(labels, scores, 100, 10000)["flagged"] == 2
    assert select_threshold(labels, scores, 100, 50)["flagged"] == 0
    assert select_threshold(labels, scores, 100, 200)["flagged"] == 0


@pytest.mark.parametrize(
    "labels,scores,audit,missed",
    [
        ([], [], 100, 1000),
        ([0, 2], [0.1, 0.2], 100, 1000),
        ([0, 1], [float("nan"), 0.2], 100, 1000),
        ([0], [0.1, 0.2], 100, 1000),
        ([0], [0.1], -1, 1000),
        ([0], [0.1], 100, float("inf")),
    ],
)
def test_invalid_economic_inputs_are_rejected(labels, scores, audit, missed):
    with pytest.raises(ValueError):
        select_threshold(labels, scores, audit, missed)


def test_validation_selects_threshold_before_untouched_test_evaluation():
    report = evaluate(n_train=1000, n_validation=500, n_test=500, n_estimators=32)
    assert report["data_type"] == "synthetic"
    assert report["splits"] == {"train": 1000, "validation": 500, "test": 500}
    assert report["selected_validation"]["total_loss_usd"] == min(
        r["total_loss_usd"] for r in report["validation_curve"]
    )
    threshold = report["selected_validation"]["threshold"]
    assert report["test"]["optimized"]["threshold"] == threshold
    for row in report["test"].values():
        assert sum(row[k] for k in ("tn", "fp", "fn", "tp")) == 500
        assert row["total_loss_usd"] == (row["tp"] + row["fp"]) * 100 + row["fn"] * 10000
    assert report["test"]["audit_none"]["flagged"] == 0
    assert report["test"]["audit_all"]["flagged"] == 500


def test_equal_scores_are_never_split_and_zero_costs_prefer_no_audits():
    curve = cost_curve([0, 1, 1], [0.5, 0.5, 0.5], 0, 0)
    assert [row["flagged"] for row in curve] == [0, 3]
    assert select_threshold([0, 1, 1], [0.5, 0.5, 0.5], 0, 0)["flagged"] == 0


def test_risk_lab_recalculates_submitted_costs_and_exposes_test_matrix():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(
        "from challenge.challenge_ui import render_cost_sensitive\nrender_cost_sensitive()",
        default_timeout=120,
    ).run()
    assert not app.exception
    initial = app.session_state["c13_report"]
    assert initial["cost_matrix_usd"]["fn"] == 10000
    assert len(app.table) == 2  # cost matrix and held-out confusion matrix
    app.number_input[0].set_value(0.0)
    app.number_input[1].set_value(0.0)
    app.button[0].click().run()
    assert not app.exception
    report = app.session_state["c13_report"]
    assert report["cost_matrix_usd"] == dict.fromkeys(("tn", "fp", "fn", "tp"), 0.0)
    assert report["selected_validation"]["flagged"] == 0
    assert report["test"]["optimized"]["total_loss_usd"] == 0
