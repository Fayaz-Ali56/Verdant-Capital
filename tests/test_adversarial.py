"""Submission regressions: malformed inputs, untrusted outputs and concurrency."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import pytest


@pytest.mark.parametrize("capital", [float("nan"), float("inf"), -1, "not money"])
def test_invalid_capital_is_rejected(capital):
    from orchestrator.graph import _defaults

    with pytest.raises(ValueError):
        _defaults({"capital": capital})


def test_cash_is_reserved_and_unknown_risk_is_rejected():
    from orchestrator.graph import _defaults

    for inputs in ({"candidates": ["CASH"]}, {"risk_profile": "unknown"}):
        with pytest.raises(ValueError):
            _defaults(inputs)


def test_corrupt_price_cache_fails_closed(tmp_path, monkeypatch):
    import config
    from data.fetch_market import load_cached_prices

    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    (tmp_path / "prices.csv").write_text('"broken', encoding="utf-8")
    assert load_cached_prices().empty


def test_nonfinite_prices_cannot_reach_optimizer():
    from data.portfolio import optimize

    prices = pd.DataFrame({"X": [float("inf")] * 60})
    result = optimize(["X"], prices, {})
    assert result["weights"] == {"X": 0.0, "CASH": 1.0}
    json.dumps(result, allow_nan=False)


def test_malformed_llm_narrative_cannot_reach_ui(monkeypatch):
    import orchestrator.graph as graph

    monkeypatch.setattr(
        graph,
        "chat_json",
        lambda *args, **kw: (
            {
                "ticker": "X",
                "verdict": "credible",
                "greenwash_risk": 2,
                "esg_credibility": 90,
                "confidence": 0.8,
                "reasoning": {"bad": "shape"},
                "red_flags": "not a list",
            },
            "test",
        ),
    )
    result, _ = graph._validated_llm_esg("X", [{"citation": "[report p.1]"}])
    assert result is None


def test_empty_outcome_source_filter_does_not_use_synthetic_history(tmp_path):
    from data.feedback_store import agent_weights, record_outcome, save_recommendation

    db = tmp_path / "feedback.db"
    rid = save_recommendation("test", {}, db_path=db)
    for i in range(4):
        record_outcome(
            rid,
            "X",
            "market_analyst",
            "bullish",
            0.1,
            db_path=db,
            label_source="synthetic_demo",
            case_key=str(i),
        )
    assert agent_weights(db, allowed_sources=set())["market_analyst"] == 1


def test_parallel_migrations_and_idempotent_legacy_outcomes(tmp_path):
    from data.feedback_store import record_outcome, save_recommendation

    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE recommendations(id INTEGER PRIMARY KEY, ts TEXT, query TEXT, memo TEXT)"
        )
        conn.execute(
            "CREATE TABLE outcomes(rec_id INTEGER, ticker TEXT, agent TEXT, predicted TEXT, actual_return_30d REAL, was_correct INTEGER)"
        )
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(lambda n: save_recommendation(str(n), {}, db_path=db), range(16)))
    assert len(set(ids)) == 16
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda _: record_outcome(ids[0], "X", "market_analyst", "bullish", 0.1, db_path=db),
                range(16),
            )
        )
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0] == 1


def test_empty_demo_universe_stays_empty():
    from data.demo import price_frame

    assert price_frame([]).empty


def test_market_change_uses_exactly_thirty_return_intervals():
    from data.fetch_market import price_stats

    frame = pd.DataFrame(
        {"X": np.arange(1.0, 32.0)}, index=pd.bdate_range("2025-01-01", periods=31)
    )
    assert price_stats(frame)["X"]["return_30d_pct"] == 3000.0


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_influence_is_rejected(value):
    from data.portfolio import optimize

    with pytest.raises(ValueError):
        optimize([], pd.DataFrame(), {}, influence={"market_analyst": value})


def test_parallel_report_writes_never_publish_partial_json(tmp_path):
    from data.files import write_json

    output = tmp_path / "report.json"
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda n: write_json(output, {"run": n, "values": list(range(100))}), range(24)
            )
        )
    assert json.loads(output.read_text())["values"] == list(range(100))
    assert list(tmp_path.iterdir()) == [output]


def test_release_excludes_secrets_databases_and_untracked_files(tmp_path, monkeypatch):
    from zipfile import ZipFile

    import tools.package_release as release

    for name in ("app.py", ".env.example", ".env.production", "private.sqlite3", "untracked.key"):
        (tmp_path / name).write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(release, "SOURCE", tmp_path)
    monkeypatch.setattr(release, "OUTPUT", tmp_path / "dist" / "release.zip")
    monkeypatch.setattr(
        release.subprocess,
        "check_output",
        lambda *a, **k: b"app.py\0.env.example\0.env.production\0private.sqlite3\0",
    )
    with ZipFile(release.package()) as archive:
        assert set(archive.namelist()) == {"Verdant-Capital/app.py", "Verdant-Capital/.env.example"}
