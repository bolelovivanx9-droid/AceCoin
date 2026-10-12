
import json
from datetime import date

from core.database import (
    get_connection,
    get_user_stats,
    change_balance,
    add_xp,
)


DAILY_QUESTS = {
    "play_3": {
        "name": "🎮 Завершить 3 игры",
        "target": 3,
        "reward_money": 150,
        "reward_xp": 10,
        "stat": "games_played",
    },
    "win_1": {
        "name": "🏆 Одержать 1 победу",
        "target": 1,
        "reward_money": 100,
        "reward_xp": 10,
        "stat": "wins",
    },
    "play_5": {
        "name": "🔥 Завершить 5 игр",
        "target": 5,
        "reward_money": 300,
        "reward_xp": 25,
        "stat": "games_played",
    },
}


def init_quests_db():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_quests (
                user_id INTEGER NOT NULL,
                quest_date TEXT NOT NULL,
                start_games INTEGER NOT NULL DEFAULT 0,
                start_wins INTEGER NOT NULL DEFAULT 0,
                claimed TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY (user_id, quest_date)
            )
            """
        )
        conn.commit()


def _get_or_create_daily_record(user_id: int):
    today = date.today().isoformat()

    stats = get_user_stats(user_id) or {}
    games = int(stats.get("games_played", 0))
    wins = int(stats.get("wins", 0))

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO daily_quests (
                user_id,
                quest_date,
                start_games,
                start_wins,
                claimed
            )
            VALUES (?, ?, ?, ?, '[]')
            """,
            (user_id, today, games, wins),
        )

        row = conn.execute(
            """
            SELECT start_games, start_wins, claimed
            FROM daily_quests
            WHERE user_id = ? AND quest_date = ?
            """,
            (user_id, today),
        ).fetchone()

        conn.commit()

    return today, row


def get_daily_quests(user_id: int):
    today, row = _get_or_create_daily_record(user_id)

    stats = get_user_stats(user_id) or {}
    games = int(stats.get("games_played", 0))
    wins = int(stats.get("wins", 0))

    start_games = int(row["start_games"])
    start_wins = int(row["start_wins"])

    progress_values = {
        "games_played": max(0, games - start_games),
        "wins": max(0, wins - start_wins),
    }

    try:
        claimed = set(json.loads(row["claimed"]))
    except (TypeError, ValueError):
        claimed = set()

    result = []

    for quest_id, quest in DAILY_QUESTS.items():
        progress = min(
            quest["target"],
            progress_values[quest["stat"]],
        )

        result.append(
            {
                "id": quest_id,
                "name": quest["name"],
                "target": quest["target"],
                "progress": progress,
                "reward_money": quest["reward_money"],
                "reward_xp": quest["reward_xp"],
                "claimed": quest_id in claimed,
                "completed": progress >= quest["target"],
            }
        )

    return result


def claim_daily_quest(user_id: int, quest_id: str):
    if quest_id not in DAILY_QUESTS:
        return False, "Неизвестный квест."

    quests = get_daily_quests(user_id)
    quest = next(
        (item for item in quests if item["id"] == quest_id),
        None,
    )

    if not quest:
        return False, "Квест не найден."

    if quest["claimed"]:
        return False, "Награда за этот квест уже получена."

    if not quest["completed"]:
        return False, "Сначала выполни задание."

    today = date.today().isoformat()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT claimed
            FROM daily_quests
            WHERE user_id = ? AND quest_date = ?
            """,
            (user_id, today),
        ).fetchone()

        if not row:
            return False, "Не удалось найти запись квеста."

        try:
            claimed = set(json.loads(row["claimed"]))
        except (TypeError, ValueError):
            claimed = set()

        if quest_id in claimed:
            return False, "Награда за этот квест уже получена."

        claimed.add(quest_id)

        conn.execute(
            """
            UPDATE daily_quests
            SET claimed = ?
            WHERE user_id = ? AND quest_date = ?
            """,
            (
                json.dumps(sorted(claimed)),
                user_id,
                today,
            ),
        )
        conn.commit()

    change_balance(user_id, quest["reward_money"])
    add_xp(user_id, quest["reward_xp"])

    return True, (
        f"Получено: +{quest['reward_money']:,} $ "
        f"и +{quest['reward_xp']} XP!"
    )
