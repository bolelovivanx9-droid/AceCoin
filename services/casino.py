from core.database import get_balance, change_balance


def get_money(user_id: int):
    return get_balance(user_id)


def can_bet(user_id: int, amount: int):
    balance = get_balance(user_id)

    return balance >= amount


def make_bet(user_id: int, amount: int):
    if not can_bet(user_id, amount):
        return False

    change_balance(
        user_id,
        -amount
    )

    return True


def give_win(user_id: int, amount: int):
    change_balance(
        user_id,
        amount
    )


def add_money(user_id: int, amount: int):
    change_balance(
        user_id,
        amount
    )