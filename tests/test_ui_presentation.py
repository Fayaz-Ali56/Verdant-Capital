"""Presentation contracts: figures correspond to real results and cannot alter allocations."""

import copy

from challenge.challenge_ui import _confusion_html, _select_evidence_folder
from ui.charts import feature_attribution, precision_recall_curve
from ui.presentation import (
    allocation_strip,
    clean_portfolio,
    decision_reason,
    get_dashboard_metrics,
    money,
    safe,
)


def test_clean_portfolio_hides_solver_epsilon_without_changing_source():
    source = [
        {"ticker": "SOLR", "weight": 0.55},
        {"ticker": "WIND", "weight": 1.2e-16},
        {"ticker": "CASH", "weight": 0.45},
    ]
    cloned = copy.deepcopy(source)
    view = clean_portfolio(source)
    assert view[1]["weight"] == 0.0
    assert source == cloned
    assert abs(sum(x["weight"] for x in view) - 1) < 1e-8


def test_view_metrics_are_derived_from_memo_not_hardcoded():
    result = {
        "final_memo": {
            "capital": 240000,
            "portfolio": [{"ticker": "A", "weight": 0.73}, {"ticker": "CASH", "weight": 0.27}],
            "conflicts": [{}],
            "optimizer_metrics": {"expected_return_pct": 5.2, "volatility_pct": 8.1},
        }
    }
    view = get_dashboard_metrics(result)
    assert view["capital"] == 240000
    assert abs(view["allocated"] - 175200) < 0.01
    assert abs(view["cash_ratio"] - 0.27) < 1e-10
    assert view["conflicts"] == 1
    assert view["return_estimate"] == 5.2


def test_html_escapes_untrusted_data_and_unknown_policy_fails_closed():
    assert "<script>" not in safe("<script>alert(1)</script>")
    assert decision_reason("UNKNOWN_POLICY") == ("Review required", "neutral")
    assert money(80000) == "$80,000"


def test_charts_use_actual_input_series_and_c06_attributions():
    allocation = allocation_strip(
        [{"ticker": "TEST", "weight": 0.4}, {"ticker": "CASH", "weight": 0.6}]
    )
    assert "TEST 40.0%" in allocation and "CASH 60.0%" in allocation
    pr = precision_recall_curve({"recall": [0, 0.5, 1], "precision": [1, 0.5, 0.01]}, 0.01)
    assert list(pr.data[0].x) == [0, 0.5, 1]
    attrib = feature_attribution(
        {
            "attributions": [
                {"feature": "vague_language_ratio", "shap_value": 0.034},
                {"feature": "missing_baseline", "shap_value": -0.013},
            ]
        }
    )
    assert list(attrib.data[0].x) == [-0.013, 0.034]


def test_bundled_snapshot_is_marked_distinct_from_live_output(tmp_path):
    root, bundled = _select_evidence_folder(tmp_path)
    assert bundled is True
    assert (root / "c02_report.json").exists()
    for name in ["c02_report.json", "c02_pr_curve.json", "c06_report.json"]:
        (tmp_path / name).write_text("{}", encoding="utf-8")
    root, bundled = _select_evidence_folder(tmp_path)
    assert root == tmp_path and not bundled


def test_confusion_matrix_represents_honest_errors():
    html = _confusion_html({"seed": 7, "tp": 1, "fp": 8, "fn": 2, "tn": 489})
    assert "False positives" in html and "Missed positives" in html
    assert ">8<" in html and ">2<" in html
