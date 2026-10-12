import sqlite3

from core.database import get_connection, get_user_stats


ACHIEVEMENTS = {
    "first_game": {
        "name": "Первый шаг",
        "emoji": "🌱",
        "description": "Завершить первую игру",
        "type": "games",
        "target": 1,
        "reward_xp": 10,
    },
    "games_10": {
        "name": "Игрок",
        "emoji": "🎮",
        "description": "Завершить 10 игр",
        "type": "games",
        "target": 10,
        "reward_xp": 25,
    },
    "games_100": {
        "name": "Ветеран",
        "emoji": "🏅",
        "description": "Завершить 100 игр",
        "type": "games",
        "target": 100,
        "reward_xp": 100,
    },
    "level_5": {
        "name": "Новичок прогрессии",
        "emoji": "⭐",
        "description": "Достичь 5-го уровня",
        "type": "level",
        "target": 5,
        "reward_xp": 50,
    },
    "level_20": {
        "name": "Опытный игрок",
        "emoji": "💎",
        "description": "Достичь 20-го уровня",
        "type": "level",
        "target": 20,
        "reward_xp": 250,
    },
}


def init_achievements_db():
    """Создаёт таблицу достижений, не удаляя существующие данные."""
    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at INTEGER NOT NULL DEFAULT (
                    CAST(strftime('%s', 'now') AS INTEGER)
                ),
                PRIMARY KEY (user_id, achievement_id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_progress(user_id: int):
    """Возвращает актуальный прогресс игрока."""
    stats = get_user_stats(user_id)

    if not stats:
        return {}

    return {
        "games": stats["games_played"],
        "level": stats["level"],
    }


def check_achievements(user_id: int):
    """
    Проверяет достижения и выдаёт награду XP один раз.
    Возвращает список новых достижений.
    """
    progress = get_progress(user_id)

    if not progress:
        return []

    unlocked_now = []
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        for achievement_id, achievement in ACHIEVEMENTS.items():
            current = progress[achievement["type"]]

            if current < achievement["target"]:
                continue

            cursor.execute(
                """
                INSERT OR IGNORE INTO user_achievements (
                    user_id, achievement_id
                )
                VALUES (?, ?)
                """,
                (user_id, achievement_id),
            )

            if cursor.rowcount != 1:
                continue

            reward = achievement["reward_xp"]

            cursor.execute(
                """
                UPDATE users
                SET xp = xp + ?
                WHERE user_id = ?
                """,
                (reward, user_id),
            )

            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError(
                    "Не найден профиль игрока"
                )

            unlocked_now.append({
                "id": achievement_id,
                **achievement,
            })

        conn.commit()
        return unlocked_now

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def get_unlocked_achievements(user_id: int):
    """Возвращает список уже полученных достижений."""
    conn = get_connection()

    try:
        rows = conn.execute(
            """
            SELECT achievement_id, unlocked_at
            FROM user_achievements
            WHERE user_id = ?
            ORDER BY unlocked_at ASC, achievement_id ASC
            """,
            (user_id,),
        ).fetchall()

        return {
            row["achievement_id"]: row["unlocked_at"]
            for row in rows
        }
    finally:
        conn.close()


def get_achievement_summary(user_id: int):
    """Формирует данные для экрана достижений."""
    check_achievements(user_id)

    progress = get_progress(user_id)
    unlocked = get_unlocked_achievements(user_id)
    result = []

    for achievement_id, achievement in ACHIEVEMENTS.items():
        current = progress.get(achievement["type"], 0)
        target = achievement["target"]
        is_unlocked = achievement_id in unlocked

        result.append({
            "id": achievement_id,
            **achievement,
            "current": min(current, target),
            "unlocked": is_unlocked,
            "unlocked_at": unlocked.get(achievement_id),
        })

    return result