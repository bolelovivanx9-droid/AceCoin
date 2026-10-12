import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu


logger = logging.getLogger(__name__)

# Настоящий ID канала
CHANNEL_ID = -1004344387835
CHANNEL_URL = "https://t.me/QxlRu9bXe51lZjAy"

SUBSCRIPTION_CALLBACK = "subscription_check"


def subscription_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📢 Подписаться на канал",
                    url=CHANNEL_URL,
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Проверить подписку",
                    callback_data=SUBSCRIPTION_CALLBACK,
                )
            ],
        ]
    )


async def is_subscribed(bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id,
        )

        return member.status in (
            "member",
            "administrator",
            "creator",
        )

    except BadRequest as error:
        logger.error(
            "Telegram не смог проверить подписку пользователя %s. "
            "ID канала: %s. Ошибка: %s. "
            "Проверь ID канала и права бота.",
            user_id,
            CHANNEL_ID,
            error,
        )
        return False

    except Forbidden:
        logger.exception(
            "У бота нет доступа к каналу %s. "
            "Добавь бота в канал и назначь администратором.",
            CHANNEL_ID,
        )
        return False

    except TelegramError:
        logger.exception(
            "Ошибка Telegram API при проверке подписки пользователя %s.",
            user_id,
        )
        return False

    except Exception:
        logger.exception(
            "Неожиданная ошибка при проверке подписки пользователя %s.",
            user_id,
        )
        return False


async def show_subscription_prompt(message):
    await message.reply_text(
        "🔒 Для использования AceCoin Casino "
        "необходимо подписаться на наш канал.\n\n"
        "1. Нажми «📢 Подписаться на канал».\n"
        "2. Подпишись на канал.\n"
        "3. Вернись сюда и нажми «✅ Проверить подписку».",
        reply_markup=subscription_keyboard(),
    )


async def subscription_message_guard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    message_text = (message.text or "").strip()
    command = (
        message_text.split(maxsplit=1)[0].split("@")[0].lower()
        if message_text
        else ""
    )

    # Разрешаем /start, чтобы пользователь мог увидеть инструкцию.
    if command == "/start":
        return

    if await is_subscribed(context.bot, user.id):
        return

    await show_subscription_prompt(message)


async def subscription_callback_guard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query or not query.from_user:
        return

    user = query.from_user

    if query.data == SUBSCRIPTION_CALLBACK:
        if await is_subscribed(context.bot, user.id):
            await query.answer("✅ Подписка подтверждена!")

            if query.message:
                try:
                    await query.message.edit_text(
                        "✅ Подписка подтверждена!\n"
                        "Теперь тебе доступен AceCoin Casino."
                    )
                except TelegramError:
                    logger.debug(
                        "Не удалось изменить сообщение проверки подписки.",
                        exc_info=True,
                    )

                await query.message.reply_text(
                    "🎰 Добро пожаловать в AceCoin Casino!",
                    reply_markup=main_menu(),
                )
        else:
            await query.answer(
                "❌ Подписка не найдена. Подпишись на канал "
                "и проверь ещё раз.",
                show_alert=True,
            )

        return

    # Защита остальных inline-кнопок для неподписанных пользователей.
    if not await is_subscribed(context.bot, user.id):
        await query.answer(
            "🔒 Сначала подпишись на канал AceCoin Casino.",
            show_alert=True,
        )

        if query.message:
            await show_subscription_prompt(query.message)

        return