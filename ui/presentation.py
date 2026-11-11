"""View-model and safe presentation helpers; never change investment decisions."""

from __future__ import annotations

from html import escape
from typing import Any

PALETTE = ["#5ef2b0", "#f2c879", "#8fd3ff", "#c9a8ff", "#ff9a8f", "#b9ffe0", "#90aaa4"]
CASH_COLOR = "#f2c879"


def money(amount: float | int | None, compact: bool = False) -> str:
    """Format USD without obscuring small values or inventing market data."""
    value = float(amount or 0.0)
    if compact and abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}m"
    if compact and abs(value) >= 1000:
        return f"${value / 1000:,.1f}k"
    return f"${value:,.0f}"


def percent(value: float | int | None, digits: int = 1) -> str:
    return f"{float(value or 0) * 100:.{digits}f}%"


def clean_portfolio(rows: list[dict]) -> list[dict]:
    """Suppress solver-level numerical noise in the visual table only."""
    result = []
    for item in rows:
        if not isinstance(item, dict) or not item.get("ticker"):
            continue
        entry = dict(item)
        weight = float(item.get("weight") or 0)
        entry["weight"] = 0.0 if abs(weight) < 1e-8 else weight
        result.append(entry)
    return result


def _color_map(rows: list[dict]) -> dict[str, str]:
    """Stable color per ticker; cash always uses the reserve color."""
    colors: dict[str, str] = {}
    index = 0
    for row in rows:
        ticker = str(row["ticker"])
        if ticker == "CASH":
            colors[ticker] = CASH_COLOR
            continue
        palette = [c for c in PALETTE if c != CASH_COLOR]
        colors[ticker] = palette[index % len(palette)]
        index += 1
    return colors


def allocation_strip(rows: list[dict]) -> str:
    """Lightweight allocation graphic; the accompanying ledger supplies exact values."""
    rows = [row for row in clean_portfolio(rows) if row["weight"] > 0]
    if not rows:
        return '<p class="vc-note">No allocation is available.</p>'
    colors = _color_map(rows)
    description = ", ".join(f"{row['ticker']} {percent(row['weight'])}" for row in rows)
    segments = "".join(
        f'<span style="flex-grow:{row["weight"]:.12f};background:{colors[str(row["ticker"])]};'
        f'animation-delay:{i * 90}ms"></span>'
        for i, row in enumerate(rows)
    )
    return (
        f'<div class="vc-allocation" role="img" aria-label="{safe(description)}">{segments}</div>'
    )


def allocation_donut(rows: list[dict], capital: float) -> str:
    """Conic-gradient donut and exact ledger built only from validated optimizer weights."""
    visible = sorted(
        (row for row in clean_portfolio(rows) if row["weight"] > 0),
        key=lambda r: r["weight"],
        reverse=True,
    )
    if not visible:
        return '<p class="vc-note">No allocation is available.</p>'
    colors = _color_map(visible)
    stops, cursor = [], 0.0
    for row in visible:
        share = max(0.0, min(1.0, float(row["weight"]))) * 100
        color = colors[str(row["ticker"])]
        stops.append(f"{color} {cursor:.3f}% {cursor + share - 0.4:.3f}%")
        stops.append(f"transparent {cursor + share - 0.4:.3f}% {cursor + share:.3f}%")
        cursor += share
    if cursor < 100:
        stops.append(f"rgba(255,255,255,.05) {cursor:.3f}% 100%")
    invested = sum(float(r["weight"]) for r in visible if r["ticker"] != "CASH")
    description = ", ".join(f"{row['ticker']} {percent(row['weight'])}" for row in visible)
    legend = "".join(
        f'<div class="vc-ledger"><span class="vc-ledger-dot" style="background:{colors[str(r["ticker"])]};color:{colors[str(r["ticker"])]}"></span>'
        f'<div class="vc-ledger-symbol">{safe(r["ticker"])}</div>'
        f'<div class="vc-ledger-track"><div class="vc-ledger-fill" style="width:{max(0, min(100, float(r["weight"]) * 100)):.2f}%;'
        f'background:linear-gradient(90deg,{colors[str(r["ticker"])]},rgba(255,255,255,.55));animation-delay:{i * 110}ms"></div></div>'
        f'<div class="vc-ledger-pct">{percent(r["weight"])}</div>'
        f'<div class="vc-ledger-amt">{money(capital * float(r["weight"]), compact=True)}</div></div>'
        for i, r in enumerate(visible)
    )
    return (
        f'<div class="vc-panel"><div class="vc-alloc">'
        f'<div class="vc-donut" role="img" aria-label="{safe(description)}" style="background:conic-gradient({", ".join(stops)})">'
        f'<div class="vc-donut-center"><strong>{percent(invested, 0)}</strong><span>Deployed</span></div></div>'
        f'<div class="vc-legend">{legend}</div></div></div>'
    )


def get_dashboard_metrics(result: dict) -> dict[str, Any]:
    """Produce labels from an actual result; no fabricated totals."""
    memo = result.get("final_memo") or {}
    allocation = clean_portfolio(memo.get("portfolio") or [])
    weights = {p["ticker"]: p["weight"] for p in allocation}
    capital = float(memo.get("capital") or 0)
    conflicts = memo.get("conflicts") or []
    cash = float(weights.get("CASH", 0))
    metrics = memo.get("optimizer_metrics") or {}
    return {
        "capital": capital,
        "allocated": capital * max(0.0, min(1.0, 1.0 - cash)),
        "cash_ratio": cash,
        "cash_amount": capital * cash,
        "conflicts": len(conflicts),
        "return_estimate": metrics.get("expected_return_pct"),
        "volatility": metrics.get("volatility_pct"),
        "portfolio": allocation,
        "status": metrics.get("status", "unavailable"),
    }


def safe(text: Any) -> str:
    return escape(str(text), quote=True)


def chip(text: str, kind: str = "neutral") -> str:
    if kind not in {"neutral", "positive", "warning", "negative", "info"}:
        kind = "neutral"
    return f'<span class="vc-chip vc-chip--{kind}">{safe(text)}</span>'


def section(title: str, detail: str = "", aside: str = "") -> str:
    subtitle = f'<p class="vc-section-desc">{safe(detail)}</p>' if detail else ""
    aside_html = f'<span class="vc-section-aside">{safe(aside)}</span>' if aside else ""
    return (
        f'<div class="vc-section-top"><div><h2>{safe(title)}</h2>{subtitle}</div>{aside_html}</div>'
    )


def stat(label: str, value: str, note: str = "", tone: str = "") -> str:
    note_html = f'<div class="vc-stat-note">{safe(note)}</div>' if note else ""
    tone_name = tone if tone in {"green", "gold", "red"} else ""
    return (
        f'<div class="vc-stat"><div class="vc-stat-label">{safe(label)}</div>'
        f'<div class="vc-stat-value {"vc-" + tone_name if tone_name else ""}">{safe(value)}</div>'
        f"{note_html}</div>"
    )


def _orbit(center_value: str, center_label: str) -> str:
    """Decorative diagram of the three specialist roles feeding one memo."""
    return f"""<div class="vc-orbit" aria-hidden="true">
      <svg viewBox="0 0 400 400">
        <defs>
          <linearGradient id="vcBeam" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#5ef2b0" stop-opacity=".9"/>
            <stop offset="1" stop-color="#f2c879" stop-opacity=".5"/>
          </linearGradient>
        </defs>
        <circle class="ring" cx="200" cy="200" r="190"/>
        <circle class="ring-dash" cx="200" cy="200" r="160"/>
        <circle class="ring" cx="200" cy="200" r="122"/>
        <circle class="ring-dash rev" cx="200" cy="200" r="96"/>
        <path class="beam" d="M200 24 Q200 120 200 200"/>
        <path class="beam" d="M36 304 Q120 260 200 200"/>
        <path class="beam" d="M364 304 Q280 260 200 200"/>
        <circle class="packet" r="3.5"><animateMotion dur="2.6s" repeatCount="indefinite" path="M200 24 Q200 120 200 200"/></circle>
        <circle class="packet" r="3.5" style="fill:#f2c879"><animateMotion dur="3.1s" begin=".6s" repeatCount="indefinite" path="M36 304 Q120 260 200 200"/></circle>
        <circle class="packet" r="3.5" style="fill:#8fd3ff"><animateMotion dur="2.8s" begin="1.1s" repeatCount="indefinite" path="M364 304 Q280 260 200 200"/></circle>
      </svg>
      <div class="vc-core"><div><strong>{safe(center_value)}</strong><span>{safe(center_label)}</span></div></div>
      <div class="vc-node n1"><i>E</i><div><b>ESG Verifier</b><small>Evidence</small></div></div>
      <div class="vc-node n2"><i>M</i><div><b>Market Analyst</b><small>Signals</small></div></div>
      <div class="vc-node n3"><i>P</i><div><b>Optimizer</b><small>Constraints</small></div></div>
    </div>"""


def hero(
    *,
    mode: str,
    preview: bool,
    last_run: str = "",
    summary: dict[str, Any] | None = None,
) -> str:
    demonstration = mode == "demo"
    provenance = "Fictional simulation" if demonstration else "Historical market cache"
    status = (
        "Preview · not saved"
        if preview
        else ("Analysis complete" if last_run else "Ready for analysis")
    )
    kpis = ""
    center_value, center_label = "Memo", "Single decision"
    if summary:
        deployed = 1.0 - float(summary.get("cash_ratio") or 0)
        holdings = sum(
            1 for r in summary.get("portfolio", []) if r["weight"] > 0 and r["ticker"] != "CASH"
        )
        center_value, center_label = percent(deployed, 0), "Capital deployed"
        kpis = (
            '<div class="vc-hero-kpis">'
            f'<div class="vc-hero-kpi"><strong>{money(summary.get("capital"), compact=True)}</strong><span>Mandate</span></div>'
            f'<div class="vc-hero-kpi"><strong>{holdings}</strong><span>Holdings funded</span></div>'
            f'<div class="vc-hero-kpi"><strong>{int(summary.get("conflicts") or 0)}</strong><span>Conflicts resolved</span></div>'
            "</div>"
        )
    run_tag = chip(f"Decision #{last_run}", "positive") if last_run and not preview else ""
    return f"""<section class="vc-hero" aria-label="Decision intelligence workspace">
      <div class="vc-hero-main">
        <div class="vc-eyebrow"><b>Live</b> Multi-agent investment studio</div>
        <h1>Conviction,<br><em>with a paper trail.</em></h1>
        <p>Bring evidence to the table. Put your mandate through three specialist
        perspectives, explicit constraints, and a decision you can inspect.</p>
        <div class="vc-hero-tags">{chip(provenance, "info")}{chip(status, "positive" if not preview and last_run else "warning" if preview else "neutral")}{run_tag}</div>
        {kpis}
      </div>
      {_orbit(center_value, center_label)}
    </section>"""


def agent_header(title: str, subtitle: str, letter: str, status: str = "Operational") -> str:
    return (
        f'<div class="vc-agent-head"><div class="vc-agent-identity"><span class="vc-agent-symbol">{safe(letter)}</span>'
        f'<div><div class="vc-agent-name">{safe(title)}</div><div class="vc-agent-sub">{safe(subtitle)}</div></div></div>'
        f'<span class="vc-mini-status">{safe(status)}</span></div>'
    )


def agent_card(
    title: str,
    subtitle: str,
    letter: str,
    status: str,
    value: str,
    label: str,
    note: str,
    ratio: float,
    color: str,
) -> str:
    width = max(0.0, min(1.0, float(ratio))) * 100
    return (
        f'<div class="vc-panel vc-agent" style="--vc-agent:{safe(color)}">{agent_header(title, subtitle, letter, status)}'
        f'<div class="vc-agent-metric">{safe(value)}<span>{safe(label)}</span></div>'
        f'<div class="vc-agent-bar"><i style="width:{width:.1f}%"></i></div>'
        f'<div class="vc-agent-note">{safe(note)}</div></div>'
    )


def matrix_html(
    tp: int, fp: int, fn: int, tn: int, heading: str, aside: str = "", notes: dict | None = None
) -> str:
    """Accessible confusion matrix: each cell has a text label as well as color."""
    notes = notes or {}

    def cell(kind: str, value: int, label: str) -> str:
        extra = f"<em>{safe(notes[kind])}</em>" if kind in notes else ""
        return f'<div class="vc-matrix-item vc-matrix-{kind}"><strong>{int(value):,}</strong><span>{safe(label)}</span>{extra}</div>'

    return (
        f'<div class="vc-confusion" role="group" aria-label="{safe(heading)}">'
        f'<div class="vc-confusion-heading">{safe(heading)} <span>{safe(aside)}</span></div>'
        '<div class="vc-matrix-axis"><div>Not flagged</div><div>Flagged</div></div>'
        '<div class="vc-matrix-grid" style="margin-top:8px">'
        f"{cell('tn', tn, 'True negatives')}{cell('fp', fp, 'False positives')}"
        f"{cell('fn', fn, 'Missed positives')}{cell('tp', tp, 'True positives')}"
        "</div></div>"
    )


def decision_reason(reason: str) -> tuple[str, str]:
    """Map documented policy codes to restrained UI labels."""
    mapping = {
        "ALLOCATED_CONSTRAINT_VALIDATED": ("Allocated", "positive"),
        "EXCLUDED_HIGH_ESG_RISK": ("Excluded", "negative"),
        "LIMITED_UNVERIFIED_ESG": ("Restricted", "warning"),
        "CASH_SAFETY_RESERVE": ("Cash reserve", "info"),
        "EXCLUDED_MISSING_PRICE_HISTORY": ("Missing prices", "warning"),
        "ZERO_OPTIMAL_WEIGHT": ("Not selected", "neutral"),
    }
    return mapping.get(str(reason), ("Review required", "neutral"))
