
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
from core.shop_database import get_equipped_details
from services.profile_card import generate_profile_card


logger = logging.getLogger(__name__)


async def _send_profile(message, context, user_id, username=None, first_name=None):
    """Отправляет карточку профиля зарегистрированного игрока."""
    record = get_user(user_id)

    if not record:
        await message.reply_text(
            "❌ Этот игрок ещё не зарегистрирован в AceCoin Casino.\n"
            "Пусть он запустит бота командой /start."
        )
        return

    money = get_balance(user_id)
    stats = get_user_stats(user_id)

    if not stats:
        await message.reply_text("❌ Не удалось загрузить статистику игрока.")
        return

    cosmetics = get_equipped_details(user_id) or {}
    frame = cosmetics.get("frame_id")
    equipped_title = cosmetics.get("title")
    title_text = (
        equipped_title.get("name")
        if isinstance(equipped_title, dict)
        else equipped_title
    )

    avatar_bytes = None

    try:
        photos = await context.bot.get_user_profile_photos(
            user_id=user_id,
            limit=1,
        )

        if photos.total_count > 0 and photos.photos:
            photo = photos.photos[0][-1]
            telegram_file = await context.bot.get_file(photo.file_id)
            avatar_bytes = bytes(
                await telegram_file.download_as_bytearray()
            )
    except Exception:
        logger.warning(
            "Не удалось загрузить аватар пользователя %s",
            user_id,
            exc_info=True,
        )

    stored_username = record["username"]
    username = username or stored_username
    display_name = first_name or (
        f"@{username}" if username and username != "unknown"
        else f"Игрок {user_id}"
    )

    try:
        profile_image = generate_profile_card(
            first_name=display_name,
            username=username or "",
            user_id=user_id,
            balance=money,
            avatar_bytes=avatar_bytes,
            level=stats["level"],
            rank=stats["rank"],
            rank_emoji=stats["rank_emoji"],
            xp=stats["xp"],
            xp_in_level=stats["xp_in_level"],
            xp_per_level=stats["xp_per_level"],
            frame_id=frame,
            title=title_text,
        )

        safe_name = html.escape(display_name)
        safe_rank = html.escape(stats["rank"])

        await message.reply_photo(
            photo=profile_image,
            caption=(
                "👤 <b>ПРОФИЛЬ ИГРОКА</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"🎮 Игрок: <b>{safe_name}</b>\n"
                f"💰 Баланс: <b>${money:,}</b>\n"
                f"💎 Ранг: <b>{stats['rank_emoji']} {safe_rank}</b>\n"
                f"⭐ Уровень: <b>{stats['level']}</b>\n"
                f"✨ Опыт: <b>{stats['xp']} XP</b>\n"
                "━━━━━━━━━━━━━━━━━━"
            ).replace(",", " "),
            parse_mode="HTML",
        )

    except Exception:
        logger.exception(
            "Ошибка создания карточки профиля пользователя %s",
            user_id,
        )
        await message.reply_text(
            "❌ Не удалось создать карточку профиля. "
            "Подробности ошибки есть в терминале."
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

        # Вариант 2: /profile @username
        elif context.args:
            if len(context.args) != 1:
                await message.reply_text(
                    "ℹ️ Использование команды:\n"
                    "• /profile — свой профиль\n"
                    "• /profile @username — профиль игрока\n"
                    "• Ответь на сообщение игрока командой /profile"
                )
                return

            username = context.args[0].strip().lstrip("@")

            if not username:
                await message.reply_text(
                    "❌ Укажи Telegram username, например /profile @username."
                )
                return

            record = get_user_by_username(username)

            if not record:
                await message.reply_text(
                    "❌ Игрок не найден в базе AceCoin Casino.\n"
                    "Он должен запустить бота командой /start."
                )
                return

            target_id = record["user_id"]
            target_username = record["username"]
            target_first_name = (
                f"@{target_username}"
                if target_username and target_username != "unknown"
                else f"Игрок {target_id}"
            )

        # Вариант 3: свой профиль.
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
            context,
            target_id,
            username=target_username,
            first_name=target_first_name,
        )

    except Exception:
        logger.exception("Ошибка команды /profile")
        await message.reply_text(
            "❌ Не удалось открыть профиль. Попробуй ещё раз."
        )
