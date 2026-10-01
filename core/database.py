import sqlite3
from pathlib import Path


DB_PATH = Path("database/casino.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 1000
    )
    """)

    conn.commit()
    conn.close()


def add_user(user_id: int, username: str):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (user_id, username)
        VALUES (?, ?)
        """,
        (user_id, username)
    )

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE user_id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    conn.close()

    return user


def get_balance(user_id: int):
    user = get_user(user_id)

    if user:
        return user[2]

    return 0


def change_balance(user_id: int, amount: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
        """,
        (amount, user_id)
    )

    conn.commit()
    conn.close()