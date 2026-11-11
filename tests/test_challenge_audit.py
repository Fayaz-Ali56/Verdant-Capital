"""Regression tests for C02/C06 reproducibility and audit integrity."""

import numpy as np

from challenge.c02_rare_event import evaluate, make_data, run_trial
from challenge.c06_explainability import choose_edge_cases, explain_cases


def test_99_to_1_split_exactly():
    X, y = make_data(5000, 0.01, np.random.default_rng(7))
    assert len(X) == 5000
    assert int(sum(y)) == 50
    assert int(sum(1 - y)) == 4950


def test_report_contains_threshold_metrics_and_evidence(tmp_path):
    report, curve = evaluate(seeds=[7], n_train=1000, n_eval=500, n_estimators=32)
    entry = report["trials"][0]
    assert report["data_type"] == "synthetic"
    assert entry["positive_count"] == 5
    assert entry["negative_count"] == 495
    assert entry["tp"] + entry["fn"] == 5
    assert entry["tn"] + entry["fp"] == 495
    assert 0 <= entry["average_precision"] <= 1
    assert entry["predicted_positives"] > 0
    assert len(curve["precision"]) == len(curve["recall"])


def test_c06_uses_same_model_score_and_explains_three_real_eval_rows(tmp_path):
    trial = run_trial(seed=7, n_train=1200, n_eval=500, n_estimators=32)
    cases = choose_edge_cases(trial)
    assert len(cases) == 3
    assert len({c["index"] for c in cases}) == 3
    records = explain_cases(trial, cases, tmp_path, background_size=10, max_evals=13)
    assert len(records) == 3
    assert all(rec["data_type"] == "synthetic" for rec in records)
    for rec in records:
        assert abs(rec["reconstructed_score"] - rec["anomaly_score"]) < 1e-5
        assert (tmp_path / rec["plot"]).exists()
        assert len(rec["attributions"]) == 6
