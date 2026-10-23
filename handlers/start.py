from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu
from core.database import add_user, get_balance
from handlers.subscription import (
    is_subscribed,
    show_subscription_prompt,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Регистрация игрока и приветствие AceCoin Casino."""

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    # Регистрируем игрока или обновляем его username.
    add_user(
        user.id,
        user.username or "unknown",
    )

    # Сохраняем существующую проверку подписки.
    if not await is_subscribed(context.bot, user.id):
        await show_subscription_prompt(message)
        return

    # Получаем актуальный баланс игрока.
    balance = get_balance(user.id)

    welcome_text = (
        "🎰 ══════════════════════ 🎰\n"
        "       ACECOIN CASINO\n"
        "══════════════════════════\n\n"

        f"👑 Добро пожаловать, {user.first_name}!\n\n"
        "🔥 Твоя история начинается прямо сейчас!\n"
        "Здесь тебя ждут игры, достижения и борьба "
        "за место среди лучших игроков.\n\n"

        "💰 ТВОЙ ИГРОВОЙ БАЛАНС\n"
        f"💵 ${balance:,}\n\n"

        "🎮 ИГРЫ\n"
        "💎 /actreasure 100 — Сокровища\n"
        "🎰 /acslots 100 — Слоты\n"
        "🎡 /acroulette — Рулетка\n"
        "🃏 /acblackjack 100 — Блэкджек\n\n"

        "💸 ВОЗМОЖНОСТИ\n"
        "🎁 /acdaily — ежедневный бонус\n"
        "🏦 /acbank — твой банк\n"
        "👤 /acprofile — твой профиль\n"
        "🏆 /actop — рейтинг игроков\n"
        "🏅 /acachievements — достижения\n\n"

        "📖 /achelp — все команды бота\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🍀 Испытай удачу и создай свою легенду!\n"
        "🎲 ACECOIN CASINO — ИГРА НАЧИНАЕТСЯ!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    await message.reply_text(
        welcome_text,
        reply_markup=main_menu(),
    )