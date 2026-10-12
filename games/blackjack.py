import random
from threading import RLock


STARTING_CARDS = 2

# Активные игры хранятся в памяти до перезапуска бота.
_games = {}
_games_lock = RLock()


def _new_deck():
    """Создаёт и перемешивает колоду из 52 карт."""
    suits = ["♠", "♥", "♦", "♣"]
    ranks = [
        ("2", 2), ("3", 3), ("4", 4), ("5", 5),
        ("6", 6), ("7", 7), ("8", 8), ("9", 9),
        ("10", 10), ("J", 10), ("Q", 10), ("K", 10),
        ("A", 11),
    ]

    deck = [
        {"rank": rank, "value": value, "suit": suit}
        for suit in suits
        for rank, value in ranks
    ]

    random.shuffle(deck)
    return deck


def _draw_card(game):
    """Берёт карту из колоды."""
    if not game["deck"]:
        game["deck"] = _new_deck()

    return game["deck"].pop()


def _hand_value(cards):
    """Считает очки, учитывая туз как 1 или 11."""
    total = sum(card["value"] for card in cards)
    aces = sum(1 for card in cards if card["rank"] == "A")

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total


def _is_blackjack(cards):
    return len(cards) == 2 and _hand_value(cards) == 21


def _format_cards(cards):
    return " ".join(
        f"{card['rank']}{card['suit']}"
        for card in cards
    )


def _public_game(game):
    """Возвращает копию игровых данных для обработчика."""
    return {
        "user_id": game["user_id"],
        "bet": game["bet"],
        "player_cards": [
            dict(card) for card in game["player_cards"]
        ],
        "dealer_cards": [
            dict(card) for card in game["dealer_cards"]
        ],
        "player_score": _hand_value(game["player_cards"]),
        "dealer_score": _hand_value(game["dealer_cards"]),
        "finished": game["finished"],
        "result": game.get("result"),
        "deck": [dict(card) for card in game["deck"]],
    }


def start_game(user_id: int, bet: int):
    """Создаёт раунд. Возвращает игру или None, если раунд уже идёт."""
    if bet <= 0:
        raise ValueError("Ставка должна быть больше нуля.")

    with _games_lock:
        if user_id in _games:
            return None

        game = {
            "user_id": user_id,
            "bet": bet,
            "deck": _new_deck(),
            "player_cards": [],
            "dealer_cards": [],
            "finished": False,
            "result": None,
        }

        game["player_cards"].append(_draw_card(game))
        game["dealer_cards"].append(_draw_card(game))
        game["player_cards"].append(_draw_card(game))
        game["dealer_cards"].append(_draw_card(game))

        _games[user_id] = game

        return _public_game(game)


def get_game(user_id: int):
    """Возвращает текущий раунд или None."""
    with _games_lock:
        game = _games.get(user_id)

        if game is None:
            return None

        return _public_game(game)


def hit(user_id: int):
    """Игрок берёт карту. При переборе раунд завершается."""
    with _games_lock:
        game = _games.get(user_id)

        if game is None or game["finished"]:
            return None

        game["player_cards"].append(_draw_card(game))

        if _hand_value(game["player_cards"]) > 21:
            game["finished"] = True
            game["result"] = "lose"

        return _public_game(game)


def stand(user_id: int):
    """Игрок остановился; дилер добирает карты до 17."""
    with _games_lock:
        game = _games.get(user_id)

        if game is None or game["finished"]:
            return None

        player_score = _hand_value(game["player_cards"])

        if player_score > 21:
            game["finished"] = True
            game["result"] = "lose"
            return _public_game(game)

        game["finished"] = True

        while _hand_value(game["dealer_cards"]) < 17:
            game["dealer_cards"].append(_draw_card(game))

        player_score = _hand_value(game["player_cards"])
        dealer_score = _hand_value(game["dealer_cards"])

        if dealer_score > 21 or player_score > dealer_score:
            result = "win"
        elif player_score < dealer_score:
            result = "lose"
        else:
            result = "draw"

        game["result"] = result

        return _public_game(game)


def finish_game(user_id: int):
    """Удаляет раунд из памяти, даже если он завершён автоматически."""
    with _games_lock:
        game = _games.get(user_id)

        if game is None:
            return False

        # Помечаем раунд завершённым перед удалением.
        game["finished"] = True
        del _games[user_id]

        return True


def remove_game(user_id: int):
    """Удаляет раунд из памяти. Выплаты здесь не производятся."""
    with _games_lock:
        return _games.pop(user_id, None) is not None


def format_cards(cards):
    """Публичная функция форматирования карт."""
    return _format_cards(cards)


def hand_value(cards):
    """Публичная функция подсчёта очков."""
    return _hand_value(cards)


def is_blackjack(cards):
    """Проверяет наличие блэкджека из двух карт."""
    return _is_blackjack(cards)