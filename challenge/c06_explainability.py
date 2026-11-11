"""C06: three auditable SHAP explanations for the SAME C02 IsolationForest.

Run AFTER / independently of C02: python -m challenge.c06_explainability
Predictions and labels describe synthetic disclosures, not real organizations.
"""

import json
from pathlib import Path

import matplotlib

import config
from data.files import write_json

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from challenge.c02_rare_event import FEATURES, run_trial


def choose_edge_cases(trial):
    """Choose actual evaluation rows; never invent a misclassification."""
    actual = trial.y_eval
    predicted = trial.y_pred
    score = trial.scores
    used = set()
    descriptions = [
        ("true_positive", (actual == 1) & (predicted == 1)),
        ("false_positive", (actual == 0) & (predicted == 1)),
        ("false_negative", (actual == 1) & (predicted == 0)),
    ]
    cases = []
    for label, mask in descriptions:
        indexes = [int(i) for i in np.flatnonzero(mask) if int(i) not in used]
        if indexes:
            idx = min(indexes, key=lambda i: abs(float(score[i])))
            case_type = label
        else:
            # The requested error type did not occur: explain a REAL borderline row.
            candidates = [i for i in range(len(score)) if i not in used]
            if not candidates:
                raise ValueError("Need at least three distinct evaluation examples")
            idx = min(candidates, key=lambda i: abs(float(score[i])))
            case_type = "borderline_substitute_for_" + label
        used.add(idx)
        cases.append({"index": idx, "case_type": case_type, "requested_case_type": label})
    return cases


def explain_cases(trial, cases, output_dir, background_size=32, max_evals=39):
    """Explain exact anomaly score; positive SHAP increases suspicion."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    def score_func(input_data):
        return -trial.model.decision_function(
            pd.DataFrame(np.asarray(input_data), columns=FEATURES)
        )

    background = trial.X_train.sample(
        n=min(background_size, len(trial.X_train)), random_state=trial.seed
    )[FEATURES].to_numpy()
    explainer = shap.Explainer(
        score_func, background, algorithm="permutation", feature_names=FEATURES, seed=trial.seed
    )
    indexes = [case["index"] for case in cases]
    samples = trial.X_eval.iloc[indexes][FEATURES]
    explanations = explainer(samples.to_numpy(), max_evals=max_evals)
    records = []
    for j, case in enumerate(cases):
        i = case["index"]
        values = np.asarray(explanations.values[j], dtype=float).reshape(-1)
        expected = float(np.asarray(explanations.base_values[j]).reshape(-1)[0])
        total = float(expected + values.sum())
        model_score = float(trial.scores[i])
        if not np.isclose(total, model_score, rtol=1e-4, atol=1e-4):
            raise AssertionError(f"SHAP reconstruction failed: {total} vs {model_score}")
        sorted_indices = np.argsort(np.abs(values))
        labels = [FEATURES[k].replace("_", " ") for k in sorted_indices]
        strengths = values[sorted_indices]
        # Polished offline PNG; same numerical explanation as the interactive Risk Lab.
        fig, ax = plt.subplots(figsize=(8.8, 4.5), facecolor="#101C24")
        ax.set_facecolor("#101C24")
        ax.barh(
            labels,
            strengths,
            color=["#F0A8A8" if v >= 0 else "#8CE1B6" for v in strengths],
            height=0.68,
        )
        ax.axvline(0, linewidth=1.0, color="#C6D5CE", alpha=0.6)
        ax.grid(axis="x", color="#37505B", alpha=0.4, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.set_xlabel(
            "SHAP impact on anomaly score · positive = greater suspicion",
            color="#B8CAC1",
            labelpad=13,
        )
        ax.set_title(
            f"{case['case_type'].replace('_', ' ').title()}  /  Score: {model_score:+.4f}",
            color="#EEF6F1",
            fontsize=13,
            fontweight="bold",
            loc="left",
            pad=18,
        )
        ax.tick_params(axis="both", colors="#CBDDD3", labelsize=9)
        for spine in ax.spines.values():
            spine.set_visible(False)
        fig.tight_layout(pad=1.6)
        plot_name = f"c06_case_{j + 1}.png"
        fig.savefig(output_dir / plot_name, dpi=150, bbox_inches="tight")
        plt.close(fig)
        records.append(
            {
                "case_id": j + 1,
                "case_type": case["case_type"],
                "requested_case_type": case["requested_case_type"],
                "eval_index": int(i),
                "data_type": "synthetic",
                "true_label": int(trial.y_eval[i]),
                "predicted_label": int(trial.y_pred[i]),
                "decision": "flag_for_review" if int(trial.y_pred[i]) else "not_flagged",
                "anomaly_score": round(model_score, 8),
                "decision_threshold": 0.0,
                "base_score": round(expected, 8),
                "reconstructed_score": round(total, 8),
                "feature_values": {name: float(samples.iloc[j][name]) for name in FEATURES},
                "attributions": [
                    {
                        "feature": FEATURES[k],
                        "shap_value": round(float(values[k]), 8),
                        "direction": "raises_suspicion" if values[k] > 0 else "lowers_suspicion",
                    }
                    for k in np.argsort(-np.abs(values))
                ],
                "plot": plot_name,
            }
        )
    return records


def main():
    trial = run_trial(seed=7)
    cases = choose_edge_cases(trial)
    output_dir = Path(config.DATA_DIR) / "c06_plots"
    records = explain_cases(trial, cases, output_dir)
    report = {
        "challenge": "C06 Explainability and Feature Attribution",
        "data_type": "synthetic",
        "model": "IsolationForest anomaly score from C02 seed 7",
        "method": "Model-agnostic permutation SHAP",
        "feature_count": len(FEATURES),
        "threshold": 0.0,
        "cases": records,
        "limitations": [
            "Feature values are synthetic and are not taken from company documents.",
            "SHAP values explain this model's anomaly score, not causality or fraud probability.",
            "Predictions are review flags, not regulatory approvals or rejections.",
        ],
    }
    dest = Path(config.DATA_DIR) / "c06_report.json"
    dest.parent.mkdir(exist_ok=True, parents=True)
    write_json(dest, report)
    print(
        json.dumps(
            {
                "report": str(dest),
                "cases": [
                    {"type": r["case_type"], "plot": r["plot"], "score": r["anomaly_score"]}
                    for r in records
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
