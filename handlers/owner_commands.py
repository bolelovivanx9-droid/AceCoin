import os

from telegram import Update
from telegram.ext import ContextTypes

from core.database import get_user, get_user_by_username
from core.steal import (
    STEAL_SUCCESS_CHANCE,
    attempt_steal,
)


try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0"))
except (TypeError, ValueError):
    OWNER_ID = 0


def _format_time(seconds: int) -> str:
    """Преобразует секунды в читаемый остаток времени."""

    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60

    if hours > 0:
        return f"{hours} ч. {minutes} мин."

    if minutes > 0:
        return f"{minutes} мин."

    return "меньше минуты"


async def admin_help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Краткая справка по командам только для владельца."""

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if OWNER_ID <= 0 or user.id != OWNER_ID:
        return

    text = (
        "👑 ACECOIN CASINO — СПРАВКА ВЛАДЕЛЬЦА\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "📌 ОСНОВНЫЕ КОМАНДЫ\n"
        "/acstart — запустить бота и открыть профиль\n"
        "/achelp — справка по командам\n"
        "/acmenu — главное меню\n"
        "/acprofile — карточка игрока\n"
        "/acbalance — проверить баланс\n"
        "/acstats — статистика игрока\n"
        "/actop — таблица лидеров\n"
        "/acrating — рейтинг игроков\n\n"

        "🎮 ИГРЫ\n"
        "/actreasure — игра «Сокровища»\n"
        "/acslots — игровые слоты\n"
        "/acroulette — рулетка\n"
        "/acblackjack — блэкджек\n"
        "/acduel — вызвать игрока на дуэль\n"
        "/accancel — отменить ожидающий вызов\n\n"

        "💰 ЭКОНОМИКА\n"
        "/acdaily — получить ежедневный бонус\n"
        "/acbank — управление банком\n"
        "/acloan — информация о кредите\n"
        "/actake_loan — взять кредит\n"
        "/acrepay_loan — погасить кредит\n"
        "/acpay — перевести деньги игроку\n"
        "/actransfer_history — история переводов\n"
        "/acsteal — попытаться украсть у игрока\n\n"

        "🏆 ПРОГРЕСС\n"
        "/acquests — ежедневные задания\n"
        "/acachievements — достижения игрока\n\n"

        "🎟️ ПРОМОКОДЫ\n"
        "/acpromo — использовать промокод\n"
        "/accreatepromo — создать промокод\n\n"

        "🛠️ КОМАНДЫ ВЛАДЕЛЬЦА\n"
        "/acadminhelp — эта справка\n"
        "/acaddmoney — начисление виртуальных денег\n"
        "/acmute — глобально заглушить бота\n"
        "/acunmute — вернуть бота к работе\n\n"

        "ℹ️ Старые команды без префикса ac также "
        "остаются доступными, если они зарегистрированы.\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    await message.reply_text(text)


async def steal_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Позволяет раз в сутки попытаться украсть монеты у игрока."""

    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    target_id = None
    target_label = None

    # Вариант 1: ответ на сообщение игрока.
    reply = message.reply_to_message

    if reply:
        target_user = reply.from_user

        if not target_user:
            await message.reply_text(
                "❌ Не удалось определить автора сообщения."
            )
            return

        if target_user.is_bot:
            await message.reply_text(
                "❌ Нельзя красть у ботов."
            )
            return

        target_id = target_user.id

        if target_user.username:
            target_label = f"@{target_user.username}"
        else:
            target_label = target_user.full_name

    # Вариант 2: команда с username.
    else:
        if len(context.args) != 1:
            await message.reply_text(
                "🕵️ КРАЖА МОНЕТ\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Ответь командой на сообщение игрока:\n"
                "/acsteal\n\n"
                "Или укажи username:\n"
                "/acsteal @username\n\n"
                "⏳ Одна попытка раз в 24 часа.\n"
                f"🎲 Шанс успеха: {STEAL_SUCCESS_CHANCE}%\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            return

        username = context.args[0].strip().lstrip("@")

        if not username:
            await message.reply_text(
                "❌ Укажи username игрока: /acsteal @username"
            )
            return

        target = get_user_by_username(username)

        if not target:
            await message.reply_text(
                "❌ Не нашёл зарегистрированного игрока с таким "
                "username. Игрок должен сначала запустить /acstart."
            )
            return

        target_id = target["user_id"]
        target_label = f"@{target['username']}"

    if target_id == user.id:
        await message.reply_text(
            "😅 Нельзя красть у самого себя!"
        )
        return

    # Кража возможна только между зарегистрированными игроками.
    thief_account = get_user(user.id)
    target_account = get_user(target_id)

    if not thief_account:
        await message.reply_text(
            "❌ Сначала создай профиль командой /acstart."
        )
        return

    if not target_account:
        await message.reply_text(
            f"❌ Игрок {target_label} ещё не зарегистрирован "
            "в AceCoin. Пусть сначала запустит /acstart."
        )
        return

    result = attempt_steal(user.id, target_id)
    status = result["status"]

    if status == "same_user":
        await message.reply_text(
            "😅 Нельзя красть у самого себя!"
        )
        return

    if status == "thief_not_found":
        await message.reply_text(
            "❌ Сначала создай профиль командой /acstart."
        )
        return

    if status == "target_not_found":
        await message.reply_text(
            "❌ Этот игрок не найден в базе AceCoin."
        )
        return

    if status == "cooldown":
        remaining = _format_time(result["remaining"])

        await message.reply_text(
            "⏳ Ты уже пытался сегодня!\n\n"
            f"До следующей попытки: {remaining}."
        )
        return

    if status == "target_broke":
        await message.reply_text(
            f"💸 У игрока {target_label} нет денег, которые можно "
            "украсть.\n"
            "Эта попытка потрачена. Попробуй снова через 24 часа."
        )
        return

    if status == "failed":
        await message.reply_text(
            "🕵️ ПОПЫТКА КРАЖИ ПРОВАЛИЛАСЬ!\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 Цель: {target_label}\n"
            "🍀 Сегодня удача не на твоей стороне.\n"
            "💰 Деньги не изменились.\n"
            "⏳ Следующая попытка будет доступна через 24 часа.\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        return

    if status == "balance_changed":
        await message.reply_text(
            "⚠️ Баланс игрока изменился во время операции. "
            "Деньги не были переведены. Попробуй позже."
        )
        return

    if status == "success":
        amount = result["amount"]
        thief_balance = result["thief_balance"]

        await message.reply_text(
            "🕵️ КРАЖА УДАЛАСЬ!\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 Цель: {target_label}\n"
            f"💰 Украдено: ${amount:,}\n"
            f"👛 Твой баланс: ${thief_balance:,}\n"
            "🍀 Тебе повезло — попытка успешна!\n"
            "⏳ Следующая попытка будет доступна через 24 часа.\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        return

    await message.reply_text(
        "❌ Не удалось выполнить попытку. Попробуй позже."
    )