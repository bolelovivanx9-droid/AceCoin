
import random

from telegram import Update
from telegram.ext import ContextTypes

from core.database import (
    add_user,
    get_balance,
    remove_money,
    change_balance,
    record_game,
)


MAX_BET = 100_000_000

WIN_XP = 5
LOSS_XP = 2

RED_NUMBERS = {
    1, 3, 5, 7, 9, 12, 14, 16, 18,
    19, 21, 23, 25, 27, 30, 32, 34, 36,
}

BLACK_NUMBERS = {
    2, 4, 6, 8, 10, 11, 13, 15, 17,
    20, 22, 24, 26, 28, 29, 31, 33, 35,
}


async def roulette_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat

    if not user or not message or not chat:
        return

    add_user(user.id, user.username or "unknown")

    if len(context.args) != 2:
        await message.reply_text(
            "🎡 РУЛЕТКА ACECOIN\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Использование:\n"
            "/acroulette red 100 — красное\n"
            "/acroulette black 100 — чёрное\n"
            "/acroulette green 100 — зеро\n"
            "/acroulette 17 100 — число\n\n"
            "🔴 Красное: выплата 2x\n"
            "⚫ Чёрное: выплата 2x\n"
            "🟢 Зеро: выплата 36x\n"
            "🔢 Число: выплата 36x\n\n"
            f"⭐ Победа: +{WIN_XP} XP\n"
            f"⭐ Поражение: +{LOSS_XP} XP\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        return

    bet_type = context.args[0].lower()

    try:
        bet = int(context.args[1])
    except (ValueError, TypeError):
        await message.reply_text(
            "❌ Ставка должна быть целым числом.\n"
            "Пример: /acroulette red 100"
        )
        return

    if bet <= 0:
        await message.reply_text(
            "❌ Ставка должна быть больше нуля."
        )
        return

    if bet > MAX_BET:
        await message.reply_text(
            f"❌ Максимальная ставка — ${MAX_BET:,}."
        )
        return

    if bet_type in ("red", "black", "green"):
        choice = bet_type
    else:
        try:
            number = int(bet_type)
        except ValueError:
            await message.reply_text(
                "❌ Выбери red, black, green "
                "или число от 0 до 36."
            )
            return

        if not 0 <= number <= 36:
            await message.reply_text(
                "❌ Число должно быть от 0 до 36."
            )
            return

        choice = number

    balance = get_balance(user.id)

    if balance < bet:
        await message.reply_text(
            "❌ Недостаточно средств!\n\n"
            f"💰 Баланс: ${balance:,}\n"
            f"🎲 Ставка: ${bet:,}"
        )
        return

    if not remove_money(user.id, bet):
        await message.reply_text(
            "❌ Не удалось списать ставку. "
            "Попробуй ещё раз."
        )
        return

    # Европейская рулетка: числа от 0 до 36.
    result = random.SystemRandom().randint(0, 36)

    if result == 0:
        result_color = "green"
        color_text = "🟢 ЗЕЛЁНОЕ"
    elif result in RED_NUMBERS:
        result_color = "red"
        color_text = "🔴 КРАСНОЕ"
    else:
        result_color = "black"
        color_text = "⚫ ЧЁРНОЕ"

    won = (
        choice == result
        or (
            isinstance(choice, str)
            and choice in ("red", "black", "green")
            and choice == result_color
        )
    )

    if won:
        # Выплата включает возвращённую ставку.
        if isinstance(choice, int):
            payout = bet * 36
        elif choice == "green":
            payout = bet * 36
        else:
            payout = bet * 2

        change_balance(user.id, payout)
        net_result = payout - bet
        xp_reward = WIN_XP

        record_game(
            user.id,
            won=True,
            winnings=payout,
            xp_reward=xp_reward,
        )

        result_text = (
            "🎉 ПОБЕДА!\n"
            f"🏆 Выплата: ${payout:,}\n"
            f"📈 Чистый выигрыш: +${net_result:,}\n"
            f"⭐ Получено опыта: +{xp_reward} XP"
        )
    else:
        xp_reward = LOSS_XP

        record_game(
            user.id,
            won=False,
            winnings=0,
            xp_reward=xp_reward,
        )

        result_text = (
            "💥 Не повезло!\n"
            f"📉 Потеряно: ${bet:,}\n"
            f"⭐ Получено опыта: +{xp_reward} XP"
        )

    if isinstance(choice, int):
        choice_text = f"число {choice}"
    else:
        choice_text = {
            "red": "🔴 красное",
            "black": "⚫ чёрное",
            "green": "🟢 зеро",
        }[choice]

    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            "🎡 РУЛЕТКА ACECOIN\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Игрок: {user.first_name}\n"
            f"🎯 Твоя ставка: {choice_text}\n"
            f"💵 Размер ставки: ${bet:,}\n\n"
            f"🎲 Выпало: {result}\n"
            f"🎨 Цвет: {color_text}\n\n"
            f"{result_text}\n\n"
            f"💰 Баланс: ${get_balance(user.id):,}\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
    )
