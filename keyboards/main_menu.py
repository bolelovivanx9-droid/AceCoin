from telegram import ReplyKeyboardMarkup


def main_menu():
    keyboard = [
        ["🎮 Игры", "🛒 Магазин"],
        ["🎁 Ежедневный бонус", "💰 Баланс"],
        ["🏦 Банк", "👤 Профиль"],
        ["📜 История переводов", "📊 Статистика"],
        ["🏆 Топ", "🏆 Квесты"],
        ["🏅 Достижения"],
        ["📢 Канал бота"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        is_persistent=True,
    )