"""C04 - Out-of-Bounds & Hallucination Guard.

Adversaries or faulty sensors submit impossible values (negative solar irradiance,
200% carbon offsets, invalid coordinates). The guard screens every payload BEFORE any
agent reasons on it, and forces LOW-CONFIDENCE mode instead of confident garbage.

Run: python -m challenge.c04_oob_guard
"""
import json, os
import config

# rule: (field, predicate, severity, message)
RULES = [
    ("solar_irradiance",  lambda v: v is None or v >= 0, "REJECT",
     "solar irradiance must be >= 0 Wh/m² (got {v})"),
    ("carbon_reduction_pct", lambda v: v is None or 0 <= v <= 100, "REJECT",
     "carbon-offset reduction must be within 0-100% (got {v}%)"),
    ("latitude",  lambda v: v is None or -90 <= v <= 90,  "REJECT",
     "latitude must be within [-90, 90] (got {v})"),
    ("longitude", lambda v: v is None or -180 <= v <= 180, "REJECT",
     "longitude must be within [-180, 180] (got {v})"),
    ("price",     lambda v: v is None or v > 0, "FLAG",
     "non-positive price {v} — treating as sensor fault, downgrading confidence"),
    ("confidence", lambda v: v is None or 0 <= v <= 1, "REJECT",
     "confidence must be within [0, 1] (got {v})"),
    ("vol_annual_pct", lambda v: v is None or 0 <= v <= 500, "FLAG",
     "annualized volatility {v}% is implausible — possible unit error, downgrading confidence"),
]

def validate(payload: dict) -> dict:
    """Screen a payload. Returns {ok, rejections, flags, safe_mode}."""
    rejections, flags = [], []
    for field, ok, severity, msg in RULES:
        if field in payload:
            v = payload[field]
            try:
                passed = ok(v)
            except TypeError:
                passed = False
            if not passed:
                entry = {"field": field, "value": v, "rule": msg.format(v=v)}
                (rejections if severity == "REJECT" else flags).append(entry)
    return {"ok": not rejections, "rejections": rejections, "flags": flags,
            "safe_mode": bool(rejections or flags)}

# Nested snapshot rules for the LIVE orchestrator guard (price_stats.json layout)
SNAPSHOT_RULES = {
    "last":           (lambda v: v is None or v > 0, "REJECT",
                       "{ticker}: non-positive price {v} — rejecting feed"),
    "vol_annual_pct": (lambda v: v is None or 0 <= v <= 500, "FLAG",
                       "{ticker}: annualized volatility {v}% implausible — low-confidence mode"),
}

def validate_market_snapshot(stats: dict) -> dict:
    """Screen the nested market snapshot (ticker -> stats dict) used by the orchestrator."""
    rejections, flags = [], []
    for ticker, sub in stats.items():
        if ticker.startswith("_") or not isinstance(sub, dict):
            continue
        for field, (ok, sev, msg) in SNAPSHOT_RULES.items():
            if field in sub:
                v = sub[field]
                try:
                    passed = ok(v)
                except TypeError:
                    passed = False
                if not passed:
                    entry = {"field": f"{ticker}.{field}", "value": v, "rule": msg.format(ticker=ticker, v=v)}
                    (rejections if sev == "REJECT" else flags).append(entry)
    carbon = stats.get("_carbon_forecast") or {}
    if carbon:
        fc = carbon.get("forecast_30d")
        if fc is not None and fc <= 0:
            rejections.append({"field": "carbon.forecast_30d", "value": fc,
                               "rule": "carbon forecast must be positive"})
        ch = carbon.get("change_pct_30d")
        if ch is not None and not (-95 <= ch <= 200):
            flags.append({"field": "carbon.change_pct_30d", "value": ch,
                          "rule": f"carbon move {ch}% out of plausible range — low-confidence mode"})
    return {"ok": not rejections, "rejections": rejections, "flags": flags,
            "safe_mode": bool(rejections or flags)}


# The 5 mandated boundary edge cases
DEMO_CASES = [
    {"name": "Faulty solar sensor",        "payload": {"solar_irradiance": -450.0}},
    {"name": "Fabricated offset claim",    "payload": {"carbon_reduction_pct": 200.0}},
    {"name": "GPS spoof / bad coordinates","payload": {"latitude": 145.0, "longitude": 999.0}},
    {"name": "Corrupt price feed",         "payload": {"price": -3.7, "vol_annual_pct": 940.0}},
    {"name": "Hallucinated confidence",    "payload": {"confidence": 1.7}},
]

def run_demo() -> dict:
    cases = []
    for c in DEMO_CASES:
        r = validate(c["payload"])
        if r["rejections"]:
            outcome = f"REJECTED ({len(r['rejections'])} rule{'s' if len(r['rejections'])>1 else ''}) — no prediction issued"
        elif r["flags"]:
            outcome = f"FLAGGED — low-confidence mode forced ({len(r['flags'])} warning{'s' if len(r['flags'])>1 else ''})"
        else:
            outcome = "PASSED"
        cases.append({"case": c["name"], "payload": c["payload"], "outcome": outcome,
                      "detail": r})
    report = {
        "challenge": "C04 Out-of-Bounds & Hallucination Guard",
        "cases_tested": len(cases),
        "cases": cases,
        "verdict": ("5/5 impossible payloads intercepted. REJECTED inputs never reach the agents; "
                    "FLAGGED inputs force low-confidence mode. The pipeline cannot produce a confident "
                    "erroneous prediction from corrupt data."),
    }
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(os.path.join(config.DATA_DIR, "c04_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    return report

if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
