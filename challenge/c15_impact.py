"""C15: board-level net financial gain in PKR from the C13 held-out evaluation.

Net Financial Gain = (Loss averted by true detections) - (Operational cost of
false alarms). Every number is an illustrative assumption on SYNTHETIC cases;
it is not a measured saving. Pass your own PKR assumptions to change them.

Usage: python -m challenge.c15_impact --portfolio-pkr 1000000000
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import config
from challenge.c13_cost_sensitive import evaluate as c13_evaluate
from data.files import write_json

USD_TO_PKR = 280.0  # assumption; update to the current rate before presenting


def net_gain(tp, fp, loss_averted_per_tp_pkr, audit_cost_pkr):
    """The C15 formula. A true detection averts the loss; every flag costs an audit."""
    for v in (tp, fp, loss_averted_per_tp_pkr, audit_cost_pkr):
        if not math.isfinite(v) or v < 0:
            raise ValueError("Counts and PKR amounts must be finite and not negative")
    averted = tp * loss_averted_per_tp_pkr
    false_alarm_cost = fp * audit_cost_pkr
    return {
        "loss_averted_pkr": float(averted),
        "false_alarm_cost_pkr": float(false_alarm_cost),
        "net_financial_gain_pkr": float(averted - false_alarm_cost),
    }


def evaluate(
    audit_cost_pkr=28_000.0,
    loss_per_case_pkr=2_800_000.0,
    portfolio_cases=1_000_000,
    seed=7,
    n_estimators=200,
) -> dict:
    """Run C13 with PKR-equivalent costs, then scale the held-out rates up."""
    if portfolio_cases <= 0:
        raise ValueError("portfolio_cases must be positive")
    c13 = c13_evaluate(
        audit_cost=audit_cost_pkr / USD_TO_PKR,
        missed_loss=loss_per_case_pkr / USD_TO_PKR,
        seed=seed,
        n_estimators=n_estimators,
    )
    test = c13["test"]["optimized"]
    n_test = c13["splits"]["test"]
    held_out = net_gain(test["tp"], test["fp"], loss_per_case_pkr, audit_cost_pkr)
    scale = portfolio_cases / n_test
    scaled = net_gain(test["tp"] * scale, test["fp"] * scale, loss_per_case_pkr, audit_cost_pkr)
    return {
        "challenge": "C15 Net Financial Impact Boardroom Calculation",
        "data_type": "synthetic",
        "currency": "PKR",
        "formula": "Net Financial Gain = (Loss averted by true detections) - (Operational cost of false alarms)",
        "assumptions": {
            "audit_cost_per_flag_pkr": audit_cost_pkr,
            "loss_averted_per_true_detection_pkr": loss_per_case_pkr,
            "portfolio_cases": portfolio_cases,
            "usd_to_pkr": USD_TO_PKR,
            "positive_rate": 0.01,
        },
        "held_out_counts": {"tp": test["tp"], "fp": test["fp"], "fn": test["fn"], "n": n_test},
        "held_out": held_out,
        "scaled_to_portfolio": scaled,
        "limitations": [
            "Synthetic cases and assumed PKR costs; this is an estimate, not realized savings.",
            "Scaling assumes the portfolio has the same 1% rate and score distribution as the test split.",
            "Missed positives (false negatives) are not credited; their loss is not averted.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-cost-pkr", type=float, default=28_000.0)
    parser.add_argument("--loss-per-case-pkr", type=float, default=2_800_000.0)
    parser.add_argument("--portfolio-cases", type=int, default=1_000_000)
    args = parser.parse_args()
    try:
        report = evaluate(args.audit_cost_pkr, args.loss_per_case_pkr, args.portfolio_cases)
    except ValueError as error:
        parser.error(str(error))
    write_json(Path(config.DATA_DIR) / "c15_report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
