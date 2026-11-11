"""Transparent 30-day SIMULATION of adaptation. No real misconduct allegations.

Simulated accuracy is NOT a measured improvement on real finance outcomes.
Run: python -m data.feedback_backtest
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import config
from data.feedback_store import agent_weights, record_outcome, save_recommendation
from data.files import write_json

DAYS = 30


def main():
    root = Path(config.DATA_DIR)
    root.mkdir(parents=True, exist_ok=True)
    # Separate, deliberately disposable demo DB; user feedback.db untouched.
    # Build a fresh simulation privately; replace only its completed database.
    with TemporaryDirectory(prefix=".simulation-", dir=root) as folder:
        database = Path(folder) / "simulation_feedback.db"
        rng = np.random.default_rng(42)
        timeline = []
        for day in range(1, DAYS + 1):
            rec_id = save_recommendation(
                f"Synthetic scenario day {day}",
                {"mode": "synthetic_demo", "day": day},
                db_path=database,
                mode="demo",
            )
            for ticker in ("SOLR", "WIND", "FOSS"):
                for agent in ("esg_verifier", "market_analyst"):
                    # Predetermined fictional skill differences, not measured market outcomes.
                    skill = 0.78 if agent == "esg_verifier" else 0.62
                    right = int(rng.random() < skill)
                    record_outcome(
                        rec_id,
                        ticker,
                        agent,
                        "demo_classification",
                        0.0,
                        correct=right,
                        db_path=database,
                        label_source="synthetic_demo",
                        case_key=f"sim-{day}",
                    )
            weights = agent_weights(db_path=database, allowed_sources={"synthetic_demo"})
            timeline.append(
                {
                    "day": day,
                    "esg_weight": weights["esg_verifier"],
                    "mkt_weight": weights["market_analyst"],
                }
            )
        database.replace(root / "simulation_feedback.db")
    report = {
        "mode": "synthetic",
        "source": "seeded Bernoulli outcomes (not external truth)",
        "description": "Demonstrates feedback update mechanics, not real prediction accuracy.",
        "days": timeline,
    }
    write_json(root / "feedback_timeline.json", report)
    print(json.dumps({"mode": report["mode"], "last_day": timeline[-1]}, indent=2))


if __name__ == "__main__":
    main()
