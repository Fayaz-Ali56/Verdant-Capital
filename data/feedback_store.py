"""SQLite audit trail with explicit outcome sources and isolated demo scoring."""

import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import config


@contextmanager
def _conn(db_path=None):
    path = Path(db_path or config.FEEDBACK_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    try:
        # Serialize migration + write boundaries, including first concurrent use.
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS recommendations(
            id INTEGER PRIMARY KEY, ts TEXT NOT NULL, query TEXT,
            memo TEXT NOT NULL, mode TEXT NOT NULL DEFAULT 'market')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS outcomes(
            rec_id INTEGER NOT NULL, ticker TEXT NOT NULL, agent TEXT NOT NULL,
            predicted TEXT NOT NULL, actual_return_30d REAL,
            was_correct INTEGER NOT NULL, label_source TEXT NOT NULL,
            case_key TEXT NOT NULL,
            UNIQUE(rec_id, ticker, agent, case_key))""")
        # Compatibility with feedback.db created by the original zohtest branch.
        # Legacy outcomes lack provenance and must NEVER count as verified truth.
        migrations = {
            "recommendations": [("mode", "TEXT NOT NULL DEFAULT 'legacy'")],
            "outcomes": [
                ("label_source", "TEXT NOT NULL DEFAULT 'legacy_unverified'"),
                ("case_key", "TEXT NOT NULL DEFAULT 'legacy'"),
            ],
        }
        for table, additions in migrations.items():
            columns = {col[1] for col in conn.execute(f"PRAGMA table_info({table})")}
            for name, sqltype in additions:
                if name not in columns:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}")
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_recommendation(query, memo, db_path=None, mode="market"):
    timestamp = datetime.now(UTC).isoformat()
    with _conn(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO recommendations(ts, query, memo, mode) VALUES (?, ?, ?, ?)",
            (timestamp, query, json.dumps(memo, allow_nan=False), mode),
        )
        return int(cursor.lastrowid)


def record_outcome(
    rec_id,
    ticker,
    agent,
    predicted,
    actual_return_30d=None,
    correct=None,
    db_path=None,
    label_source="verified",
    case_key="30d",
):
    if actual_return_30d is not None and not math.isfinite(float(actual_return_30d)):
        raise ValueError("Outcome returns must be finite")
    if correct is not None and correct not in (True, False, 0, 1):
        raise ValueError("Correctness must be an explicit boolean")
    if correct is None:
        if predicted not in {"bullish", "bearish"} or actual_return_30d is None:
            raise ValueError("Non-directional predictions require explicit truth labels")
        correct = (predicted == "bullish" and actual_return_30d > 0) or (
            predicted == "bearish" and actual_return_30d < 0
        )
    with _conn(db_path) as conn:
        # Legacy databases have no UNIQUE constraint; the transaction also
        # makes repeated concurrent outcome submissions idempotent there.
        if conn.execute(
            "SELECT 1 FROM outcomes WHERE rec_id=? AND ticker=? AND agent=? AND case_key=?",
            (int(rec_id), ticker, agent, str(case_key)),
        ).fetchone():
            return
        conn.execute(
            """INSERT OR IGNORE INTO outcomes
            (rec_id, ticker, agent, predicted, actual_return_30d,
             was_correct, label_source, case_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                int(rec_id),
                ticker,
                agent,
                predicted,
                actual_return_30d,
                int(bool(correct)),
                label_source,
                str(case_key),
            ),
        )


def agent_weights(db_path=None, allowed_sources=None):
    """Smoothed accuracy, raw weight 0.5..1.5. No data means neutral weight 1.0.

    Production calls must filter to verified outcomes, not simulated labels.
    """
    sources = set({"verified", "synthetic_demo"} if allowed_sources is None else allowed_sources)
    weights = {"esg_verifier": 1.0, "market_analyst": 1.0}
    if not sources:
        return weights
    params = sorted(sources)
    placeholders = ",".join("?" for _ in params)
    with _conn(db_path) as conn:
        # Only "?" placeholders are interpolated; values are bound parameters.
        rows = conn.execute(  # nosec B608  # noqa: S608
            f"""SELECT agent, SUM(was_correct), COUNT(*) FROM outcomes
          WHERE label_source IN ({placeholders}) GROUP BY agent""",
            params,
        ).fetchall()
    for agent, hits, n in rows:
        if agent in weights and n >= 3:
            # Beta(2,2) prior prevents wild jumps from small samples.
            posterior = (hits + 2) / (n + 4)
            weights[agent] = round(0.5 + posterior, 3)
    return weights


def recent_recommendations(db_path=None, limit=10):
    with _conn(db_path) as conn:
        rows = conn.execute(
            "SELECT id, ts, query, memo, mode FROM recommendations ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 100)),),
        ).fetchall()
    results = []
    for row in rows:
        try:
            memo = json.loads(row[3])
        except (ValueError, TypeError):
            memo = {"error": "Stored memo is unreadable; original record retained"}
        results.append({"id": row[0], "ts": row[1], "query": row[2], "memo": memo, "mode": row[4]})
    return results
