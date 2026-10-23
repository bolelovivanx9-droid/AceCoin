
import html
import logging

from telegram import Update
from telegram.ext import ContextTypes

from core.database import (
    add_user,
    get_balance,
    get_user,
    get_user_by_username,
    get_user_stats,
)


logger = logging.getLogger(__name__)


async def _send_profile(
    message,
    user_id,
    username=None,
    first_name=None,
):
    """Отправляет текстовый профиль зарегистрированного игрока."""

    record = get_user(user_id)

    if not record:
        await message.reply_text(
            "❌ Этот игрок ещё не зарегистрирован в AceCoin Casino.\n"
            "Пусть он запустит бота командой /acstart."
        )
        return

    money = get_balance(user_id)
    stats = get_user_stats(user_id)

    if not stats:
        await message.reply_text(
            "❌ Не удалось загрузить статистику игрока."
        )
        return

    stored_username = record["username"]
    username = username or stored_username

    display_name = first_name or (
        f"@{username}"
        if username and username != "unknown"
        else f"Игрок {user_id}"
    )

    safe_name = html.escape(str(display_name))
    safe_rank = html.escape(str(stats["rank"]))
    safe_username = html.escape(
        f"@{username}"
        if username and username != "unknown"
        else "Не указан"
    )

    xp = stats["xp"]
    level = stats["level"]
    rank_emoji = stats["rank_emoji"]

    wins = stats.get("wins", 0)
    losses = stats.get("losses", 0)
    games_played = stats.get("games_played", 0)
    total_winnings = stats.get("total_winnings", 0)

    xp_in_level = stats.get("xp_in_level")
    xp_per_level = stats.get("xp_per_level")

    profile_text = (
        "👤 <b>ПРОФИЛЬ ИГРОКА</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🎮 Имя: <b>{safe_name}</b>\n"
        f"🔖 Username: <b>{safe_username}</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n\n"
        "💰 <b>ЭКОНОМИКА</b>\n"
        f"💵 Баланс: <b>${money:,}</b>\n\n"
        "⭐ <b>ПРОГРЕСС</b>\n"
        f"💎 Ранг: <b>{rank_emoji} {safe_rank}</b>\n"
        f"📈 Уровень: <b>{level}</b>\n"
        f"✨ Опыт: <b>{xp} XP</b>\n"
    ).replace(",", " ")

    if xp_in_level is not None and xp_per_level is not None:
        profile_text += (
            f"📊 Прогресс уровня: "
            f"<b>{xp_in_level}/{xp_per_level} XP</b>\n"
        )

    profile_text += (
        "\n🏆 <b>СТАТИСТИКА</b>\n"
        f"✅ Победы: <b>{wins}</b>\n"
        f"❌ Поражения: <b>{losses}</b>\n"
        f"🎮 Игр сыграно: <b>{games_played}</b>\n"
        f"💰 Общий выигрыш: <b>${total_winnings:,}</b>\n"
        "━━━━━━━━━━━━━━━━━━"
    ).replace(",", " ")

    await message.reply_text(
        profile_text,
        parse_mode="HTML",
    )


async def profile_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    command_user = update.effective_user

    if message is None or command_user is None:
        return

    try:
        target_id = None
        target_username = None
        target_first_name = None

        # Вариант 1: команда ответом на сообщение игрока.
        if message.reply_to_message:
            target = message.reply_to_message.from_user

            if target is None or target.is_bot:
                await message.reply_text(
                    "❌ Не удалось определить профиль этого игрока."
                )
                return

            target_id = target.id
            target_username = target.username
            target_first_name = target.first_name

        # Вариант 2: /acprofile @username
        elif context.args:
            if len(context.args) != 1:
                await message.reply_text(
                    "ℹ️ Использование команды:\n"
                    "• /acprofile — свой профиль\n"
                    "• /acprofile @username — профиль игрока\n"
                    "• Ответь на сообщение игрока командой /acprofile"
                )
                return

            username = context.args[0].strip().lstrip("@")

            if not username:
                await message.reply_text(
                    "❌ Укажи Telegram username, например "
                    "/acprofile @username."
                )
                return

            record = get_user_by_username(username)

            if not record:
                await message.reply_text(
                    "❌ Игрок не найден в базе AceCoin Casino.\n"
                    "Он должен запустить бота командой /acstart."
                )
                return

            target_id = record["user_id"]
            target_username = record["username"]
            target_first_name = (
                f"@{target_username}"
                if target_username
                and target_username != "unknown"
                else f"Игрок {target_id}"
            )

        # Вариант 3: собственный профиль.
        else:
            target_id = command_user.id
            target_username = command_user.username
            target_first_name = command_user.first_name

            add_user(
                command_user.id,
                command_user.username or "unknown",
            )

        await _send_profile(
            message,
            target_id,
            username=target_username,
            first_name=target_first_name,
        )

    except Exception:
        logger.exception("Ошибка команды /acprofile")
        await message.reply_text(
            "❌ Не удалось открыть профиль. Попробуй ещё раз."
        )
