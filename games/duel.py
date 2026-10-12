
import secrets
import time
from threading import RLock


DUEL_TIMEOUT = 120
STARTING_HP = 3
MAX_AIM_BONUS = 2

_duels = {}
_player_duels = {}
_duels_lock = RLock()


def _snapshot(duel):
    """Возвращает копию дуэли без раскрытия скрытых действий."""
    result = dict(duel)
    result.pop("actions", None)
    result.pop("aim_bonus", None)

    # Не отдаём внешнему коду изменяемые словари самой дуэли.
    for key in ("hp", "player_names"):
        if key in result:
            result[key] = dict(result[key])

    return result


def create_duel(
    challenger_id: int,
    opponent_id: int,
    bet: int,
    challenger_name=None,
    opponent_name=None,
):
    """Создаёт вызов на дуэль без списания денег."""
    if challenger_id == opponent_id:
        return None, "same_player"

    if bet <= 0:
        return None, "invalid_bet"

    with _duels_lock:
        if challenger_id in _player_duels:
            return None, "challenger_busy"

        if opponent_id in _player_duels:
            return None, "opponent_busy"

        duel_id = secrets.token_hex(6)

        duel = {
            "id": duel_id,
            "challenger_id": challenger_id,
            "opponent_id": opponent_id,
            "bet": bet,
            "created_at": time.time(),
            "status": "pending",
            "winner_id": None,
            "round": 1,
            "hp": {},
            "aim_bonus": {},
            "actions": {},
            "events": [],
            "player_names": {
                challenger_id: challenger_name or f"Игрок {challenger_id}",
                opponent_id: opponent_name or f"Игрок {opponent_id}",
            },
        }

        _duels[duel_id] = duel
        _player_duels[challenger_id] = duel_id
        _player_duels[opponent_id] = duel_id

        return _snapshot(duel), "success"


def get_duel(duel_id: str):
    with _duels_lock:
        duel = _duels.get(duel_id)

        if duel is None:
            return None

        return _snapshot(duel)


def get_player_duel(user_id: int):
    with _duels_lock:
        duel_id = _player_duels.get(user_id)

        if duel_id is None:
            return None

        duel = _duels.get(duel_id)

        if duel is None:
            _player_duels.pop(user_id, None)
            return None

        return _snapshot(duel)


def accept_duel(duel_id: str, user_id: int):
    """Принимает вызов. Ставки здесь не списываются."""
    with _duels_lock:
        duel = _duels.get(duel_id)

        if duel is None:
            return None, "not_found"

        if duel["status"] != "pending":
            return None, "not_pending"

        if duel["opponent_id"] != user_id:
            return None, "not_opponent"

        if time.time() - duel["created_at"] >= DUEL_TIMEOUT:
            _delete_duel_locked(duel_id)
            return None, "expired"

        duel["status"] = "accepted"
        return _snapshot(duel), "success"


def start_battle(duel_id: str):
    """Запускает перестрелку после списания ставок."""
    with _duels_lock:
        duel = _duels.get(duel_id)

        if duel is None or duel["status"] != "accepted":
            return None

        challenger_id = duel["challenger_id"]
        opponent_id = duel["opponent_id"]

        duel["status"] = "active"
        duel["round"] = 1
        duel["hp"] = {
            challenger_id: STARTING_HP,
            opponent_id: STARTING_HP,
        }
        duel["aim_bonus"] = {
            challenger_id: 0,
            opponent_id: 0,
        }
        duel["actions"] = {}
        duel["events"] = [
            "⚔️ Перестрелка началась!",
            f"❤️ У каждого игрока {STARTING_HP} HP.",
        ]

        return _snapshot(duel)


def submit_action(duel_id: str, user_id: int, action: str):
    """
    Принимает скрытое действие игрока.
    Когда оба игрока сделали ход, разрешает раунд.
    """
    if action not in ("shoot", "aim", "disrupt"):
        return None, "invalid_action", []

    with _duels_lock:
        duel = _duels.get(duel_id)

        if duel is None:
            return None, "not_found", []

        if duel["status"] != "active":
            return None, "not_active", []

        participants = (
            duel["challenger_id"],
            duel["opponent_id"],
        )

        if user_id not in participants:
            return None, "not_participant", []

        if user_id in duel["actions"]:
            return _snapshot(duel), "already_moved", []

        duel["actions"][user_id] = action

        if len(duel["actions"]) < 2:
            return _snapshot(duel), "waiting", []

        challenger_id, opponent_id = participants
        actions = dict(duel["actions"])
        old_aim = dict(duel["aim_bonus"])
        names = duel["player_names"]

        challenger_name = names[challenger_id]
        opponent_name = names[opponent_id]

        events = [f"⚔️ Раунд {duel['round']}"]
        damage = {
            challenger_id: 0,
            opponent_id: 0,
        }

        # Выстрелы рассчитываются одновременно.
        for shooter_id, target_id in (
            (challenger_id, opponent_id),
            (opponent_id, challenger_id),
        ):
            if actions[shooter_id] != "shoot":
                continue

            bonus = old_aim[shooter_id]
            chance = 0.45 + 0.20 * bonus

            if actions[target_id] == "disrupt":
                chance -= 0.20

            chance = max(0.15, min(0.90, chance))
            hit = secrets.randbelow(100) < int(chance * 100)

            shooter_name = names[shooter_id]
            target_name = names[target_id]

            if hit:
                damage[target_id] += 1
                events.append(
                    f"💥 {shooter_name} попал в {target_name}!"
                )
            else:
                events.append(
                    f"💨 {shooter_name} промахнулся!"
                )

        # Применяем урон одновременно.
        for target_id, amount in damage.items():
            duel["hp"][target_id] = max(
                0,
                duel["hp"][target_id] - amount,
            )

        # Обновляем бонусы прицеливания.
        for player_id, target_id in (
            (challenger_id, opponent_id),
            (opponent_id, challenger_id),
        ):
            chosen = actions[player_id]
            player_name = names[player_id]
            target_name = names[target_id]

            if chosen == "aim":
                if actions[target_id] == "disrupt":
                    duel["aim_bonus"][player_id] = 0
                    events.append(
                        f"💨 {target_name} сбил прицел "
                        f"игрока {player_name}!"
                    )
                else:
                    duel["aim_bonus"][player_id] = min(
                        MAX_AIM_BONUS,
                        old_aim[player_id] + 1,
                    )
                    events.append(
                        f"🎯 {player_name} прицелился!"
                    )

            elif chosen == "shoot":
                duel["aim_bonus"][player_id] = 0

            elif chosen == "disrupt":
                duel["aim_bonus"][target_id] = 0
                events.append(
                    f"💨 {player_name} попытался сбить "
                    f"прицел соперника!"
                )

        # Проверяем результат после одновременных выстрелов.
        challenger_hp = duel["hp"][challenger_id]
        opponent_hp = duel["hp"][opponent_id]

        if challenger_hp == 0 and opponent_hp == 0:
            duel["status"] = "finished"
            duel["winner_id"] = None
            events.append("🤝 Оба игрока выбыли. Ничья!")

        elif opponent_hp == 0:
            duel["status"] = "finished"
            duel["winner_id"] = challenger_id
            events.append(f"🏆 Победитель: {challenger_name}!")

        elif challenger_hp == 0:
            duel["status"] = "finished"
            duel["winner_id"] = opponent_id
            events.append(f"🏆 Победитель: {opponent_name}!")

        else:
            duel["round"] += 1

        duel["events"] = events
        duel["actions"] = {}

        return _snapshot(duel), (
            "finished"
            if duel["status"] == "finished"
            else "round_resolved"
        ), list(events)


def finish_battle(duel_id: str):
    """Удаляет завершённую перестрелку и освобождает игроков."""
    with _duels_lock:
        duel = _duels.get(duel_id)

        if duel is None or duel["status"] != "finished":
            return None

        result = _snapshot(duel)
        _delete_duel_locked(duel_id)
        return result


def cancel_duel(duel_id: str, user_id: int):
    """Отменяет ожидающий вызов его создателем."""
    with _duels_lock:
        duel = _duels.get(duel_id)

        if duel is None:
            return None, "not_found"

        if duel["status"] != "pending":
            return None, "not_pending"

        if duel["challenger_id"] != user_id:
            return None, "not_challenger"

        result = _snapshot(duel)
        _delete_duel_locked(duel_id)

        return result, "success"


def expire_duel(duel_id: str):
    """Удаляет просроченный вызов, если его не приняли."""
    with _duels_lock:
        duel = _duels.get(duel_id)

        if duel is None or duel["status"] != "pending":
            return None

        if time.time() - duel["created_at"] < DUEL_TIMEOUT:
            return None

        result = _snapshot(duel)
        _delete_duel_locked(duel_id)
        return result


def remove_duel(duel_id: str):
    """Удаляет дуэль без выплаты победителю."""
    with _duels_lock:
        if duel_id not in _duels:
            return False

        _delete_duel_locked(duel_id)
        return True


def _delete_duel_locked(duel_id: str):
    duel = _duels.pop(duel_id, None)

    if duel is None:
        return

    for player_id in (
        duel["challenger_id"],
        duel["opponent_id"],
    ):
        if _player_duels.get(player_id) == duel_id:
            _player_duels.pop(player_id, None)
