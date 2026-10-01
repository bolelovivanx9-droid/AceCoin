from telegram import Update
from telegram.ext import ContextTypes

from keyboards.treasure import treasure_field
from games.treasure import create_game
from core.database import get_balance, remove_money


waiting_bets = {}


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    money = get_balance(user_id)

    await update.message.reply_text(
        f"💰 Ваш баланс: {money} AceCoin"
    )


async def menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text


    # Баланс
    if text == "💰 Баланс":

        await balance(update, context)

        return


    # Если игрок вводит ставку
    if user_id in waiting_bets:

        if text.isdigit():

            bet = int(text)

            money = get_balance(user_id)


            if money < bet:

                await update.message.reply_text(
                    "❌ Недостаточно AceCoin"
                )

                return


            remove_money(
                user_id,
                bet
            )


            waiting_bets.pop(user_id)


            create_game(
                user_id,
                bet
            )


            await update.message.reply_text(
                f"💎 Ставка принята: {bet} AceCoin\n\n"
                "Выбери клетку:",
                reply_markup=treasure_field()
            )

            return


    # Игры
    if text == "🎰 Игры":

        await update.message.reply_text(
            "🎰 Доступные игры:\n\n"
            "💎 Сокровища\n"
            "🎰 Слоты\n"
            "🎲 Кубики"
        )

        return


    # Сокровища
    if text == "💎 Сокровища":

        waiting_bets[user_id] = True

        await update.message.reply_text(
            "💎 Сокровища\n\n"
            "Введите ставку:"
        )

        return


    # Профиль
    if text == "👤 Профиль":

        await update.message.reply_text(
            "👤 Профиль игрока"
        )

        return


    # Бонус
    if text == "🎁 Бонус":

        await update.message.reply_text(
            "🎁 Бонус скоро будет доступен"
        )

        return


    # Проверка подписки
    if text == "📢 Проверка подписки":

        await update.message.reply_text(
            "📢 Проверка подписки"
        )

        return