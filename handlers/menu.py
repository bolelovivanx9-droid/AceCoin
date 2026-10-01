from telegram import Update
from telegram.ext import ContextTypes

from core.database import get_balance


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    money = get_balance(user_id)

    await update.message.reply_text(
        f"💰 Ваш баланс: {money} AceCoin"
    )


async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "💰 Баланс":
        await balance(update, context)

    elif text == "🎰 Игры":
        await update.message.reply_text(
            "🎰 Игры скоро будут доступны"
        )

    elif text == "👤 Профиль":
        await update.message.reply_text(
            "👤 Профиль игрока"
        )

    elif text == "🎁 Бонус":
        await update.message.reply_text(
            "🎁 Бонус скоро будет доступен"
        )

    elif text == "📢 Проверка подписки":
        await update.message.reply_text(
            "📢 Проверка подписки"
        )