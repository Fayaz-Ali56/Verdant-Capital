"""Actual Streamlit flows with injected cache, storage and provider failures."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def app_with_storage(tmp_path, monkeypatch):
    import config

    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(config, "FEEDBACK_DB", str(tmp_path / "feedback.db"))
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=120).run()


def review(app):
    next(button for button in app.button if button.label == "Review this mandate").click().run()


def test_hidden_risk_lab_does_not_train_and_error_retains_previous_decision(tmp_path, monkeypatch):
    import orchestrator.graph as graph

    app = app_with_storage(tmp_path, monkeypatch)
    assert not app.exception
    assert "c13_report" not in app.session_state
    review(app)
    old_id = app.session_state["boardroom_result"]["run_id"]

    def unavailable():
        raise RuntimeError("sensitive-provider-detail")

    monkeypatch.setattr(graph, "build_graph", unavailable)
    review(app)
    assert not app.exception
    assert app.session_state["boardroom_result"]["run_id"] == old_id
    assert app.error and "sensitive-provider-detail" not in app.error[0].value


def test_corrupt_feedback_and_database_offer_recovery_without_tracebacks(tmp_path, monkeypatch):
    app = app_with_storage(tmp_path, monkeypatch)
    (tmp_path / "feedback_timeline.json").write_text("[not json", encoding="utf-8")
    app.radio(key="workspace").set_value("Market intelligence").run()
    assert not app.exception
    assert app.error and "Regenerate" in app.error[0].value
    (tmp_path / "feedback.db").write_text("not sqlite", encoding="utf-8")
    app.radio(key="workspace").set_value("Audit trail").run()
    assert not app.exception
    assert app.error and "permissions" in app.error[0].value


def test_invalid_benchmark_shape_does_not_block_independent_economics(tmp_path, monkeypatch):
    for name in ("c02_report.json", "c02_pr_curve.json", "c06_report.json"):
        (tmp_path / name).write_text("[]", encoding="utf-8")
    app = app_with_storage(tmp_path, monkeypatch)
    app.radio(key="workspace").set_value("Risk Lab").run()
    assert not app.exception and app.error
    next(r for r in app.radio if r.label == "Evaluation").set_value(
        "Decision economics · C13"
    ).run()
    assert not app.exception and not app.error
    assert app.session_state["c13_report"]["test"]["optimized"]["tp"] > 0
