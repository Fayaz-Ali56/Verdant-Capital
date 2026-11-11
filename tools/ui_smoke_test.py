"""Real Streamlit smoke flows in a disposable data directory; no fake UI framework."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory


def main():
    with TemporaryDirectory(prefix="verdant-smoke-") as folder:
        os.environ["VERDANT_DATA_DIR"] = folder
        os.environ["VERDANT_FEEDBACK_DB"] = str(Path(folder) / "feedback.db")
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_file(
            str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=120
        ).run()
        assert not app.exception, app.exception
        assert "c13_report" not in app.session_state
        next(b for b in app.button if b.label == "Review this mandate").click().run()
        assert not app.exception and not app.error
        assert app.session_state["boardroom_result"]["engine"] == "LangGraph"
        for view in ("Risk Lab", "Market intelligence", "Audit trail", "Investment boardroom"):
            app.radio(key="workspace").set_value(view).run()
            assert not app.exception, app.exception
        app.multiselect[0].set_value([]).run()
        next(b for b in app.button if b.label == "Review this mandate").click().run()
        assert app.session_state["boardroom_result"]["optimizer_weights"] == {"CASH": 1.0}
        next(r for r in app.radio if r.label == "Data environment").set_value(
            "Historical market cache"
        ).run()
        next(b for b in app.button if b.label == "Review this mandate").click().run()
        assert not app.exception
        assert app.session_state["boardroom_result"]["optimizer_weights"]["CASH"] == 1.0
        print(
            "PASS: real Streamlit preview, persisted LangGraph review, lazy navigation, empty universe, missing historical cache"
        )


if __name__ == "__main__":
    main()
