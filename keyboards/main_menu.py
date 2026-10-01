from telegram import ReplyKeyboardMarkup


def main_menu():
    keyboard = [
        ["🎰 Игры", "💰 Баланс"],
        ["👤 Профиль", "🎁 Бонус"],
        ["📢 Проверка подписки"]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True
    )