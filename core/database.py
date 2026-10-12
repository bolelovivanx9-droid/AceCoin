import sqlite3
import time
from pathlib import Path


DB_PATH = Path("database/casino.db")

DAILY_BONUS_AMOUNT = 250
DAILY_BONUS_INTERVAL = 24 * 60 * 60

XP_PER_LEVEL = 100

RANKS = [
    (1, "Камень", "🪨"),
    (3, "Бронза I", "🥉"),
    (5, "Бронза II", "🥉"),
    (7, "Бронза III", "🥉"),
    (10, "Серебро I", "🥈"),
    (13, "Серебро II", "🥈"),
    (16, "Серебро III", "🥈"),
    (20, "Золото I", "🥇"),
    (25, "Золото II", "🥇"),
    (30, "Золото III", "🥇"),
    (35, "Платина", "💠"),
    (40, "Алмаз", "💎"),
    (50, "Мастер", "👑"),
    (65, "Грандмастер", "🔥"),
    (80, "Легенда", "🌌"),
]


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _check_achievements(user_id: int):
    """Проверяет достижения после изменения прогресса."""
    try:
        from core.achievements import check_achievements
        check_achievements(user_id)
    except Exception:
        # Ошибка достижений не должна ломать экономику или игру.
        import logging
        logging.getLogger(__name__).exception(
            "Не удалось проверить достижения игрока %s",
            user_id,
        )


def init_db():
    """Создаёт таблицы и добавляет недостающие поля без удаления данных."""
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 1000
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_bonus (
                user_id INTEGER PRIMARY KEY,
                last_claim INTEGER NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                amount INTEGER NOT NULL CHECK (amount > 0),
                created_at INTEGER NOT NULL
            )
        """)

        cursor.execute("PRAGMA table_info(users)")
        existing_columns = {
            row["name"] for row in cursor.fetchall()
        }

        new_columns = {
            "xp": "INTEGER NOT NULL DEFAULT 0",
            "wins": "INTEGER NOT NULL DEFAULT 0",
            "losses": "INTEGER NOT NULL DEFAULT 0",
            "games_played": "INTEGER NOT NULL DEFAULT 0",
            "total_winnings": "INTEGER NOT NULL DEFAULT 0",
            "bank_balance": "INTEGER NOT NULL DEFAULT 0",
        }

        for column_name, column_type in new_columns.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE users ADD COLUMN "
                    f"{column_name} {column_type}"
                )

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transfers_sender
            ON transfers (sender_id, created_at DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transfers_recipient
            ON transfers (recipient_id, created_at DESC)
        """)

        conn.commit()

    finally:
        conn.close()

    # Таблицу достижений создаёт модуль достижений.
    from core.achievements import init_achievements_db
    init_achievements_db()


def add_user(user_id: int, username: str):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO users (user_id, username)
            VALUES (?, ?)
            """,
            (user_id, username),
        )

        cursor.execute(
            """
            UPDATE users
            SET username = ?
            WHERE user_id = ?
            """,
            (username, user_id),
        )

        conn.commit()

    finally:
        conn.close()


def get_user(user_id: int):
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        )
        return cursor.fetchone()

    finally:
        conn.close()


def get_user_by_username(username: str):
    """Ищет зарегистрированного игрока по Telegram username."""
    if not username:
        return None

    username = username.strip().lstrip("@")

    if not username or username.lower() == "unknown":
        return None

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE username IS NOT NULL
              AND username != ''
              AND LOWER(username) = LOWER(?)
              AND LOWER(username) != 'unknown'
            LIMIT 1
            """,
            (username,),
        )
        return cursor.fetchone()

    finally:
        conn.close()


def get_balance(user_id: int) -> int:
    user = get_user(user_id)
    return user["balance"] if user else 0


def change_balance(user_id: int, amount: int):
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (amount, user_id),
        )
        conn.commit()

    finally:
        conn.close()


def remove_money(user_id: int, amount: int):
    if amount <= 0:
        return False

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
              AND balance >= ?
            """,
            (amount, user_id, amount),
        )

        success = cursor.rowcount > 0
        conn.commit()
        return success

    finally:
        conn.close()


# ==================================================
# БАНК
# ==================================================

def get_bank_balance(user_id: int) -> int:
    user = get_user(user_id)
    return user["bank_balance"] if user else 0


def deposit_money(user_id: int, amount: int):
    """Переводит монеты с основного баланса в банк."""
    if isinstance(amount, bool) or not isinstance(amount, int):
        return False

    if amount <= 0:
        return False

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            UPDATE users
            SET balance = balance - ?,
                bank_balance = bank_balance + ?
            WHERE user_id = ?
              AND balance >= ?
            """,
            (amount, amount, user_id, amount),
        )

        success = cursor.rowcount == 1

        if success:
            conn.commit()
        else:
            conn.rollback()

        return success

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def withdraw_money(user_id: int, amount: int):
    """Переводит монеты из банка на основной баланс."""
    if isinstance(amount, bool) or not isinstance(amount, int):
        return False

    if amount <= 0:
        return False

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            UPDATE users
            SET bank_balance = bank_balance - ?,
                balance = balance + ?
            WHERE user_id = ?
              AND bank_balance >= ?
            """,
            (amount, amount, user_id, amount),
        )

        success = cursor.rowcount == 1

        if success:
            conn.commit()
        else:
            conn.rollback()

        return success

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ==================================================
# ПЕРЕВОДЫ
# ==================================================

def transfer_money(
    sender_id: int,
    recipient_id: int,
    amount: int,
):
    """Безопасно переводит монеты между игроками."""
    if isinstance(amount, bool) or not isinstance(amount, int):
        return False, "invalid_amount"

    if amount <= 0:
        return False, "invalid_amount"

    if sender_id == recipient_id:
        return False, "same_user"

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (sender_id,),
        )
        if not cursor.fetchone():
            conn.rollback()
            return False, "sender_not_found"

        cursor.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (recipient_id,),
        )
        if not cursor.fetchone():
            conn.rollback()
            return False, "recipient_not_found"

        cursor.execute(
            """
            UPDATE users
            SET balance = balance - ?
            WHERE user_id = ?
              AND balance >= ?
            """,
            (amount, sender_id, amount),
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return False, "insufficient_funds"

        cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (amount, recipient_id),
        )

        if cursor.rowcount != 1:
            conn.rollback()
            return False, "recipient_not_found"

        cursor.execute(
            """
            INSERT INTO transfers (
                sender_id, recipient_id, amount, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                sender_id,
                recipient_id,
                amount,
                int(time.time()),
            ),
        )

        conn.commit()
        return True, "success"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_transfer_history(user_id: int, limit: int = 10):
    """Возвращает последние отправленные и полученные переводы."""
    limit = max(1, min(int(limit), 100))
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, sender_id, recipient_id, amount, created_at
            FROM transfers
            WHERE sender_id = ? OR recipient_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (user_id, user_id, limit),
        )
        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()


# ==================================================
# ЕЖЕДНЕВНЫЙ БОНУС
# ==================================================

def claim_daily_bonus(user_id: int):
    """Пытается выдать ежедневный бонус."""
    now = int(time.time())
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT last_claim FROM daily_bonus WHERE user_id = ?",
            (user_id,),
        )
        result = cursor.fetchone()

        if result:
            remaining = DAILY_BONUS_INTERVAL - (
                now - result["last_claim"]
            )

            if remaining > 0:
                conn.rollback()
                return False, remaining

            cursor.execute(
                """
                UPDATE daily_bonus
                SET last_claim = ?
                WHERE user_id = ?
                """,
                (now, user_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO daily_bonus (user_id, last_claim)
                VALUES (?, ?)
                """,
                (user_id, now),
            )

        cursor.execute(
            """
            UPDATE users
            SET balance = balance + ?
            WHERE user_id = ?
            """,
            (DAILY_BONUS_AMOUNT, user_id),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return False, 0

        conn.commit()
        return True, 0

    finally:
        conn.close()


# ==================================================
# УРОВНИ И РАНГИ
# ==================================================

def get_level_from_xp(xp: int) -> int:
    """Уровень 1 начинается с 0 XP; каждые 100 XP — новый уровень."""
    return max(1, xp // XP_PER_LEVEL + 1)


def get_rank(level: int) -> dict:
    """Возвращает ранг, подходящий под указанный уровень."""
    selected_rank = RANKS[0]

    for min_level, name, emoji in RANKS:
        if level >= min_level:
            selected_rank = (min_level, name, emoji)
        else:
            break

    min_level, name, emoji = selected_rank

    return {
        "name": name,
        "emoji": emoji,
        "min_level": min_level,
    }


def get_user_stats(user_id: int):
    """Возвращает статистику игрока или None."""
    user = get_user(user_id)

    if not user:
        return None

    xp = user["xp"]
    level = get_level_from_xp(xp)
    rank = get_rank(level)
    xp_in_level = xp % XP_PER_LEVEL

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "balance": user["balance"],
        "xp": xp,
        "level": level,
        "rank": rank["name"],
        "rank_emoji": rank["emoji"],
        "wins": user["wins"],
        "losses": user["losses"],
        "games_played": user["games_played"],
        "total_winnings": user["total_winnings"],
        "xp_in_level": xp_in_level,
        "xp_to_next_level": XP_PER_LEVEL - xp_in_level,
        "xp_per_level": XP_PER_LEVEL,
    }


def add_xp(user_id: int, amount: int):
    """Начисляет XP и проверяет достижения."""
    if isinstance(amount, bool) or not isinstance(amount, int):
        return get_user_stats(user_id)

    if amount <= 0:
        return get_user_stats(user_id)

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET xp = xp + ?
            WHERE user_id = ?
            """,
            (amount, user_id),
        )

        if cursor.rowcount == 0:
            conn.commit()
            return None

        conn.commit()

    finally:
        conn.close()

    _check_achievements(user_id)
    return get_user_stats(user_id)


def record_game(
    user_id: int,
    won: bool,
    winnings: int = 0,
    xp_reward: int = 0,
    draw: bool = False,
):
    """
    Записывает завершённую игру и проверяет достижения.

    won=True  — победа.
    draw=True — ничья.
    Иначе — поражение.
    """
    if winnings < 0 or xp_reward < 0:
        raise ValueError(
            "winnings и xp_reward не могут быть отрицательными"
        )

    if draw:
        won = False

    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            UPDATE users
            SET
                games_played = games_played + 1,
                wins = wins + ?,
                losses = losses + ?,
                total_winnings = total_winnings + ?,
                xp = xp + ?
            WHERE user_id = ?
            """,
            (
                1 if won else 0,
                0 if won and not draw else (0 if draw else 1),
                winnings,
                xp_reward,
                user_id,
            ),
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return None

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

    _check_achievements(user_id)
    return get_user_stats(user_id)


# ==================================================
# РЕЙТИНГ ИГРОКОВ
# ==================================================

def get_top_users(limit: int = 10):
    """Возвращает игроков для таблицы лидеров."""
    limit = max(1, min(int(limit), 50))
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                user_id, username, balance, xp, wins, losses,
                games_played, total_winnings
            FROM users
            ORDER BY xp DESC, wins DESC, balance DESC, user_id ASC
            LIMIT ?
            """,
            (limit,),
        )

        result = []

        for position, user in enumerate(cursor.fetchall(), start=1):
            xp = user["xp"]
            level = get_level_from_xp(xp)
            rank = get_rank(level)

            result.append({
                "position": position,
                "user_id": user["user_id"],
                "username": user["username"],
                "balance": user["balance"],
                "xp": xp,
                "level": level,
                "rank": rank["name"],
                "rank_emoji": rank["emoji"],
                "wins": user["wins"],
                "losses": user["losses"],
                "games_played": user["games_played"],
                "total_winnings": user["total_winnings"],
            })

        return result

    finally:
        conn.close()


def get_user_rank(user_id: int):
    """Возвращает место игрока в общем рейтинге или None."""
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, xp, wins, balance
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )

        user = cursor.fetchone()

        if not user:
            return None

        cursor.execute(
            """
            SELECT COUNT(*) + 1 AS position
            FROM users
            WHERE
                xp > ?
                OR (xp = ? AND wins > ?)
                OR (xp = ? AND wins = ? AND balance > ?)
                OR (
                    xp = ?
                    AND wins = ?
                    AND balance = ?
                    AND user_id < ?
                )
            """,
            (
                user["xp"],
                user["xp"],
                user["wins"],
                user["xp"],
                user["wins"],
                user["balance"],
                user["xp"],
                user["wins"],
                user["balance"],
                user["user_id"],
            ),
        )

        return cursor.fetchone()["position"]

    finally:
        conn.close()


def get_daily_bonus_remaining(user_id: int) -> int:
    """Возвращает секунды до следующего бонуса; 0 означает, что он доступен."""
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT last_claim FROM daily_bonus WHERE user_id = ?",
            (user_id,),
        )
        result = cursor.fetchone()

        if not result:
            return 0

        remaining = DAILY_BONUS_INTERVAL - (
            int(time.time()) - result["last_claim"]
        )

        return max(0, remaining)

    finally:
        conn.close()
