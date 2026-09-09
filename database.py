import sqlite3
from datetime import datetime, timedelta

DB_NAME = "finance.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def add_expense(user_id: int, username: str, category: str, amount: float):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        INSERT INTO expenses (user_id, username, category, amount, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, username, category, amount, now),
    )

    conn.commit()
    conn.close()


def get_expenses_period(days: int):
    conn = get_connection()
    cursor = conn.cursor()

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        SELECT username, category, amount, created_at
        FROM expenses
        WHERE created_at >= ?
        ORDER BY created_at DESC
        """,
        (cutoff,),
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_month_summary():
    conn = get_connection()
    cursor = conn.cursor()

    month_start = datetime.now().strftime("%Y-%m-01 00:00:00")

    cursor.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE created_at >= ?
        """,
        (month_start,),
    )

    count, total = cursor.fetchone()
    conn.close()

    return count, total

def delete_last_expense(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id
        FROM expenses
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False

    expense_id = row[0]

    cursor.execute(
        """
        DELETE FROM expenses
        WHERE id = ?
        """,
        (expense_id,)
    )

    conn.commit()
    conn.close()

    return True


