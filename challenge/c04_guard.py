"""C04: out-of-bounds / hallucination guard in front of the C02 anomaly model.

Hard rules reject physically or logically impossible values. Soft rules flag
values that are possible but far outside what the model was trained on, so the
pipeline says "low confidence" instead of returning a confident wrong score.
All inputs here are synthetic; no real sensor or issuer data is used.

Usage: python -m challenge.c04_guard
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import config
from challenge.c02_rare_event import FEATURES, run_trial
from data.files import write_json

# field -> (min, max, description). Hard limits: outside means impossible.
HARD_LIMITS = {
    "vague_language_ratio": (-1.0, 2.0, "share of vague wording"),
    "sentiment_gap": (-1.0, 2.0, "tone gap between claim and evidence"),
    "missing_baseline": (0, 1, "binary flag"),
    "no_third_party_verif": (0, 1, "binary flag"),
    "capex_backing_ratio": (-1.0, 3.0, "capex backing the claim"),
    "intensity_anomaly": (-2.0, 3.0, "emissions intensity anomaly"),
    "solar_irradiance_wm2": (0.0, 1500.0, "W/m2; cannot be negative"),
    "carbon_offset_reduction_pct": (0.0, 100.0, "cannot offset more than 100%"),
    "latitude": (-90.0, 90.0, "degrees"),
    "longitude": (-180.0, 180.0, "degrees"),
}
BINARY = {"missing_baseline", "no_third_party_verif"}
SOFT_Z = 6.0  # beyond this many training std-devs: low confidence


def fit_reference(X_train):
    """Training mean/std per model feature, used by the soft check."""
    return {c: (float(X_train[c].mean()), float(X_train[c].std()) or 1.0) for c in FEATURES}


def _as_float(value):
    """Finite-safe float conversion; None when the value is not a usable number."""
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def validate(record: dict, reference: dict | None = None) -> dict:
    """Return status accept | low_confidence | reject plus the reasons."""
    reasons, soft = [], []
    if not isinstance(record, dict):
        return {"status": "reject", "reasons": ["record is not a mapping"], "soft": []}
    for name in FEATURES:
        if name not in record:
            reasons.append(f"{name}: missing required field")
    for name, value in record.items():
        if name not in HARD_LIMITS:
            continue
        lo, hi, _ = HARD_LIMITS[name]
        number = _as_float(value)
        if number is None:
            reasons.append(f"{name}: not a usable number")
        elif not math.isfinite(number):
            reasons.append(f"{name}: NaN or infinite")
        elif not lo <= number <= hi:
            reasons.append(f"{name}: {number:g} outside [{lo}, {hi}]")
        elif name in BINARY and number not in (0.0, 1.0):
            reasons.append(f"{name}: must be 0 or 1")
        elif reference and name in reference:
            mean, std = reference[name]
            if abs(number - mean) / std > SOFT_Z:
                soft.append(f"{name}: {number:g} is >{SOFT_Z:g} std from training data")
    if reasons:
        return {"status": "reject", "reasons": reasons, "soft": soft}
    if soft:
        return {"status": "low_confidence", "reasons": [], "soft": soft}
    return {"status": "accept", "reasons": [], "soft": []}


def guarded_score(model, record: dict, reference: dict | None = None) -> dict:
    """Score only if the record passes the guard; otherwise refuse to guess."""
    check = validate(record, reference)
    if check["status"] == "reject":
        return {**check, "score": None, "flag": "REJECTED_INVALID_INPUT"}
    row = pd.DataFrame([{f: float(record[f]) for f in FEATURES}])
    score = float(-model.decision_function(row)[0])
    flag = "LOW_CONFIDENCE_HUMAN_REVIEW" if check["status"] == "low_confidence" else "OK"
    return {**check, "score": score, "flag": flag}


def _valid_base():
    return {
        "vague_language_ratio": 0.15,
        "sentiment_gap": 0.10,
        "missing_baseline": 0,
        "no_third_party_verif": 0,
        "capex_backing_ratio": 0.55,
        "intensity_anomaly": 0.05,
        "solar_irradiance_wm2": 800.0,
        "carbon_offset_reduction_pct": 40.0,
        "latitude": 24.86,
        "longitude": 67.00,
    }


EDGE_CASES = {
    "negative solar irradiance": {"solar_irradiance_wm2": -250.0},
    "200% carbon-offset reduction": {"carbon_offset_reduction_pct": 200.0},
    "invalid latitude 95": {"latitude": 95.0},
    "NaN ratio from broken sensor": {"vague_language_ratio": float("nan")},
    "non-binary flag value 7": {"missing_baseline": 7},
    "extreme but possible outlier": {"intensity_anomaly": 2.9},
}


def evaluate(seed=7, n_train=5000, n_eval=500, n_estimators=64) -> dict:
    trial = run_trial(seed=seed, n_train=n_train, n_eval=n_eval, n_estimators=n_estimators)
    reference = fit_reference(trial.X_train)
    cases = []
    for name, change in EDGE_CASES.items():
        record = {**_valid_base(), **change}
        naive = None
        try:  # what an unguarded pipeline does with the same row
            row = pd.DataFrame([{f: float(record[f]) for f in FEATURES}])
            naive = float(-trial.model.decision_function(row)[0])
            naive = naive if math.isfinite(naive) else None
        except ValueError:
            naive = None
        guarded = guarded_score(trial.model, record, reference)
        cases.append(
            {
                "case": name,
                "unguarded_score": naive,
                "guarded_status": guarded["status"],
                "guarded_flag": guarded["flag"],
                "reasons": guarded["reasons"] + guarded["soft"],
            }
        )
    clean = guarded_score(trial.model, _valid_base(), reference)
    handled = sum(c["guarded_status"] != "accept" for c in cases)
    return {
        "challenge": "C04 Out-of-Bounds & Hallucination Guard",
        "data_type": "synthetic",
        "edge_cases_injected": len(cases),
        "edge_cases_handled": handled,
        "confident_wrong_predictions": len(cases) - handled,
        "clean_record_status": clean["status"],
        "cases": cases,
        "limitations": [
            "Hard bounds are domain assumptions written for this prototype.",
            "Soft check uses training mean/std only; it is not a full OOD detector.",
        ],
    }


def main():
    report = evaluate()
    dest = Path(config.DATA_DIR) / "c04_report.json"
    write_json(dest, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
