import re
import sqlite3
import time
from pathlib import Path


DB_PATH = Path("database/casino.db")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_promo_db():
    """Создаёт таблицы промокодов, не удаляя существующие данные."""
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                amount INTEGER NOT NULL CHECK (amount > 0),
                created_by INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS promo_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                redeemed_at INTEGER NOT NULL,
                UNIQUE (code, user_id),
                FOREIGN KEY (code) REFERENCES promo_codes(code)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_promo_redemptions_user
            ON promo_redemptions (user_id, redeemed_at DESC)
        """)

        conn.commit()
    finally:
        conn.close()


def create_promo(code: str, amount: int, admin_id: int):
    """Создаёт промокод. Возвращает (успех, статус)."""
    if not isinstance(code, str):
        return False, "invalid_code"

    code = code.strip().upper()

    if not re.fullmatch(r"[A-Z0-9_-]{3,32}", code):
        return False, "invalid_code"

    if isinstance(amount, bool) or not isinstance(amount, int):
        return False, "invalid_amount"

    if amount <= 0:
        return False, "invalid_amount"

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO promo_codes (code, amount, created_by, created_at)
            VALUES (?, ?, ?, ?)
        """, (code, amount, admin_id, int(time.time())))

        conn.commit()
        return True, "success"

    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "already_exists"

    finally:
        conn.close()


def redeem_promo(user_id: int, code: str):
    """Атомарно активирует промокод и начисляет награду."""
    if not isinstance(code, str):
        return False, "invalid_code", 0

    code = code.strip().upper()

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT amount FROM promo_codes WHERE code = ?",
            (code,),
        )
        promo = cursor.fetchone()

        if not promo:
            conn.rollback()
            return False, "not_found", 0

        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
        )
        user = cursor.fetchone()

        if not user:
            conn.rollback()
            return False, "user_not_found", 0

        cursor.execute("""
            SELECT id
            FROM promo_redemptions
            WHERE code = ? AND user_id = ?
        """, (code, user_id))

        if cursor.fetchone():
            conn.rollback()
            return False, "already_used", 0

        amount = promo["amount"]

        cursor.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
        """, (amount, user_id))

        if cursor.rowcount != 1:
            conn.rollback()
            return False, "user_not_found", 0

        cursor.execute("""
            INSERT INTO promo_redemptions (code, user_id, redeemed_at)
            VALUES (?, ?, ?)
        """, (code, user_id, int(time.time())))

        conn.commit()
        return True, "success", amount

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()