import random
import time

from core.database import get_connection


STEAL_COOLDOWN = 24 * 60 * 60
STEAL_SUCCESS_CHANCE = 15
MIN_STEAL_AMOUNT = 50
MAX_STEAL_AMOUNT = 300


def init_steal_db():
    """Создаёт таблицу попыток кражи, сохраняя существующие данные."""

    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steal_attempts (
                user_id INTEGER PRIMARY KEY,
                last_attempt INTEGER NOT NULL
            )
        """)

        conn.commit()

    finally:
        conn.close()


def attempt_steal(
    thief_id: int,
    target_id: int,
) -> dict:
    """
    Выполняет одну попытку кражи в транзакции SQLite.

    Одна попытка в 24 часа на игрока независимо от чата
    и способа указания цели.
    """

    if thief_id == target_id:
        return {"status": "same_user"}

    now = int(time.time())
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        # Проверяем существование обоих игроков.
        cursor.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (thief_id,),
        )
        thief = cursor.fetchone()

        if not thief:
            conn.rollback()
            return {"status": "thief_not_found"}

        cursor.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (target_id,),
        )
        target = cursor.fetchone()

        if not target:
            conn.rollback()
            return {"status": "target_not_found"}

        # Проверяем общую суточную перезарядку.
        cursor.execute(
            """
            SELECT last_attempt
            FROM steal_attempts
            WHERE user_id = ?
            """,
            (thief_id,),
        )
        previous_attempt = cursor.fetchone()

        if previous_attempt:
            elapsed = now - previous_attempt["last_attempt"]
            remaining = STEAL_COOLDOWN - elapsed

            if remaining > 0:
                conn.rollback()
                return {
                    "status": "cooldown",
                    "remaining": remaining,
                }

        # Попытка считается использованной независимо от удачи.
        cursor.execute(
            """
            INSERT INTO steal_attempts (user_id, last_attempt)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET last_attempt = excluded.last_attempt
            """,
            (thief_id, now),
        )

        target_balance = target["balance"]

        # Даже попытка украсть у игрока без денег расходует попытку.
        if target_balance <= 0:
            conn.commit()
            return {"status": "target_broke"}

        # Проверяем шанс успеха.
        if random.randint(1, 100) > STEAL_SUCCESS_CHANCE:
            conn.commit()
            return {"status": "failed"}

        # Сумма не может быть больше баланса жертвы.
        max_amount = min(MAX_STEAL_AMOUNT, target_balance)
        min_amount = min(MIN_STEAL_AMOUNT, max_amount)
        amount = random.randint(min_amount, max_amount)

        # Сначала списываем у цели.
        cursor.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
              AND balance >= ?
            """,
            (amount, target_id, amount),
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return {"status": "balance_changed"}

        # Затем начисляем вору в той же транзакции.
        cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (amount, thief_id),
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return {"status": "balance_changed"}

        cursor.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (thief_id,),
        )
        thief_after = cursor.fetchone()

        cursor.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (target_id,),
        )
        target_after = cursor.fetchone()

        conn.commit()

        return {
            "status": "success",
            "amount": amount,
            "thief_balance": thief_after["balance"],
            "target_balance": target_after["balance"],
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()