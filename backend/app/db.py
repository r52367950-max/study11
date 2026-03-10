import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "memory.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT NOT NULL,
                subject TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                correct_total INTEGER NOT NULL DEFAULT 0,
                total_questions INTEGER NOT NULL DEFAULT 0,
                avg_duration_s INTEGER NOT NULL DEFAULT 0,
                top_pitfalls TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, subject)
            )
            """
        )


def upsert_practice(
    user_id: str,
    subject: str,
    total: int,
    correct: int,
    avg_duration_s: int,
    pitfall_hint: str | None,
) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE user_id=? AND subject=?", (user_id, subject)
        ).fetchone()
        pitfalls: list[str] = []
        if row:
            pitfalls = json.loads(row["top_pitfalls"])

        if pitfall_hint:
            hint = pitfall_hint.strip()
            if hint:
                pitfalls = [hint] + [p for p in pitfalls if p != hint]
                pitfalls = pitfalls[:5]

        if row:
            new_attempts = row["attempts"] + 1
            new_correct_total = row["correct_total"] + correct
            new_total_questions = row["total_questions"] + total
            prev_duration = row["avg_duration_s"]
            new_avg_duration = avg_duration_s if prev_duration <= 0 else int((prev_duration + avg_duration_s) / 2)
            conn.execute(
                """
                UPDATE profiles
                SET attempts=?, correct_total=?, total_questions=?, avg_duration_s=?,
                    top_pitfalls=?, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=? AND subject=?
                """,
                (
                    new_attempts,
                    new_correct_total,
                    new_total_questions,
                    new_avg_duration,
                    json.dumps(pitfalls, ensure_ascii=False),
                    user_id,
                    subject,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO profiles
                (user_id, subject, attempts, correct_total, total_questions, avg_duration_s, top_pitfalls)
                VALUES (?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    subject,
                    correct,
                    total,
                    avg_duration_s,
                    json.dumps(pitfalls, ensure_ascii=False),
                ),
            )


def get_profile(user_id: str, subject: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM profiles WHERE user_id=? AND subject=?", (user_id, subject)
        ).fetchone()


def build_report(user_id: str, subject: str) -> dict | None:
    row = get_profile(user_id, subject)
    if not row:
        return None

    total_questions = max(1, row["total_questions"])
    accuracy = row["correct_total"] / total_questions

    if accuracy >= 0.85:
        level = "A"
    elif accuracy >= 0.65:
        level = "B"
    else:
        level = "C"

    if row["attempts"] >= 10 and accuracy >= 0.75:
        trend = "improving"
    elif row["attempts"] >= 5 and accuracy < 0.6:
        trend = "needs_attention"
    else:
        trend = "stable"

    pitfalls = json.loads(row["top_pitfalls"])
    suggestions = [
        "每天至少做20分钟错题复盘。",
        "每道题先写已知条件再动笔计算。",
        "对最近3次高频错误类型做专项练习。",
    ]
    if pitfalls:
        suggestions.insert(0, f"优先攻克高频问题：{pitfalls[0]}。")

    return {
        "user_id": row["user_id"],
        "subject": row["subject"],
        "level": level,
        "trend": trend,
        "attempts": row["attempts"],
        "accuracy": round(accuracy, 3),
        "top_pitfalls": pitfalls,
        "suggestions": suggestions[:4],
    }
