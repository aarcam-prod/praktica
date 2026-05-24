CREATE TABLE IF NOT EXISTS users (
    user_id      INTEGER PRIMARY KEY,          -- Telegram user_id
    username     TEXT,                          -- @username (может быть NULL)
    first_name   TEXT,                          -- Имя пользователя
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    reminder_time TEXT DEFAULT '20:00'          -- Время ежедневного напоминания
);


CREATE TABLE IF NOT EXISTS daily_entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    entry_date   TEXT NOT NULL,                 -- ISO 8601: '2025-06-01'
    mood         INTEGER CHECK(mood BETWEEN 1 AND 5),
    work_hours   REAL    CHECK(work_hours  >= 0),
    sleep_hours  REAL    CHECK(sleep_hours >= 0),
    comment      TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, entry_date)                -- Одна запись в день
);


CREATE INDEX IF NOT EXISTS idx_entries_user_date
    ON daily_entries(user_id, entry_date);

CREATE INDEX IF NOT EXISTS idx_entries_date
    ON daily_entries(entry_date);


CREATE VIEW IF NOT EXISTS weekly_stats AS
SELECT
    user_id,
    ROUND(AVG(mood),        2) AS avg_mood,
    ROUND(AVG(work_hours),  2) AS avg_work_hours,
    ROUND(AVG(sleep_hours), 2) AS avg_sleep_hours,
    COUNT(*)                   AS days_tracked
FROM daily_entries
WHERE entry_date >= date('now', '-7 days')
GROUP BY user_id;


CREATE VIEW IF NOT EXISTS monthly_stats AS
SELECT
    user_id,
    ROUND(AVG(mood),        2) AS avg_mood,
    ROUND(AVG(work_hours),  2) AS avg_work_hours,
    ROUND(AVG(sleep_hours), 2) AS avg_sleep_hours,
    COUNT(*)                   AS days_tracked
FROM daily_entries
WHERE entry_date >= date('now', '-30 days')
GROUP BY user_id;
