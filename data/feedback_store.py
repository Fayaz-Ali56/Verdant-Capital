"""Feedback & Memory Layer — the differentiator. Tracks recommendations, scores outcomes,
and re-weights agent influence based on measured accuracy."""
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

def record_outcome(rec_id: int, ticker: str, agent: str, predicted: str, actual_return_30d: float):
    correct = 1 if (predicted == "bullish" and actual_return_30d > 0) or                    (predicted == "bearish" and actual_return_30d < 0) else 0
    c = _conn()
    c.execute("INSERT INTO outcomes VALUES (?,?,?,?,?,?)",
              (rec_id, ticker, agent, predicted, actual_return_30d, correct))
    c.commit()

def agent_weights() -> dict:
    """Accuracy-weighted influence per agent, with smoothing for cold start."""
    c = _conn()
    rows = c.execute("SELECT agent, AVG(was_correct), COUNT(*) FROM outcomes GROUP BY agent").fetchall()
    base = {"esg_verifier": 1.0, "market_analyst": 1.0}
    for agent, acc, n in rows:
        if n >= 3 and acc is not None:
            base[agent] = round(0.5 + float(acc), 3)
    return base

if __name__ == "__main__":
    print("Agent influence weights (cold start = 1.0):", agent_weights())
