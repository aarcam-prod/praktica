import sqlite3
import os
from datetime import datetime, date
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "mood_tracker.db")

def get_connection():

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            first_name  TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            reminder_time TEXT DEFAULT '20:00'
        );
        CREATE TABLE IF NOT EXISTS daily_entries (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            entry_date      TEXT NOT NULL,
            mood            INTEGER CHECK(mood BETWEEN 1 AND 5),
            work_hours      REAL CHECK(work_hours >= 0),
            sleep_hours     REAL CHECK(sleep_hours >= 0),
            comment         TEXT,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, entry_date)
        );

        CREATE INDEX IF NOT EXISTS idx_entries_user_date
            ON daily_entries(user_id, entry_date);
    """)
    conn.commit()
    conn.close()

def upsert_user(user_id: int, username: str, first_name: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name
    """, (user_id, username, first_name))
    conn.commit()
    conn.close()

def get_user(user_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_entry(user_id: int, mood: int, work_hours: float,
               sleep_hours: float, comment: str = None):
    today = date.today().isoformat()
    conn = get_connection()
    conn.execute("""
        INSERT INTO daily_entries (user_id, entry_date, mood, work_hours, sleep_hours, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, entry_date) DO UPDATE SET
            mood        = excluded.mood,
            work_hours  = excluded.work_hours,
            sleep_hours = excluded.sleep_hours,
            comment     = excluded.comment,
            created_at  = datetime('now')
    """, (user_id, today, mood, work_hours, sleep_hours, comment))
    conn.commit()
    conn.close()

def entry_exists_today(user_id: int) -> bool:
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute(
        "SELECT 1 FROM daily_entries WHERE user_id = ? AND entry_date = ?",
        (user_id, today)
    ).fetchone()
    conn.close()
    return row is not None

def get_stats(user_id: int, period: str = "week") -> dict:
    days = 7 if period == "week" else 30
    conn = get_connection()
    rows = conn.execute("""
        SELECT entry_date, mood, work_hours, sleep_hours, comment
        FROM daily_entries
        WHERE user_id = ?
          AND entry_date >= date('now', ? || ' days')
        ORDER BY entry_date DESC
    """, (user_id, f"-{days}")).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_entries(user_id: int, limit: int = 30) -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT entry_date, mood, work_hours, sleep_hours, comment
        FROM daily_entries
        WHERE user_id = ?
        ORDER BY entry_date DESC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_reminder_time(user_id: int, time_str: str):
    conn = get_connection()
    conn.execute(
        "UPDATE users SET reminder_time = ? WHERE user_id = ?",
        (time_str, user_id)
    )
    conn.commit()
    conn.close()

def clear_user_data(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM daily_entries WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_insights(user_id: int) -> dict:
    conn = get_connection()
    sleep_mood = conn.execute("""
        SELECT
            CASE
                WHEN sleep_hours < 6 THEN 'мало (<6ч)'
                WHEN sleep_hours BETWEEN 6 AND 8 THEN 'норма (6-8ч)'
                ELSE 'много (>8ч)'
            END as sleep_cat,
            ROUND(AVG(mood), 2) as avg_mood,
            COUNT(*) as cnt
        FROM daily_entries
        WHERE user_id = ? AND sleep_hours IS NOT NULL
        GROUP BY sleep_cat
        ORDER BY avg_mood DESC
    """, (user_id,)).fetchall()

    work_mood = conn.execute("""
        SELECT
            CASE
                WHEN work_hours < 2 THEN 'мало (<2ч)'
                WHEN work_hours BETWEEN 2 AND 6 THEN 'умеренно (2-6ч)'
                ELSE 'много (>6ч)'
            END as work_cat,
            ROUND(AVG(mood), 2) as avg_mood,
            COUNT(*) as cnt
        FROM daily_entries
        WHERE user_id = ? AND work_hours IS NOT NULL
        GROUP BY work_cat
        ORDER BY avg_mood DESC
    """, (user_id,)).fetchall()

    weekday_mood = conn.execute("""
        SELECT
            CASE strftime('%w', entry_date)
                WHEN '0' THEN 'Воскресенье'
                WHEN '1' THEN 'Понедельник'
                WHEN '2' THEN 'Вторник'
                WHEN '3' THEN 'Среда'
                WHEN '4' THEN 'Четверг'
                WHEN '5' THEN 'Пятница'
                WHEN '6' THEN 'Суббота'
            END as weekday,
            ROUND(AVG(mood), 2) as avg_mood
        FROM daily_entries
        WHERE user_id = ?
        GROUP BY strftime('%w', entry_date)
        ORDER BY avg_mood DESC
    """, (user_id,)).fetchall()
    conn.close()
    return {
        "sleep_mood": [dict(r) for r in sleep_mood],
        "work_mood":  [dict(r) for r in work_mood],
        "weekday_mood": [dict(r) for r in weekday_mood],
    }
