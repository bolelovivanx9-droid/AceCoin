import time

from core.database import get_connection


MAX_LOAN_AMOUNT = 10_000


def init_loan_db():
    """Создаёт таблицы кредитов и истории, если их ещё нет."""
    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL CHECK (amount > 0),
                remaining_amount INTEGER NOT NULL DEFAULT 0
                    CHECK (remaining_amount >= 0),
                repaid_amount INTEGER NOT NULL DEFAULT 0
                    CHECK (repaid_amount >= 0),
                status TEXT NOT NULL DEFAULT 'active',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_loans_user_status
            ON loans(user_id, status)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS loan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                loan_id INTEGER,
                action TEXT NOT NULL,
                amount INTEGER NOT NULL,
                remaining_after INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_loan_history_user
            ON loan_history(user_id, created_at)
        """)

        conn.commit()
    finally:
        conn.close()


def get_active_loan(user_id):
    """Возвращает активный кредит пользователя или None."""
    init_loan_db()

    conn = get_connection()

    try:
        return conn.execute("""
            SELECT *
            FROM loans
            WHERE user_id = ?
              AND status = 'active'
              AND remaining_amount > 0
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,)).fetchone()
    finally:
        conn.close()


def get_loan_history(user_id, limit=10):
    """Возвращает последние операции по кредитам."""
    init_loan_db()

    conn = get_connection()

    try:
        return conn.execute("""
            SELECT *
            FROM loan_history
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
    finally:
        conn.close()


def issue_loan(user_id, amount):
    """
    Выдаёт кредит.
    Результат: (True, данные кредита) или (False, код ошибки).
    """
    init_loan_db()

    if not isinstance(amount, int) or isinstance(amount, bool):
        return False, "invalid_amount"

    if amount < 1:
        return False, "invalid_amount"

    if amount > MAX_LOAN_AMOUNT:
        return False, "limit_exceeded"

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        user = conn.execute("""
            SELECT user_id, balance
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if user is None:
            conn.rollback()
            return False, "user_not_found"

        active_loan = conn.execute("""
            SELECT id
            FROM loans
            WHERE user_id = ?
              AND status = 'active'
              AND remaining_amount > 0
            LIMIT 1
        """, (user_id,)).fetchone()

        if active_loan is not None:
            conn.rollback()
            return False, "existing_debt"

        now = int(time.time())

        cursor = conn.execute("""
            INSERT INTO loans (
                user_id,
                amount,
                remaining_amount,
                repaid_amount,
                status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 0, 'active', ?, ?)
        """, (user_id, amount, amount, now, now))

        loan_id = cursor.lastrowid

        conn.execute("""
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
        """, (amount, user_id))

        conn.execute("""
            INSERT INTO loan_history (
                user_id,
                loan_id,
                action,
                amount,
                remaining_after,
                created_at
            )
            VALUES (?, ?, 'issued', ?, ?, ?)
        """, (user_id, loan_id, amount, amount, now))

        loan = conn.execute("""
            SELECT *
            FROM loans
            WHERE id = ?
        """, (loan_id,)).fetchone()

        conn.commit()
        return True, loan

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def repay_loan(user_id, amount):
    """
    Погашает кредит с обычного баланса пользователя.
    Результат: (True, данные кредита) или (False, код ошибки).
    """
    init_loan_db()

    if not isinstance(amount, int) or isinstance(amount, bool):
        return False, "invalid_amount"

    if amount < 1:
        return False, "invalid_amount"

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        user = conn.execute("""
            SELECT balance
            FROM users
            WHERE user_id = ?
        """, (user_id,)).fetchone()

        if user is None:
            conn.rollback()
            return False, "user_not_found"

        loan = conn.execute("""
            SELECT *
            FROM loans
            WHERE user_id = ?
              AND status = 'active'
              AND remaining_amount > 0
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,)).fetchone()

        if loan is None:
            conn.rollback()
            return False, "no_active_loan"

        if amount > loan["remaining_amount"]:
            conn.rollback()
            return False, "amount_exceeds_debt"

        if user["balance"] < amount:
            conn.rollback()
            return False, "insufficient_balance"

        remaining = loan["remaining_amount"] - amount
        repaid = loan["repaid_amount"] + amount
        now = int(time.time())
        status = "paid" if remaining == 0 else "active"

        conn.execute("""
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
        """, (amount, user_id))

        conn.execute("""
            UPDATE loans
            SET remaining_amount = ?,
                repaid_amount = ?,
                status = ?,
                updated_at = ?
            WHERE id = ?
        """, (remaining, repaid, status, now, loan["id"]))

        conn.execute("""
            INSERT INTO loan_history (
                user_id,
                loan_id,
                action,
                amount,
                remaining_after,
                created_at
            )
            VALUES (?, ?, 'repayment', ?, ?, ?)
        """, (user_id, loan["id"], amount, remaining, now))

        updated_loan = conn.execute("""
            SELECT *
            FROM loans
            WHERE id = ?
        """, (loan["id"],)).fetchone()

        conn.commit()
        return True, updated_loan

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()