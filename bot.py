
import asyncio
import logging
import traceback

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN

from core.database import init_db
from core.promocodes import init_promo_db
from core.shop_database import init_shop_db
from core.logger import setup_logger
from core.quests import init_quests_db

from handlers.start import start
from handlers.menu import (
    menu_buttons,
    treasure_command,
    balance,
    transfer_command,
    daily_bonus_callback,
    rating_command,
    stats_command,
)
from handlers.help import help_command
from handlers.profile import profile_command
from handlers.shop import shop_callback
from handlers.admin import add_money
from handlers.promo import (
    create_promo_command,
    promo_command,
)
from handlers.achievements import achievements_command
from handlers.quests import show_quests, quest_claim_callback
from handlers.subscription import (
    SUBSCRIPTION_CALLBACK,
    is_subscribed,
    show_subscription_prompt,
    subscription_callback_guard,
)

from games.slots import slots_command
from games.roulette import roulette_command
from handlers.callbacks import treasure_click
from handlers.blackjack import (
    blackjack_command,
    blackjack_click,
)
from handlers.duel import (
    duel_command,
    duel_click,
    cancel_command,
)


async def subscription_message_gate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Проверяет подписку только при использовании команд бота."""
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    message_text = (message.text or "").strip()

    # Обычные сообщения, фото, стикеры и прочее не проверяем.
    if not message_text.startswith("/"):
        return

    command = message_text.split(maxsplit=1)[0].split("@")[0].lower()

    # /start всегда доступен, чтобы пользователь мог подписаться.
    if command == "/start":
        return

    # Проверяем только команды, зарегистрированные в боте.
    protected_commands = {
        "/help",
        "/profile",
        "/balance",
        "/treasure",
        "/slots",
        "/roulette",
        "/blackjack",
        "/rating",
        "/top",
        "/quests",
        "/achievements",
        "/duel",
        "/cancel",
        "/addmoney",
        "/pay",
        "/createpromo",
        "/promo",
    }

    if command not in protected_commands:
        return

    if await is_subscribed(context.bot, user.id):
        return

    await show_subscription_prompt(message)
    raise ApplicationHandlerStop


async def subscription_callback_gate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Проверяет подписку перед обработкой inline-кнопок."""
    query = update.callback_query

    if not query or not query.from_user:
        return

    user = query.from_user

    # Кнопка проверки подписки должна работать для всех.
    if query.data == SUBSCRIPTION_CALLBACK:
        await subscription_callback_guard(update, context)
        raise ApplicationHandlerStop

    if await is_subscribed(context.bot, user.id):
        return

    await query.answer(
        "🔒 Сначала подпишись на канал AceCoin Casino.",
        show_alert=True,
    )

    if query.message:
        await show_subscription_prompt(query.message)

    raise ApplicationHandlerStop


async def debug_treasure_click(update, context):
    query = update.callback_query

    if query:
        print(
            f"[DEBUG] Получено нажатие кнопки: {query.data}",
            flush=True,
        )
        print(
            f"[DEBUG] Нажал пользователь: {query.from_user.id}",
            flush=True,
        )

    try:
        await treasure_click(update, context)
        print(
            "[DEBUG] Обработчик treasure_click завершён.",
            flush=True,
        )
    except Exception:
        print(
            "[ERROR] Ошибка внутри treasure_click:",
            flush=True,
        )
        traceback.print_exc()
        raise


async def debug_blackjack_click(update, context):
    query = update.callback_query

    if query:
        print(
            f"[DEBUG] Блэкджек: {query.data}",
            flush=True,
        )
        print(
            f"[DEBUG] Пользователь: {query.from_user.id}",
            flush=True,
        )

    try:
        await blackjack_click(update, context)
    except Exception:
        print(
            "[ERROR] Ошибка внутри blackjack_click:",
            flush=True,
        )
        traceback.print_exc()
        raise


async def error_handler(update, context):
    print(
        "\n[ERROR] Произошла ошибка в боте:",
        flush=True,
    )

    if context.error:
        traceback.print_exception(
            type(context.error),
            context.error,
            context.error.__traceback__,
        )
    else:
        print(
            "Подробности ошибки отсутствуют.",
            flush=True,
        )


async def main():
    logging.basicConfig(
        format=(
            "%(asctime)s - %(name)s - "
            "%(levelname)s - %(message)s"
        ),
        level=logging.INFO,
    )

    logger = setup_logger()

    # Инициализация баз данных без удаления существующих данных.
    init_db()
    init_promo_db()
    init_shop_db()
    init_quests_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Проверка подписки выполняется раньше остальных обработчиков.
    app.add_handler(
        MessageHandler(
            filters.ALL,
            subscription_message_gate,
        ),
        group=-1,
    )
    app.add_handler(
        CallbackQueryHandler(subscription_callback_gate),
        group=-1,
    )

    # Основные команды.
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("treasure", treasure_command))
    app.add_handler(CommandHandler("slots", slots_command))
    app.add_handler(CommandHandler("roulette", roulette_command))
    app.add_handler(CommandHandler("blackjack", blackjack_command))

    # Рейтинг: обе команды открывают один рейтинг.
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("top", rating_command))
    app.add_handler(CommandHandler("rating", rating_command))

    # Ежедневные квесты.
    app.add_handler(CommandHandler("quests", show_quests))
    app.add_handler(
        CallbackQueryHandler(
            quest_claim_callback,
            pattern=r"^quest_claim:",
        )
    )

    # Ежедневный бонус.
    app.add_handler(
        CallbackQueryHandler(
            daily_bonus_callback,
            pattern=r"^daily_bonus_claim:\d+$",
        )
    )

    # Достижения.
    app.add_handler(
        CommandHandler("achievements", achievements_command)
    )

    # Дуэли и отмена ожидающего вызова.
    app.add_handler(CommandHandler("duel", duel_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    # Экономика и промокоды.
    app.add_handler(CommandHandler("addmoney", add_money))
    app.add_handler(CommandHandler("pay", transfer_command))
    app.add_handler(
        CommandHandler("createpromo", create_promo_command)
    )
    app.add_handler(CommandHandler("promo", promo_command))

    # Кнопки магазина.
    app.add_handler(
        CallbackQueryHandler(
            shop_callback,
            pattern=r"^shop_",
        )
    )

    # Кнопки игры «Сокровища».
    app.add_handler(
        CallbackQueryHandler(
            debug_treasure_click,
            pattern=r"^treasure_",
        )
    )

    # Кнопки блэкджека.
    app.add_handler(
        CallbackQueryHandler(
            debug_blackjack_click,
            pattern=r"^blackjack_",
        )
    )

    # Кнопки дуэлей.
    app.add_handler(
        CallbackQueryHandler(
            duel_click,
            pattern=r"^duel_",
        )
    )

    # Текстовые кнопки главного меню.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_buttons,
        )
    )

    app.add_error_handler(error_handler)

    logger.info("🎰 AceCoin бот запускается")
    print(
        "[DEBUG] Бот подготовлен к запуску.",
        flush=True,
    )

    await app.initialize()
    await app.start()

    if app.updater is None:
        raise RuntimeError("Telegram updater недоступен")

    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES
    )

    print(
        "[DEBUG] Polling запущен. Ожидаю обновления Telegram...",
        flush=True,
    )
    logger.info("🎰 AceCoin бот запущен")

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        if app.updater.running:
            await app.updater.stop()

        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        print(
            "[FATAL] Бот завершился с ошибкой:",
            flush=True,
        )
        traceback.print_exc()
