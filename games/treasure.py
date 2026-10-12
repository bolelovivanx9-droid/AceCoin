import random


games = {}

GRID_SIZE = 5
TOTAL_CELLS = GRID_SIZE * GRID_SIZE

TREASURES_COUNT = 20
BOMBS_COUNT = 5
BOMBS_TO_LOSE = 3

MULTIPLIER_STEP = 0.25
BASE_MULTIPLIER = 1.0


def get_multiplier(treasures: int) -> float:
    """Возвращает множитель в зависимости от найденных сокровищ."""
    return BASE_MULTIPLIER + treasures * MULTIPLIER_STEP


def calculate_win(bet: int, treasures: int) -> int:
    """Рассчитывает выплату с учётом множителя."""
    multiplier = get_multiplier(treasures)
    return int(round(bet * multiplier))


def create_game(user_id: int, bet: int):
    """Создаёт новое игровое поле."""

    treasure_positions = set(
        random.sample(
            range(TOTAL_CELLS),
            TREASURES_COUNT,
        )
    )

    cells = {}

    for number in range(TOTAL_CELLS):
        if number in treasure_positions:
            cells[number] = "💰"
        else:
            cells[number] = "💣"

    games[user_id] = {
        "cells": cells,
        "opened": [],
        "bet": bet,
        "treasures": 0,
        "bombs": 0,
        "finished": False,
    }


def get_cell(user_id: int, number: int):
    """Открывает клетку и обновляет состояние игры."""

    game = games.get(user_id)

    if not game or game["finished"]:
        return None

    if not isinstance(number, int):
        return None

    if number < 0 or number >= TOTAL_CELLS:
        return None

    if number in game["opened"]:
        return "opened"

    game["opened"].append(number)

    result = game["cells"][number]

    if result == "💰":
        game["treasures"] += 1

    elif result == "💣":
        game["bombs"] += 1

        # Игра завершается только после третьего попадания на бомбу.
        if game["bombs"] >= BOMBS_TO_LOSE:
            game["finished"] = True

    return result


def get_bet(user_id: int) -> int:
    game = games.get(user_id)

    if game:
        return game["bet"]

    return 0


def get_game(user_id: int):
    return games.get(user_id)


def get_opened(user_id: int) -> list:
    game = games.get(user_id)

    if game:
        return game["opened"].copy()

    return []


def get_stats(user_id: int) -> dict:
    game = games.get(user_id)

    if not game:
        return {
            "treasures": 0,
            "bombs": 0,
            "opened": 0,
        }

    return {
        "treasures": game["treasures"],
        "bombs": game["bombs"],
        "opened": len(game["opened"]),
    }


def end_game(user_id: int):
    game = games.get(user_id)

    if game:
        game["finished"] = True


def delete_game(user_id: int):
    games.pop(user_id, None)