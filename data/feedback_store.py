"""Feedback & Memory Layer — tracks recommendations, scores outcomes,
re-weights agent influence based on measured accuracy."""
import os, json, sqlite3, datetime
import config

def _conn():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    c = sqlite3.connect(config.FEEDBACK_DB)
    c.execute("""CREATE TABLE IF NOT EXISTS recommendations(
        id INTEGER PRIMARY KEY, ts TEXT, query TEXT, memo TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS outcomes(
        rec_id INTEGER, ticker TEXT, agent TEXT,
        predicted TEXT, actual_return_30d REAL, was_correct INTEGER)""")
    return c

def save_recommendation(query: str, memo: dict) -> int:
    c = _conn()
    cur = c.execute("INSERT INTO recommendations(ts, query, memo) VALUES (?,?,?)",
                    (datetime.datetime.now().isoformat(), query, json.dumps(memo)))
    c.commit()
    return cur.lastrowid

def record_outcome(rec_id: int, ticker: str, agent: str, predicted: str,
                   actual_return_30d: float, correct: int | None = None):
    """correct: pass explicitly for non-directional agents (e.g. ESG verdicts).
    None -> infer from direction: bullish needs positive return, bearish negative."""
    if correct is None:
        correct = 1 if ((predicted == "bullish" and actual_return_30d > 0) or
                        (predicted == "bearish" and actual_return_30d < 0)) else 0
    c = _conn()
    c.execute("INSERT INTO outcomes VALUES (?,?,?,?,?,?)",
              (rec_id, ticker, agent, predicted, actual_return_30d, int(correct)))
    c.commit()

def agent_weights() -> dict:
    """Accuracy-weighted influence per agent (0.5 + accuracy), smoothed for cold start."""
    c = _conn()
    rows = c.execute("SELECT agent, AVG(was_correct), COUNT(*) FROM outcomes GROUP BY agent").fetchall()
    base = {"esg_verifier": 1.0, "market_analyst": 1.0}
    for agent, acc, n in rows:
        if n >= 3 and acc is not None:
            base[agent] = round(0.5 + float(acc), 3)
    return base


def reset_outcomes():
    """Clear scored outcomes (used so the simulated backtest is reproducible, not cumulative)."""
    c = _conn()
    c.execute("DELETE FROM outcomes")
    c.commit()
