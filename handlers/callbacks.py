from telegram import Update
from telegram.ext import ContextTypes

from games.treasure import (
    get_cell,
    get_bet,
    end_game
)

from services.casino import give_win


async def treasure_click(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()


    user_id = query.from_user.id


    data = query.data.split("_")


    try:

        row = int(data[1])
        col = int(data[2])

    except:

        await query.edit_message_text(
            "❌ Ошибка клетки"
        )

        return


    number = row * 3 + col


    result = get_cell(
        user_id,
        number
    )


    bet = get_bet(user_id)


    if not bet:

        await query.edit_message_text(
            "❌ Игра не найдена"
        )

        return



    # Победа
    if result == "💎":


        win = bet * 3


        give_win(
            user_id,
            win
        )


        end_game(user_id)


        await query.edit_message_text(
            f"💎 Ты нашёл сокровище!\n\n"
            f"Выигрыш: +{win} AceCoin"
        )


        return



    # Проигрыш
    if result == "💣":


        end_game(user_id)


        await query.edit_message_text(
            f"💣 Бомба!\n\n"
            f"Ты проиграл {bet} AceCoin"
        )


        return



    # Пустая клетка
    await query.edit_message_text(
        "❌ Ничего нет...\n"
        "Попробуй другую клетку."
    )