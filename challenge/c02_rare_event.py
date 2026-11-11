"""C02 - Severe Class Imbalance / Rare-Event Stress: greenwashing detection at 99:1 skew.

Story: <1% of ESG disclosures are fraudulent. A naive model that approves everything
scores 99% accuracy and is completely useless. We detect the rare positives with a
calibrated anomaly detector and PROVE it with PR-AUC under the mandated 99:1 split.

Run: python -m challenge.c02_rare_event
"""
import json, os
import numpy as np
import pandas as pd
import config

N_TRAIN, N_EVAL = 20_000, 5_000
POS_RATE = 0.01
SEED = 7

FEATURES = ["vague_language_ratio", "sentiment_gap", "missing_baseline",
            "no_third_party_verif", "capex_backing_ratio", "intensity_anomaly"]

def make_data(n, pos_rate, rng):
    """Synthetic disclosure features. Positives (greenwashed) live in a shifted region."""
    n_pos = int(n * pos_rate)
    neg = pd.DataFrame({
        "vague_language_ratio":  rng.normal(0.15, 0.05, n - n_pos),
        "sentiment_gap":         rng.normal(0.10, 0.05, n - n_pos),
        "missing_baseline":      rng.binomial(1, 0.08, n - n_pos),
        "no_third_party_verif":  rng.binomial(1, 0.10, n - n_pos),
        "capex_backing_ratio":   rng.normal(0.55, 0.15, n - n_pos),
        "intensity_anomaly":     rng.normal(0.05, 0.05, n - n_pos),
    })
    pos = pd.DataFrame({
        "vague_language_ratio":  rng.normal(0.38, 0.22, n_pos),
        "sentiment_gap":         rng.normal(0.40, 0.24, n_pos),
        "missing_baseline":      rng.binomial(1, 0.50, n_pos),
        "no_third_party_verif":  rng.binomial(1, 0.62, n_pos),
        "capex_backing_ratio":   rng.normal(0.32, 0.22, n_pos),
        "intensity_anomaly":     rng.normal(0.48, 0.30, n_pos),
    })
    X = pd.concat([neg, pos], ignore_index=True)
    y = np.array([0] * (n - n_pos) + [1] * n_pos)
    idx = rng.permutation(len(X))
    return X.iloc[idx].reset_index(drop=True), y[idx]

def main():
    from sklearn.ensemble import IsolationForest
    from sklearn.metrics import precision_recall_curve, auc, average_precision_score
    from sklearn.model_selection import train_test_split

    seeds = [7, 13, 21, 34, 55]
    pr_aucs, aps, prec1s, lifts, curves = [], [], [], [], []
    for sd in seeds:
        rng = np.random.default_rng(sd)
        X, y = make_data(N_TRAIN + N_EVAL, POS_RATE, rng)
        X_tr, X_ev, y_tr, y_ev = train_test_split(X, y, test_size=N_EVAL / (N_TRAIN + N_EVAL),
                                                 stratify=y, random_state=sd)
        detector = IsolationForest(n_estimators=200, contamination=POS_RATE, random_state=sd)
        detector.fit(X_tr)
        score = -detector.decision_function(X_ev)

        prec, rec, thr = precision_recall_curve(y_ev, score)
        pr_aucs.append(auc(rec, prec))
        aps.append(average_precision_score(y_ev, score))

        flag_n = max(int(0.01 * len(y_ev)), 1)
        flagged = np.argsort(-score)[:flag_n]
        p1 = float(y_ev[flagged].sum()) / flag_n
        prec1s.append(p1)
        lifts.append(p1 / POS_RATE)
        step = max(1, len(rec) // 200)
        curves.append({"recall": [round(float(r), 4) for r in rec[::step]],
                       "precision": [round(float(p), 4) for p in prec[::step]]})

    mean_pr = float(np.mean(pr_aucs)); std_pr = float(np.std(pr_aucs))
    mean_p1 = float(np.mean(prec1s)); mean_lift = float(np.mean(lifts))
    majority_acc = 1 - POS_RATE
    curve = curves[0]  # representative curve for the dashboard

    report = {
        "challenge": "C02 Severe Class Imbalance / Rare-Event Stress (99:1)",
        "data_source": "SYNTHETIC - disclosure features are generated from hand-chosen distributions; "
                      "no real labelled greenwashing dataset is used. Results prove the evaluation "
                      "harness and imbalance handling, not real-world detection accuracy.",
        "methodology": f"5 random seeds x {N_EVAL:,} eval samples each, 1% positives",
        "seeds": seeds,
        "pr_auc_mean": round(mean_pr, 4), "pr_auc_std": round(std_pr, 4),
        "average_precision_mean": round(float(np.mean(aps)), 4),
        "positive_rate": POS_RATE,
        "eval_size": N_EVAL,
        "positives_per_eval": int(N_EVAL * POS_RATE),
        "detector": "IsolationForest(200 trees) anomaly score, unsupervised fit",
        "majority_class_accuracy_trap": round(majority_acc, 4),
        "precision_at_1pct_flag_rate": round(mean_p1, 4),
        "lift_over_random": round(mean_lift, 1),
        "verdict": (f"[Synthetic data] Across 5 seeds at 99:1 skew: PR-AUC {mean_pr:.3f} ± {std_pr:.3f} "
                    f"vs random-guess baseline {POS_RATE:.3f}. A useless approve-everything model "
                    f"hits {majority_acc:.0%} accuracy — we measure PR-AUC instead, so collapse is "
                    f"impossible to hide. At a 1% audit budget, {mean_p1:.0%} of flagged cases are "
                    f"true fraud ({mean_lift:.0f}x lift)."),
        "features": FEATURES,
    }
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(os.path.join(config.DATA_DIR, "c02_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    with open(os.path.join(config.DATA_DIR, "c02_pr_curve.json"), "w") as f:
        json.dump(curve, f)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
