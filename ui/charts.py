"""Consistent Plotly chart grammar for the Verdant dark workspace."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

TEXT = "#EAF3F0"
MUTED = "#AABCB5"
GRID = "rgba(196,218,210,0.09)"


def finish(fig: go.Figure, height: int = 300, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=14, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=MUTED, size=12),
        hoverlabel=dict(
            bgcolor="#0b1c19",
            bordercolor="rgba(94,242,176,.45)",
            font=dict(color=TEXT, size=12, family="JetBrains Mono, monospace"),
        ),
        showlegend=legend,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            x=0.0,
            xanchor="left",
            font=dict(size=11, color=MUTED),
        ),
        xaxis=dict(showgrid=False, zeroline=False, linecolor=GRID, tickfont=dict(color=MUTED)),
        yaxis=dict(showgrid=True, gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED)),
    )
    return fig


def scenario_comparison(rows: list[dict], baseline: dict[str, float]) -> go.Figure:
    labels = [str(row["ticker"]) for row in rows]
    baseline_weights = [round(100 * baseline.get(t, 0), 1) for t in labels]
    current_weights = [round(100 * float(r["weight"]), 1) for r in rows]
    fig = go.Figure()
    fig.add_bar(
        name="Base mandate",
        x=labels,
        y=baseline_weights,
        marker_color="#59778A",
        marker_line_width=0,
        hovertemplate="%{x}: %{y:.1f}%<extra>Base</extra>",
    )
    fig.add_bar(
        name="Stress event",
        x=labels,
        y=current_weights,
        marker_color="#7CE0B2",
        marker_line_width=0,
        hovertemplate="%{x}: %{y:.1f}%<extra>Event</extra>",
    )
    finish(fig, height=290)
    fig.update_layout(barmode="group", bargap=0.28, yaxis_title="Portfolio weight (%)")
    return fig


def precision_recall_curve(curve: dict, base_rate: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=curve["recall"],
            y=curve["precision"],
            mode="lines",
            name="Rare-event detector",
            line=dict(color="#7CE0B2", width=3),
            fill="tozeroy",
            fillcolor="rgba(124,224,178,0.08)",
            hovertemplate="Recall: %{x:.1%}<br>Precision: %{y:.1%}<extra></extra>",
        )
    )
    fig.add_hline(
        y=float(base_rate),
        line=dict(color="#E9C38D", width=1.5, dash="dot"),
        annotation_text="1% random ranking",
        annotation_position="top right",
        annotation_font_color="#E9C38D",
    )
    finish(fig, height=335)
    fig.update_layout(
        xaxis_title="Recall", yaxis_title="Precision", xaxis_range=[0, 1], yaxis_range=[0, 1.03]
    )
    return fig


def carbon_forecast_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["ds"],
            y=df["yhat_upper"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["ds"],
            y=df["yhat_lower"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(124,224,178,.11)",
            name="Indicative band",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["ds"],
            y=df["yhat"],
            mode="lines",
            name="Model projection",
            line=dict(width=3, color="#7CE0B2"),
        )
    )
    finish(fig, height=315)
    fig.update_layout(xaxis_title="Date", yaxis_title="Carbon ETF proxy (USD)")
    return fig


def feedback_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for column, name, color in [
        ("esg_weight", "ESG influence", "#7CE0B2"),
        ("mkt_weight", "Market influence", "#E9C38D"),
    ]:
        if column in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["day"],
                    y=df[column],
                    mode="lines",
                    name=name,
                    line=dict(width=3, color=color),
                    hovertemplate="Day %{x}<br>Weight %{y:.2f}<extra></extra>",
                )
            )
    finish(fig, height=300)
    fig.update_layout(xaxis_title="Simulation day", yaxis_title="Agent influence")
    return fig


def feature_attribution(record: dict) -> go.Figure:
    """Interactive diverging attribution view of the actual C06 recorded model output."""
    attrs = list(record.get("attributions", []))[:6]
    # Plotly displays the last category at the top; reverse pre-sorted importance.
    attrs = list(reversed(attrs))
    labels = [str(a.get("feature", "")).replace("_", " ").capitalize() for a in attrs]
    values = [float(a.get("shap_value", 0)) for a in attrs]
    colors = ["#F0A8A8" if v > 0 else "#8CE1B6" for v in values]
    fig = go.Figure()
    fig.add_bar(
        y=labels,
        x=values,
        orientation="h",
        marker=dict(color=colors),
        customdata=[["Raises suspicion" if v > 0 else "Lowers suspicion"] for v in values],
        hovertemplate="%{y}<br>%{x:+.4f} · %{customdata[0]}<extra></extra>",
    )
    fig.add_vline(x=0, line=dict(color="rgba(232,245,238,.45)", width=1))
    finish(fig, height=315, legend=False)
    fig.update_layout(
        xaxis_title="SHAP impact on anomaly score",
        margin=dict(l=12, r=22, t=12, b=30),
        xaxis=dict(gridcolor=GRID, showgrid=True, zeroline=False),
        yaxis=dict(showgrid=False, automargin=True, tickfont=dict(size=11, color=TEXT)),
    )
    return fig
