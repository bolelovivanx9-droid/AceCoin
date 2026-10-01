from telegram import Update
from telegram.ext import ContextTypes

from games.treasure import get_cell, end_game


async def treasure_click(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    data = query.data.split("_")

    number = int(data[1]) * 3 + int(data[2])


    result = get_cell(
        user_id,
        number
    )


    if result == "💎":

        await query.edit_message_text(
            "💎 Ты нашёл сокровище!\n"
            "Победа!"
        )

        end_game(user_id)


    elif result == "💣":

        await query.edit_message_text(
            "💣 Бомба!\n"
            "Ты проиграл."
        )

        end_game(user_id)