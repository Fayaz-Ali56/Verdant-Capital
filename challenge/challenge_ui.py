"""C02, C06 and C13 model assurance cockpit. Import safe outside Streamlit."""

from __future__ import annotations

import json
from pathlib import Path

from ui.charts import feature_attribution, finish, precision_recall_curve
from ui.presentation import chip, matrix_html, safe, section, stat

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "assets" / "benchmark_snapshot"


def _select_evidence_folder(data_dir: str | Path) -> tuple[Path, bool]:
    """Prefer freshly generated results; otherwise show clearly labeled bundled sample."""
    live = Path(data_dir)
    files = ["c02_report.json", "c02_pr_curve.json", "c06_report.json"]
    if all((live / path).exists() for path in files):
        return live, False
    if all((SAMPLE_DIR / path).exists() for path in files):
        return SAMPLE_DIR, True
    return live, False


def _confusion_html(trial: dict) -> str:
    tp, fp, fn, tn = (int(trial.get(n, 0)) for n in ["tp", "fp", "fn", "tn"])
    return f"""<div class="vc-confusion" role="group" aria-label="Held-out confusion matrix">
      <div class="vc-confusion-heading">Holdout predictions <span>Seed {int(trial["seed"])}</span></div>
      <div class="vc-matrix-grid">
        <div class="vc-matrix-item vc-matrix-tp"><strong>{tp:,}</strong><span>True positives</span></div>
        <div class="vc-matrix-item vc-matrix-fp"><strong>{fp:,}</strong><span>False positives</span></div>
        <div class="vc-matrix-item vc-matrix-fn"><strong>{fn:,}</strong><span>Missed positives</span></div>
        <div class="vc-matrix-item vc-matrix-tn"><strong>{tn:,}</strong><span>True negatives</span></div>
      </div>
      <div class="vc-matrix-caption">Actual label and model flag, held-out split. An error is shown, not hidden.</div>
    </div>"""


def _render_c02_c06(data_dir: str = "data_cache") -> None:
    import pandas as pd
    import streamlit as st

    root, bundled = _select_evidence_folder(data_dir)
    st.markdown(
        section(
            "Model assurance",
            "Rare-event robustness and transparent, inspectable explanations.",
            "C02 / C06 evaluation",
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="vc-note"><strong>Controlled scientific benchmark.</strong> Model inputs and labels are <strong>synthetic ESG disclosure features</strong>. Numbers below are not validated greenwashing-detection accuracy on real issuers.</div>',
        unsafe_allow_html=True,
    )
    if bundled:
        st.caption(
            "Showing a bundled, reproducible synthetic benchmark snapshot. Run the evaluation scripts to generate results on this machine."
        )

    p_report, p_curve = root / "c02_report.json", root / "c02_pr_curve.json"
    if not (p_report.exists() and p_curve.exists()):
        st.info(
            "Evaluation not generated. Run `python -m challenge.c02_rare_event` and `python -m challenge.c06_explainability`."
        )
        return
    try:
        report = json.loads(p_report.read_text(encoding="utf-8"))
        curve = json.loads(p_curve.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        st.error(
            f"Benchmark report could not be loaded: {type(err).__name__}. Re-run evaluation scripts."
        )
        return

    st.markdown(
        section(
            "C02 — Rare-event stress",
            "A held-out 99:1 imbalance, scored beyond majority-class accuracy.",
            "Isolation Forest · Five seeds",
        ),
        unsafe_allow_html=True,
    )
    cards = [
        stat(
            "Mean PR-AUC",
            f"{report.get('pr_auc_mean', 0):.3f}",
            "Across independent seeds",
            "green",
        ),
        stat(
            "Average precision",
            f"{report.get('average_precision_mean', 0):.3f}",
            "Ranking quality above 1% baseline",
        ),
        stat(
            "Recall at threshold",
            f"{report.get('recall_mean', 0):.1%}",
            "Actual positives detected",
        ),
        stat(
            "Imbalance",
            f"{int(report.get('negative_count', 0)):,}:{int(report.get('positive_count', 0)):,}",
            "Held-out negatives : positives",
            "gold",
        ),
    ]
    for col, html in zip(st.columns(4), cards, strict=False):
        with col:
            st.markdown(html, unsafe_allow_html=True)
    left, right = st.columns([1.45, 0.9], gap="large")
    with left:
        st.markdown(
            section(
                "Precision–recall profile",
                "The relevant comparison for a rare-event classification problem.",
            ),
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            precision_recall_curve(curve, float(report.get("positive_rate", 0.01))),
            width="stretch",
            config={"displayModeBar": False},
        )
        st.caption(
            "Reference: the dotted line is approximately the 1% prevalence baseline for random ranking. PR-AUC is not classification accuracy."
        )
    with right:
        st.markdown(
            section(
                "Evidence of detection",
                "Held-out classification at the documented operating threshold.",
            ),
            unsafe_allow_html=True,
        )
        trial = (report.get("trials") or [{}])[0]
        if trial:
            st.markdown(_confusion_html(trial), unsafe_allow_html=True)
        if report.get("no_majority_collapse"):
            st.markdown(
                '<div class="vc-note"><strong>Passed controlled collapse check.</strong> The model detected positive examples in every evaluated split.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.error(
                "At least one split failed the collapse check. Review the saved per-seed results."
            )
    with st.expander("Inspect methodology and per-seed model metrics"):
        st.write(report.get("methodology", ""))
        st.dataframe(pd.DataFrame(report.get("trials", [])), width="stretch", hide_index=True)
        st.download_button(
            "Download C02 evaluation JSON",
            p_report.read_text(encoding="utf-8"),
            "c02_evaluation.json",
            mime="application/json",
        )

    st.markdown(
        section(
            "C06 — Explainability audit",
            "Three actual held-out cases from the same C02 model, with feature contributions.",
            "Permutation SHAP",
        ),
        unsafe_allow_html=True,
    )
    p_c06 = root / "c06_report.json"
    if not p_c06.exists():
        st.info(
            "Run `python -m challenge.c06_explainability` to generate SHAP feature-attribution reports."
        )
        return
    try:
        c06 = json.loads(p_c06.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        st.error(
            "C06 report could not be read. Regenerate it with `python -m challenge.c06_explainability`."
        )
        return
    records = c06.get("cases", [])
    if not records:
        st.warning("No explainable cases are present in the C06 audit report.")
        return
    summary_cards = []
    for record in records[:3]:
        case_name = record.get("case_type", "unknown").replace("_", " ").title()
        label = "Flagged" if record.get("predicted_label") == 1 else "Not flagged"
        summary_cards.append((case_name, label, record))
    for col, (name, label, record) in zip(st.columns(3), summary_cards, strict=False):
        with col:
            tone = "positive" if record.get("case_type") == "true_positive" else "warning"
            st.markdown(
                f'<div class="vc-case"><div class="vc-case-head"><div class="vc-case-name">{safe(name)}</div>{chip(label, tone)}</div>'
                f'<div class="vc-case-meta">Observed label: {"positive" if record.get("true_label") else "negative"}<br>Score: {float(record.get("anomaly_score", 0)):+.4f} · Cutoff: {float(record.get("decision_threshold", 0)):+.4f}</div></div>',
                unsafe_allow_html=True,
            )
    tabs = st.tabs([r.get("case_type", "Case").replace("_", " ").title() for r in records[:3]])
    for case_tab, record in zip(tabs, records[:3], strict=False):
        with case_tab:
            left, right = st.columns([1.45, 0.65], gap="large")
            with left:
                st.markdown(
                    section(
                        "Feature contribution",
                        "Positive bars increase the anomaly score; negative bars reduce it.",
                    ),
                    unsafe_allow_html=True,
                )
                st.plotly_chart(
                    feature_attribution(record), width="stretch", config={"displayModeBar": False}
                )
            with right:
                st.markdown(
                    section("Decision record", "The numerical decision and its limitations."),
                    unsafe_allow_html=True,
                )
                st.metric("Model anomaly score", f"{float(record.get('anomaly_score', 0)):+.4f}")
                st.metric(
                    "Decision threshold", f"{float(record.get('decision_threshold', 0)):+.4f}"
                )
                top = (record.get("attributions") or [{}])[0]
                st.markdown(
                    f"**Dominant influence**  \n{top.get('feature', 'unknown').replace('_', ' ').title()}"
                )
                st.caption(
                    "This is a model attribution, not a causal explanation of fraud or regulatory approval."
                )
                if record.get("case_type", "").startswith("borderline_substitute"):
                    st.warning(
                        "No example of the requested error occurred; this is a disclosed real borderline substitute."
                    )
                path = root / "c06_plots" / Path(str(record.get("plot", ""))).name
                if path.is_file() and path.resolve().is_relative_to((root / "c06_plots").resolve()):
                    st.download_button(
                        "Export attribution PNG",
                        path.read_bytes(),
                        file_name=path.name,
                        mime="image/png",
                        key=f"c06_download_{record.get('case_id', 0)}",
                    )
            with st.expander("Feature values and additive reconstruction"):
                st.dataframe(
                    pd.DataFrame(record.get("attributions", [])), hide_index=True, width="stretch"
                )
                st.write(
                    "Baseline + SHAP sum = reconstructed score; numerical consistency checked by the C06 pipeline."
                )
                st.json(
                    {
                        key: record.get(key)
                        for key in [
                            "base_score",
                            "reconstructed_score",
                            "anomaly_score",
                            "feature_values",
                            "eval_index",
                        ]
                    }
                )
    st.caption(
        "SHAP identifies contributors to the Isolation Forest anomaly score; it does not prove a company is fraudulent, establish causality, or provide a calibrated fraud probability."
    )
    st.download_button(
        "Download complete C06 audit (JSON)",
        p_c06.read_text(encoding="utf-8"),
        "c06_shap_audit.json",
        mime="application/json",
    )


def render_cost_sensitive() -> None:
    import pandas as pd
    import plotly.graph_objects as go
    import streamlit as st

    from challenge.c13_cost_sensitive import evaluate

    st.markdown(
        section(
            "C13 — Decision economics",
            "Choose an audit threshold using financial consequences, then evaluate it on untouched cases.",
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        "Synthetic 99:1 benchmark · Illustrative USD assumptions · This experiment does not change investment allocations."
    )
    with st.form("c13_costs"):
        left, right = st.columns(2)
        audit = left.number_input(
            "Audit cost per flagged case (USD)",
            min_value=0.0,
            max_value=1e9,
            value=100.0,
            step=25.0,
            format="%.2f",
        )
        missed = right.number_input(
            "Financial loss per missed positive (USD)",
            min_value=0.0,
            max_value=1e9,
            value=10000.0,
            step=1000.0,
            format="%.2f",
        )
        submitted = st.form_submit_button("Optimize economic threshold")
    if submitted or "c13_report" not in st.session_state:
        try:
            with st.spinner(
                "Selecting on validation cases and evaluating the fixed threshold on held-out cases..."
            ):
                st.session_state["c13_report"] = st.cache_data(
                    show_spinner=False, ttl=3600, max_entries=8
                )(evaluate)(audit, missed)
        except (ValueError, RuntimeError) as error:
            st.error(f"Economic evaluation could not finish: {error}. Check costs and retry.")
            return
    report = st.session_state["c13_report"]
    costs = report["cost_matrix_usd"]
    cost_cell = (
        '<div class="vc-matrix-item vc-matrix-{k}"><strong style="font-size:1.5rem">${v:,.2f}</strong>'
        "<span>{label}</span></div>"
    )
    st.markdown(
        '<div class="vc-confusion" role="group" aria-label="Cost matrix in USD per case">'
        '<div class="vc-confusion-heading">Cost matrix <span>USD per case</span></div>'
        '<div class="vc-matrix-axis"><div>Not flagged</div><div>Flagged for audit</div></div>'
        '<div class="vc-matrix-grid" style="margin-top:8px">'
        + cost_cell.format(k="tn", v=costs["tn"], label="TN · actual negative")
        + cost_cell.format(k="fp", v=costs["fp"], label="FP · actual negative")
        + cost_cell.format(k="fn", v=costs["fn"], label="FN · actual positive")
        + cost_cell.format(k="tp", v=costs["tp"], label="TP · actual positive")
        + "</div></div>",
        unsafe_allow_html=True,
    )
    st.caption(report["cost_assumptions"])
    st.markdown(
        '<div class="vc-formula">Total economic loss = (TP + FP) × audit cost + FN × missed-positive loss</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Values and results reflect the last submitted scenario. Change the costs and select Optimize economic threshold to recalculate."
    )

    chosen, result = report["selected_validation"], report["test"]["optimized"]
    savings = report["test_savings_vs_default_usd"]
    cards = [
        stat("Selected threshold", f"{chosen['threshold']:.6f}", "Frozen from validation"),
        stat("Held-out economic loss", f"${result['total_loss_usd']:,.2f}", "Untouched test cases", "gold"),
        stat(
            "Savings vs default",
            f"${savings:,.2f}",
            "Same held-out cases",
            "green" if savings >= 0 else "red",
        ),
    ]
    for col, html in zip(st.columns(3), cards, strict=False):
        with col:
            st.markdown(html, unsafe_allow_html=True)
    if savings < 0:
        st.warning(
            "The validation-selected policy costs more than the default on this held-out split. Validation optimization does not guarantee test savings."
        )
    st.caption(
        "Flag when anomaly score > threshold. Scores are not probabilities. The selected threshold minimizes validation loss, not test loss."
    )

    left, right = st.columns([1.3, 1])
    with left:
        curve = pd.DataFrame(report["validation_curve"]).sort_values("threshold")
        chart = go.Figure(
            go.Scatter(
                x=curve["threshold"],
                y=curve["total_loss_usd"],
                mode="lines",
                name="Validation loss",
                line={"color": "#5ef2b0", "width": 3, "shape": "spline"},
                fill="tozeroy",
                fillcolor="rgba(94,242,176,0.07)",
                hovertemplate="Threshold %{x:.4f}<br>Loss $%{y:,.0f}<extra></extra>",
            )
        )
        chart.add_trace(
            go.Scatter(
                x=[chosen["threshold"]],
                y=[chosen["total_loss_usd"]],
                mode="markers",
                name="Selected validation minimum",
                marker={"size": 14, "color": "#f2c879", "line": {"width": 3, "color": "rgba(242,200,121,.3)"}},
            )
        )
        chart.add_vline(x=chosen["threshold"], line={"color": "rgba(242,200,121,.5)", "width": 1, "dash": "dot"})
        finish(chart, height=340)
        chart.update_layout(
            xaxis_title="Anomaly-score threshold",
            yaxis_title="Total economic loss (USD)",
        )
        st.markdown(
            '<div class="vc-panel-head">Validation loss across thresholds</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})
    with right:
        st.markdown(
            matrix_html(
                result["tp"],
                result["fp"],
                result["fn"],
                result["tn"],
                "Optimized policy",
                "Held-out",
            )
            + f'<div class="vc-panel" style="padding:6px 20px">'
            f'<div class="vc-kv" style="border-top:0"><span>Audit spend</span><b>${result["audit_cost_usd"]:,.2f}</b></div>'
            f'<div class="vc-kv"><span>Missed-positive loss</span><b>${result["missed_loss_usd"]:,.2f}</b></div>'
            f'<div class="vc-kv"><span>Precision · Recall</span><b>{result["precision"]:.1%} · {result["recall"]:.1%}</b></div></div>',
            unsafe_allow_html=True,
        )

    names = {
        "optimized": "Validation-selected threshold",
        "default": "Default threshold (0)",
        "audit_none": "Audit none",
        "audit_all": "Audit all",
    }
    st.write("**Policies compared on the same held-out test cases**")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Policy": names[name],
                    "TP": row["tp"],
                    "FP": row["fp"],
                    "FN": row["fn"],
                    "TN": row["tn"],
                    "Audits": row["flagged"],
                    "Audit spend (USD)": row["audit_cost_usd"],
                    "Missed loss (USD)": row["missed_loss_usd"],
                    "Total loss (USD)": row["total_loss_usd"],
                }
                for name, row in report["test"].items()
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    with st.expander("Economic assumptions, split methodology and complete evidence"):
        st.write(
            f"Training: {report['splits']['train']:,} · Validation: {report['splits']['validation']:,} · Test: {report['splits']['test']:,}. Each split has 1% synthetic positives. Seed {report['seed']}."
        )
        st.write(report["selection"])
        st.write(
            f"Minimum validation loss: ${chosen['total_loss_usd']:,.2f}. The test set is used only to report the frozen policy's results."
        )
        for limitation in report["limitations"]:
            st.write(limitation)
        st.download_button(
            f"Download C13 audit (${costs['fp']:g} audit / ${costs['fn']:g} missed)",
            json.dumps(report, indent=2, allow_nan=False),
            file_name=f"c13_audit_{costs['fp']:g}_{costs['fn']:g}.json",
            mime="application/json",
            key=f"c13_download_{costs['fp']}_{costs['fn']}",
            on_click="ignore",
        )


def render_guard_and_impact() -> None:
    import pandas as pd
    import streamlit as st

    from challenge.c04_guard import evaluate as c04_evaluate
    from challenge.c15_impact import evaluate as c15_evaluate

    st.markdown(
        section(
            "C04 — Out-of-bounds guard",
            "Impossible inputs are rejected or flagged, never scored with false confidence.",
        ),
        unsafe_allow_html=True,
    )
    st.caption("Synthetic edge cases. The unguarded column shows what the bare model would return.")
    with st.spinner("Injecting out-of-bounds edge cases..."):
        report = st.cache_data(show_spinner=False, ttl=3600)(c04_evaluate)()
    wrong = int(report["confident_wrong_predictions"])
    guard_cards = [
        stat("Edge cases injected", f"{int(report['edge_cases_injected'])}", "Impossible or out-of-range inputs"),
        stat(
            "Confident wrong predictions",
            f"{wrong}",
            "Scored with false confidence",
            "green" if wrong == 0 else "red",
        ),
    ]
    for col, html in zip(st.columns(2), guard_cards, strict=False):
        with col:
            st.markdown(html, unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Case": c["case"],
                    "Unguarded score": "n/a"
                    if c["unguarded_score"] is None
                    else round(c["unguarded_score"], 3),
                    "Guard verdict": c["guarded_flag"],
                    "Reason": "; ".join(c["reasons"]),
                }
                for c in report["cases"]
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    st.markdown(
        section(
            "C15 — Net financial impact (PKR)",
            "Loss averted by true detections minus the cost of false alarms.",
        ),
        unsafe_allow_html=True,
    )
    st.caption("Synthetic cases and assumed PKR costs. An estimate, not realized savings.")
    with st.form("c15_inputs"):
        a, b, c = st.columns(3)
        audit = a.number_input("Audit cost per flag (PKR)", 0.0, 1e9, 28000.0, 1000.0)
        loss = b.number_input(
            "Loss averted per true detection (PKR)", 0.0, 1e12, 2800000.0, 100000.0
        )
        cases = c.number_input("Portfolio size (cases)", 1000, 100_000_000, 1_000_000, 100_000)
        st.form_submit_button("Calculate net gain")
    try:
        with st.spinner("Scoring held-out cases and converting to PKR..."):
            impact = st.cache_data(show_spinner=False, ttl=3600, max_entries=8)(c15_evaluate)(
                audit, loss, int(cases)
            )
    except (ValueError, RuntimeError) as error:
        st.error(f"Impact calculation could not finish: {error}")
        return
    held, scaled = impact["held_out"], impact["scaled_to_portfolio"]
    net = float(scaled["net_financial_gain_pkr"])
    impact_cards = [
        stat("Loss averted", f"PKR {scaled['loss_averted_pkr']:,.0f}", "True detections × averted loss", "green"),
        stat("False-alarm cost", f"PKR {scaled['false_alarm_cost_pkr']:,.0f}", "Audits that found nothing", "gold"),
        stat("Net financial gain", f"PKR {net:,.0f}", "Scaled to portfolio size", "green" if net >= 0 else "red"),
    ]
    for col, html in zip(st.columns(3), impact_cards, strict=False):
        with col:
            st.markdown(html, unsafe_allow_html=True)
    st.caption(
        f"Held-out test only: net gain PKR {held['net_financial_gain_pkr']:,.0f}. "
        + impact["limitations"][1]
    )


def render_challenge_sections(data_dir: str = "data_cache") -> None:
    import streamlit as st

    selected = st.radio(
        "Evaluation",
        [
            "Detection & explanations · C02 / C06",
            "Decision economics · C13",
            "Input guard & PKR impact · C04 / C15",
        ],
        horizontal=True,
        label_visibility="collapsed",
        key="risk_lab_view",
    )
    if selected.endswith("C13"):
        render_cost_sensitive()
    elif selected.endswith("C15"):
        render_guard_and_impact()
    else:
        try:
            _render_c02_c06(data_dir)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError):
            st.error(
                "The benchmark report has an invalid structure. Regenerate C02 and C06; C13 remains available independently."
            )
