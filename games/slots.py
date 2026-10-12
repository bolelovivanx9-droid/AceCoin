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
JACKPOT_MULTIPLIER = 10

WIN_XP = 5
LOSS_XP = 2


async def slots_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Игровой автомат Telegram."""

    user = update.effective_user
    message = update.effective_message
    chat = update.effective_chat

    if not user or not message or not chat:
        return

    add_user(user.id, user.username or "unknown")

    if len(context.args) != 1:
        await message.reply_text(
            "🎰 СЛОТЫ ACECOIN\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Использование:\n"
            "/slots СТАВКА\n\n"
            "Пример: /slots 100\n\n"
            "💰 Джекпот выплачивает 10x от ставки.\n"
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
            "Пример: /slots 100"
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

    # Списываем ставку до начала игры.
    if not remove_money(user.id, bet):
        await message.reply_text(
            "❌ Не удалось списать ставку. "
            "Проверь баланс и попробуй снова."
        )
        return

    try:
        # Telegram самостоятельно показывает анимацию слотов.
        dice_message = await context.bot.send_dice(
            chat_id=chat.id,
            emoji="🎰",
        )
    except Exception:
        # Если анимацию отправить не удалось, возвращаем ставку.
        change_balance(user.id, bet)

        await message.reply_text(
            "❌ Не удалось запустить слоты.\n"
            f"Ставка ${bet:,} возвращена на баланс."
        )
        return

    result = dice_message.dice.value

    if result == 64:
        # Джекпот: выплата составляет 10 ставок.
        payout = bet * JACKPOT_MULTIPLIER
        change_balance(user.id, payout)

        # Записываем победу и начисляем опыт.
        record_game(
            user.id,
            won=True,
            winnings=payout,
            xp_reward=WIN_XP,
        )

        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "🎉💎 ДЖЕКПОТ! 💎🎉\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Игрок: {user.first_name}\n"
                f"🎲 Ставка: ${bet:,}\n"
                f"🏆 Выплата: ${payout:,}\n"
                f"💰 Чистый выигрыш: ${payout - bet:,}\n"
                f"⭐ Опыт: +{WIN_XP} XP\n"
                f"👛 Баланс: ${get_balance(user.id):,}\n\n"
                "🔥 Невероятная удача!\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
        )
    else:
        # Записываем поражение и начисляем небольшой опыт.
        record_game(
            user.id,
            won=False,
            winnings=0,
            xp_reward=LOSS_XP,
        )

        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "🎰 СЛОТЫ ACECOIN\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Игрок: {user.first_name}\n"
                f"🎲 Ставка: ${bet:,}\n"
                "💥 В этот раз без выигрыша.\n"
                f"⭐ Опыт: +{LOSS_XP} XP\n"
                f"💰 Баланс: ${get_balance(user.id):,}\n\n"
                "Попробуй ещё раз: /slots 100\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
        )