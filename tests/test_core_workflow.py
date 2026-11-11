"""Behavioral acceptance tests for the three-agent sustainable finance workflow."""

import numpy as np
import pandas as pd


def _prices(n=170):
    rng = np.random.default_rng(12)
    return pd.DataFrame(
        {
            "SOLR": 80 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, n))),
            "WIND": 65 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))),
            "FOSS": 42 * np.exp(np.cumsum(rng.normal(0.0005, 0.020, n))),
        },
        index=pd.bdate_range("2025-01-01", periods=n),
    )


def test_optimizer_long_only_normalized_and_respects_exclusions():
    from data.portfolio import optimize

    votes = {
        "SOLR": {"verdict": "credible", "esg_credibility": 82, "greenwash_risk": 18},
        "WIND": {"verdict": "unverified", "esg_credibility": None, "greenwash_risk": None},
        "FOSS": {"verdict": "likely_greenwashing", "esg_credibility": 27, "greenwash_risk": 87},
    }
    result = optimize(
        ["SOLR", "WIND", "FOSS"], _prices(), votes, risk_profile="moderate", strict_esg=True
    )
    weights = result["weights"]
    assert abs(sum(weights.values()) - 1.0) < 1e-6
    assert all(v >= -1e-9 for v in weights.values())
    assert weights["FOSS"] == 0.0
    assert weights["WIND"] <= 0.1000001
    assert set(weights) == {"SOLR", "WIND", "FOSS", "CASH"}


def test_optimizer_all_excluded_allocates_cash():
    from data.portfolio import optimize

    res = optimize(
        ["FOSS"],
        _prices(),
        {"FOSS": {"verdict": "likely_greenwashing", "greenwash_risk": 90}},
        strict_esg=True,
    )
    assert res["weights"]["CASH"] == 1.0
    assert res["weights"]["FOSS"] == 0.0


def test_no_esg_evidence_must_be_unverified():
    from orchestrator.graph import run_esg_verifier

    out = run_esg_verifier({"candidates": ["NO_DATA"], "mode": "market", "votes": []})
    payload = out["votes"][0]["payload"]
    assert payload["verdict"] == "unverified"
    assert payload["greenwash_risk"] is None
    assert payload["evidence"] == []


def test_full_demo_pipeline_is_bounded_auditable_and_uses_three_agents(tmp_path, monkeypatch):
    import config
    from orchestrator.graph import run_pipeline

    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "FEEDBACK_DB", str(tmp_path / "feedback.db"))
    result = run_pipeline(
        {
            "candidates": ["SOLR", "WIND", "FOSS"],
            "risk_profile": "moderate",
            "capital": 100000,
            "query": "No greenwashing",
            "mode": "demo",
        },
        persist=True,
    )
    assert len([v for v in result["votes"] if v["agent"] == "esg_verifier"]) == 3
    assert len([v for v in result["votes"] if v["agent"] == "market_analyst"]) == 3
    assert result["debate_rounds"] <= 1
    memo = result["final_memo"]
    assert set(memo["agents"]) == {"esg_verifier", "market_analyst", "portfolio_optimizer"}
    assert abs(sum(p["weight"] for p in memo["portfolio"]) - 1.0) < 1e-6
    assert memo["mode"] == "demo"
    assert result["run_id"] > 0
    assert any(e["source"].startswith("SYNTHETIC") for e in result["esg_evidence"].get("SOLR", []))


def test_market_stats_short_history_and_no_lookahead():
    from data.fetch_market import price_stats

    dates = pd.bdate_range("2025-05-01", periods=35)
    data = pd.DataFrame({"SOLR": np.linspace(10, 20, 35)}, index=dates)
    stats = price_stats(data)
    assert stats["SOLR"]["trend_90d"] == "insufficient_history"
    assert stats["SOLR"]["last"] == 20


def test_feedback_isolated_by_database_and_not_conflated_with_mock_results(tmp_path):
    from data.feedback_store import agent_weights, record_outcome, save_recommendation

    db = tmp_path / "testfeedback.db"
    rid = save_recommendation("demo", {"portfolio": []}, db_path=db, mode="demo")
    assert rid == 1
    assert agent_weights(db_path=db)["market_analyst"] == 1.0
    for n in range(4):
        record_outcome(
            rid,
            "SOLR",
            "market_analyst",
            "bullish",
            0.05,
            correct=1,
            db_path=db,
            label_source="synthetic_demo",
            case_key=f"{n}",
        )
    assert agent_weights(db_path=db)["market_analyst"] > 1.0


def test_cache_loader_preserves_ticker_column_prices_csv(tmp_path, monkeypatch):
    import config
    from data.fetch_market import load_cached_prices

    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    _prices().to_csv(tmp_path / "prices.csv")
    got = load_cached_prices()
    assert "SOLR" in got.columns
    assert "MISSING" not in got.columns
    assert len(got) == 170


def test_legacy_feedback_database_can_upgrade_safely(tmp_path):
    import sqlite3

    from data.feedback_store import agent_weights, record_outcome, save_recommendation

    db = tmp_path / "old_feedback.db"
    conn = sqlite3.connect(db)
    conn.execute(
        "CREATE TABLE recommendations(id INTEGER PRIMARY KEY, ts TEXT, query TEXT, memo TEXT)"
    )
    conn.execute(
        "CREATE TABLE outcomes(rec_id INTEGER, ticker TEXT, agent TEXT, predicted TEXT, actual_return_30d REAL, was_correct INTEGER)"
    )
    conn.execute("INSERT INTO outcomes VALUES (1, 'X', 'market_analyst', 'bullish', 0.1, 1)")
    conn.commit()
    conn.close()
    rid = save_recommendation("new mandate", {"portfolio": []}, db_path=db, mode="demo")
    record_outcome(
        rid, "SOLR", "market_analyst", "bullish", 0.03, db_path=db, label_source="synthetic_demo"
    )
    assert rid == 1
    assert agent_weights(db_path=db, allowed_sources={"verified"})["market_analyst"] == 1.0


def test_event_shock_is_explicitly_synthetic_and_changes_only_scenario_prices():
    from data.demo import price_frame

    normal = price_frame(["SOLR", "FOSS"], periods=180)
    shocked = price_frame(["SOLR", "FOSS"], periods=180, event="carbon_price_spike")
    pd.testing.assert_frame_equal(normal.iloc[:-30], shocked.iloc[:-30])
    assert not np.allclose(normal.iloc[-1].values, shocked.iloc[-1].values)


def test_adaptive_weights_influence_portfolio_scenario_without_overriding_esg_caps():
    from data.portfolio import optimize

    esg = {
        "SOLR": {"verdict": "credible", "greenwash_risk": 15, "esg_credibility": 85},
        "WIND": {"verdict": "credible", "greenwash_risk": 20, "esg_credibility": 80},
    }
    base = optimize(
        ["SOLR", "WIND"], _prices(), esg, influence={"esg_verifier": 1.0, "market_analyst": 1.0}
    )
    adaptive = optimize(
        ["SOLR", "WIND"], _prices(), esg, influence={"esg_verifier": 1.3, "market_analyst": 0.7}
    )
    assert base["influence_used"]["market_analyst"] == 1.0
    assert adaptive["influence_used"]["market_analyst"] == 0.7
    assert abs(sum(adaptive["weights"].values()) - 1) < 1e-6
    assert all(adaptive["weights"][t] <= adaptive["esg_caps"][t] + 1e-6 for t in ["SOLR", "WIND"])


def test_screening_rejection_has_policy_reason_codes_and_citations(tmp_path, monkeypatch):
    import config
    from orchestrator.graph import run_pipeline

    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    result = run_pipeline(
        {
            "mode": "demo",
            "candidates": ["SOLR", "FOSS"],
            "query": "Sustainability-first",
            "strict_esg": True,
        },
        persist=False,
    )
    rows = {x["ticker"]: x for x in result["final_memo"]["decision_audit"]}
    assert rows["FOSS"]["policy_reason"] == "EXCLUDED_HIGH_ESG_RISK"
    assert rows["FOSS"]["weight"] == 0
    assert rows["FOSS"]["citations"]
    assert rows["SOLR"]["weight"] >= 0


def test_material_hypothetical_market_event_rebalances_a_moderate_portfolio(tmp_path, monkeypatch):
    import config
    from orchestrator.graph import run_pipeline

    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    universe = {"mode": "demo", "candidates": ["SOLR", "WIND", "FOSS"], "risk_profile": "moderate"}
    normal = run_pipeline(dict(universe, event="baseline"), persist=False)
    shock = run_pipeline(dict(universe, event="market_selloff"), persist=False)
    assert normal["optimizer_weights"]["SOLR"] > shock["optimizer_weights"]["SOLR"] + 0.05
