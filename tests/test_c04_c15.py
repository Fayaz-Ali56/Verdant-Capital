"""C04 guard and C15 PKR impact regression tests."""

import math

import pytest

from challenge.c04_guard import EDGE_CASES, _valid_base, validate
from challenge.c04_guard import evaluate as c04_evaluate
from challenge.c15_impact import evaluate as c15_evaluate
from challenge.c15_impact import net_gain


def test_clean_record_is_accepted():
    assert validate(_valid_base())["status"] == "accept"


@pytest.mark.parametrize("name", [n for n in EDGE_CASES if n != "extreme but possible outlier"])
def test_impossible_values_are_rejected(name):
    assert validate({**_valid_base(), **EDGE_CASES[name]})["status"] == "reject"


def test_missing_field_and_wrong_type_rejected():
    record = _valid_base()
    del record["sentiment_gap"]
    assert validate(record)["status"] == "reject"
    assert validate({**_valid_base(), "latitude": "north"})["status"] == "reject"
    assert validate("not a dict")["status"] == "reject"


def test_pipeline_never_returns_confident_score_for_bad_input():
    report = c04_evaluate(n_train=1500, n_eval=300, n_estimators=32)
    assert report["edge_cases_injected"] >= 5
    assert report["confident_wrong_predictions"] == 0
    assert report["clean_record_status"] == "accept"
    for case in report["cases"]:
        assert case["guarded_flag"] != "OK"


def test_net_gain_formula():
    out = net_gain(tp=10, fp=20, loss_averted_per_tp_pkr=1000, audit_cost_pkr=100)
    assert out["loss_averted_pkr"] == 10000
    assert out["false_alarm_cost_pkr"] == 2000
    assert out["net_financial_gain_pkr"] == 8000
    with pytest.raises(ValueError):
        net_gain(-1, 0, 1, 1)


def test_c15_report_is_consistent():
    report = c15_evaluate(portfolio_cases=100_000, n_estimators=32)
    held, scaled = report["held_out"], report["scaled_to_portfolio"]
    assert math.isclose(
        held["net_financial_gain_pkr"], held["loss_averted_pkr"] - held["false_alarm_cost_pkr"]
    )
    assert scaled["net_financial_gain_pkr"] > 0
    with pytest.raises(ValueError):
        c15_evaluate(portfolio_cases=0)


@pytest.mark.parametrize("bad", [10**400, -(10**400), float("inf"), "1", None, [], True, 1 + 2j])
def test_guard_never_crashes_on_garbage_values(bad):
    for field in ("latitude", "missing_baseline", "vague_language_ratio"):
        assert validate({**_valid_base(), field: bad})["status"] == "reject"


def test_net_gain_rejects_nan_and_infinity():
    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            net_gain(bad, 1, 1, 1)
        with pytest.raises(ValueError):
            net_gain(1, 1, bad, 1)
