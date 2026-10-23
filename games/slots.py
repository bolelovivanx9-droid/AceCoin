from random import choices

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

# Символы и относительные вероятности выпадения.
SYMBOLS = ["💎", "7️⃣", "🍒", "🍇", "🍋", "🍊"]
SYMBOL_WEIGHTS = [2, 4, 10, 12, 16, 16]

# Множители полной выплаты, включая исходную ставку.
TRIPLE_PAYOUTS = {
    "💎": 10,
    "7️⃣": 7,
    "🍒": 5,
    "🍇": 3,
    "🍋": 2,
    "🍊": 2,
}

PAIR_MULTIPLIER = 1.5


def generate_slots_result():
    """Генерирует три символа и определяет множитель."""

    result = choices(
        SYMBOLS,
        weights=SYMBOL_WEIGHTS,
        k=3,
    )

    if result[0] == result[1] == result[2]:
        multiplier = TRIPLE_PAYOUTS[result[0]]
        combination_name = f"Три {result[0]}"

    elif (
        result[0] == result[1]
        or result[0] == result[2]
        or result[1] == result[2]
    ):
        multiplier = PAIR_MULTIPLIER
        combination_name = "Пара одинаковых символов"

    else:
        multiplier = 0
        combination_name = "Без выигрышной комбинации"

    return result, multiplier, combination_name


async def slots_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Игровой автомат AceCoin с виртуальными ставками."""

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    add_user(user.id, user.username or "unknown")

    if len(context.args) != 1:
        await message.reply_text(
            "🎰 СЛОТЫ ACECOIN\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Использование:\n"
            "/acslots СТАВКА\n\n"
            "Пример: /acslots 100\n\n"
            "💎 Три алмаза — x10\n"
            "7️⃣ Три семёрки — x7\n"
            "🍒 Три вишни — x5\n"
            "🍇 Три винограда — x3\n"
            "🍋 или 🍊 три одинаковых — x2\n"
            "🎯 Пара одинаковых — x1.5\n\n"
            "⭐ Победа: +5 XP\n"
            "⭐ Поражение: +2 XP\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        return

    try:
        bet = int(context.args[0])
    except (ValueError, TypeError):
        await message.reply_text(
            "❌ Ставка должна быть целым числом.\n"
            "Пример: /acslots 100"
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

    balance = get_balance(user.id)

    if balance < bet:
        await message.reply_text(
            "❌ Недостаточно средств!\n\n"
            f"💰 Баланс: ${balance:,}\n"
            f"🎲 Ставка: ${bet:,}"
        )
        return

    # Списываем ставку перед началом раунда.
    if not remove_money(user.id, bet):
        await message.reply_text(
            "❌ Не удалось списать ставку. "
            "Проверь баланс и попробуй снова."
        )
        return

    # Генерируем комбинацию.
    result, multiplier, combination_name = generate_slots_result()

    # Выплата включает исходную ставку.
    payout = int(bet * multiplier)

    if payout > 0:
        change_balance(user.id, payout)

        record_game(
            user.id,
            won=True,
            winnings=payout,
            xp_reward=WIN_XP,
        )

        xp_text = f"+{WIN_XP} XP"

        outcome_text = (
            f"🎉 Выигрыш! Множитель: x{multiplier:g}\n"
            f"🏆 Выплата: ${payout:,}\n"
            f"💵 Чистый выигрыш: ${payout - bet:,}"
        )

    else:
        record_game(
            user.id,
            won=False,
            winnings=0,
            xp_reward=LOSS_XP,
        )

        xp_text = f"+{LOSS_XP} XP"
        outcome_text = "💥 В этот раз без выигрыша."

    current_balance = get_balance(user.id)

    await message.reply_text(
        "🎰 СЛОТЫ ACECOIN\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Игрок: {user.first_name}\n"
        f"🎲 Ставка: ${bet:,}\n\n"
        f"   {' │ '.join(result)}\n\n"
        f"📋 Комбинация: {combination_name}\n"
        f"{outcome_text}\n"
        f"⭐ Опыт: {xp_text}\n"
        f"👛 Баланс: ${current_balance:,}\n\n"
        "Сыграть ещё: /acslots 100\n"
        "━━━━━━━━━━━━━━━━━━"
    )