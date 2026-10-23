import asyncio
import json
import logging
import os
import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    TypeHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN

from core.database import init_db
from core.promocodes import init_promo_db
from core.shop_database import init_shop_db
from core.logger import setup_logger
from core.quests import init_quests_db
from core.steal import init_steal_db

from handlers.start import start
from handlers.menu import (
    menu_buttons,
    menu_command,
    daily_command,
    treasure_command,
    balance,
    transfer_command,
    daily_bonus_callback,
    rating_command,
    stats_command,
)
from handlers.economy_commands import (
    bank_command,
    loan_command,
    take_loan_command,
    repay_loan_command,
    transfer_history_command,
    economy_callback,
    process_economy_text,
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
from handlers.owner_commands import (
    admin_help_command,
    steal_command,
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


# ============================================================
# ГЛОБАЛЬНЫЙ МУТ БОТА
# ============================================================

OWNER_ID_RAW = os.getenv("OWNER_ID", "").strip()

try:
    OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW else 0
except ValueError:
    OWNER_ID = 0


MUTE_STATE_FILE = (
    Path(__file__).resolve().parent / "bot_mute_state.json"
)


def load_mute_state() -> bool:
    """Загружает состояние мута при запуске."""

    try:
        with MUTE_STATE_FILE.open("r", encoding="utf-8") as file:
            state = json.load(file)

        return bool(state.get("muted", False))

    except FileNotFoundError:
        return False

    except (OSError, json.JSONDecodeError, AttributeError):
        logging.getLogger(__name__).exception(
            "Не удалось прочитать состояние мута."
        )
        return False


def save_mute_state(muted: bool) -> bool:
    """Сохраняет состояние мута между перезапусками."""

    temp_file = MUTE_STATE_FILE.with_suffix(".tmp")

    try:
        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(
                {"muted": muted},
                file,
                ensure_ascii=False,
            )

        temp_file.replace(MUTE_STATE_FILE)
        return True

    except OSError:
        logging.getLogger(__name__).exception(
            "Не удалось сохранить состояние мута."
        )
        return False


BOT_MUTED = load_mute_state()

MUTE_COMMANDS = {
    "acmute",
    "mute",
    "mutebot",
}

UNMUTE_COMMANDS = {
    "acunmute",
    "unmute",
    "unmutebot",
}


def get_command_name(update: Update):
    """Возвращает имя команды без / и без @username бота."""

    message = update.effective_message

    if not message or not message.text:
        return None

    text = message.text.strip()

    if not text.startswith("/"):
        return None

    command = text.split(maxsplit=1)[0]
    command = command.split("@", maxsplit=1)[0]

    return command.lstrip("/").lower()


async def global_mute_gate(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Блокирует все обновления, пока бот находится в муте."""

    global BOT_MUTED

    command = get_command_name(update)
    user = update.effective_user

    # Эти команды перехватываются даже в режиме мута.
    if command in MUTE_COMMANDS or command in UNMUTE_COMMANDS:

        if user and OWNER_ID > 0 and user.id == OWNER_ID:

            if command in MUTE_COMMANDS:
                if not BOT_MUTED:
                    BOT_MUTED = True
                    save_mute_state(True)

                    logging.getLogger(__name__).warning(
                        "Владелец включил глобальный мут бота."
                    )

            elif command in UNMUTE_COMMANDS:
                if BOT_MUTED:
                    BOT_MUTED = False
                    save_mute_state(False)

                    logging.getLogger(__name__).warning(
                        "Владелец отключил глобальный мут бота."
                    )

        # Команды мута не передаются обычным обработчикам.
        raise ApplicationHandlerStop

    if BOT_MUTED:
        # Никаких ответов на команды, сообщения или кнопки.
        raise ApplicationHandlerStop


# ============================================================
# ПРОВЕРКА ПОДПИСКИ
# ============================================================

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

    # Обычные сообщения не проверяем.
    if not message_text.startswith("/"):
        return

    command = (
        message_text.split(maxsplit=1)[0]
        .split("@")[0]
        .lower()
    )

    # /start всегда доступен, если бот не заглушён.
    if command in {"/start", "/acstart"}:
        return

    protected_commands = {
        "/help", "/achelp",
        "/menu", "/acmenu",
        "/daily", "/acdaily",
        "/profile", "/acprofile",
        "/balance", "/acbalance",
        "/treasure", "/actreasure",
        "/slots", "/acslots",
        "/roulette", "/acroulette",
        "/blackjack", "/acblackjack",
        "/rating", "/acrating",
        "/top", "/actop",
        "/stats", "/acstats",
        "/quests", "/acquests",
        "/achievements", "/acachievements",
        "/duel", "/acduel",
        "/cancel", "/accancel",
        "/addmoney", "/acaddmoney",
        "/pay", "/acpay",
        "/createpromo", "/accreatepromo",
        "/promo", "/acpromo",
        "/bank", "/acbank",
        "/loan", "/acloan",
        "/take_loan", "/actake_loan",
        "/repay_loan", "/acrepay_loan",
        "/transfer_history", "/actransfer_history",
        "/steal", "/acsteal",
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

    # Кнопка проверки подписки доступна всем.
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


# ============================================================
# ОТЛАДКА ИГР
# ============================================================

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


# ============================================================
# ОБРАБОТКА ТЕКСТА И МЕНЮ
# ============================================================

async def economy_text_or_menu(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Если пользователь вводит сумму для банка или кредита,
    передаёт сообщение обработчику экономики.
    Иначе передаёт его обычному обработчику меню.
    """

    if context.user_data.get("economy_action"):
        await process_economy_text(update, context)
        return

    await menu_buttons(update, context)


# ============================================================
# ОБРАБОТКА ОШИБОК
# ============================================================

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


# ============================================================
# ЗАПУСК БОТА
# ============================================================

async def main():
    logging.basicConfig(
        format=(
            "%(asctime)s - %(name)s - "
            "%(levelname)s - %(message)s"
        ),
        level=logging.INFO,
    )

    logger = setup_logger()

    if OWNER_ID <= 0:
        logger.warning(
            "OWNER_ID не задан или некорректен. "
            "Команды владельца не смогут проверить доступ."
        )

    if BOT_MUTED:
        logger.warning(
            "Бот запускается в режиме глобального молчания. "
            "Владелец может включить его командой /acunmute."
        )

    # Инициализация баз данных без удаления существующих данных.
    init_db()
    init_promo_db()
    init_shop_db()
    init_quests_db()
    init_steal_db()

    app = Application.builder().token(BOT_TOKEN).build()

    # Глобальный мут проверяется первым для любых обновлений.
    app.add_handler(
        TypeHandler(Update, global_mute_gate),
        group=-2,
    )

    # Проверка подписки выполняется после глобального мута.
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

    # Основные команды: старые и новые варианты с префиксом ac.
    app.add_handler(CommandHandler(["start", "acstart"], start))
    app.add_handler(CommandHandler(["help", "achelp"], help_command))
    app.add_handler(CommandHandler(["menu", "acmenu"], menu_command))
    app.add_handler(CommandHandler(["daily", "acdaily"], daily_command))
    app.add_handler(CommandHandler(["profile", "acprofile"], profile_command))
    app.add_handler(CommandHandler(["balance", "acbalance"], balance))
    app.add_handler(CommandHandler(["treasure", "actreasure"], treasure_command))
    app.add_handler(CommandHandler(["slots", "acslots"], slots_command))
    app.add_handler(CommandHandler(["roulette", "acroulette"], roulette_command))
    app.add_handler(CommandHandler(["blackjack", "acblackjack"], blackjack_command))

    # Банк, кредиты и история переводов.
    app.add_handler(CommandHandler(["bank", "acbank"], bank_command))
    app.add_handler(CommandHandler(["loan", "acloan"], loan_command))
    app.add_handler(CommandHandler(["take_loan", "actake_loan"], take_loan_command))
    app.add_handler(CommandHandler(["repay_loan", "acrepay_loan"], repay_loan_command))
    app.add_handler(
        CommandHandler(
            ["transfer_history", "actransfer_history"],
            transfer_history_command,
        )
    )

    # Рейтинг и статистика.
    app.add_handler(CommandHandler(["stats", "acstats"], stats_command))
    app.add_handler(CommandHandler(["top", "actop"], rating_command))
    app.add_handler(CommandHandler(["rating", "acrating"], rating_command))

    # Ежедневные квесты.
    app.add_handler(CommandHandler(["quests", "acquests"], show_quests))
    app.add_handler(
        CallbackQueryHandler(
            quest_claim_callback,
            pattern=r"^quest_claim:",
        )
    )

    # Ежедневный бонус через inline-кнопку.
    app.add_handler(
        CallbackQueryHandler(
            daily_bonus_callback,
            pattern=r"^daily_bonus_claim:\d+$",
        )
    )

    # Достижения.
    app.add_handler(
        CommandHandler(
            ["achievements", "acachievements"],
            achievements_command,
        )
    )

    # Дуэли и отмена ожидающего вызова.
    app.add_handler(CommandHandler(["duel", "acduel"], duel_command))
    app.add_handler(CommandHandler(["cancel", "accancel"], cancel_command))

    # Экономика и промокоды.
    app.add_handler(CommandHandler(["addmoney", "acaddmoney"], add_money))
    app.add_handler(CommandHandler(["pay", "acpay"], transfer_command))
    app.add_handler(
        CommandHandler(
            ["createpromo", "accreatepromo"],
            create_promo_command,
        )
    )
    app.add_handler(CommandHandler(["promo", "acpromo"], promo_command))

    # Справка владельца и попытка кражи.
    app.add_handler(
        CommandHandler(
            ["adminhelp", "acadminhelp"],
            admin_help_command,
        )
    )
    app.add_handler(
        CommandHandler(
            ["steal", "acsteal"],
            steal_command,
        )
    )

    # Кнопки экономики: банк, кредиты, история и отмена.
    app.add_handler(
        CallbackQueryHandler(
            economy_callback,
            pattern=r"^econ:",
        )
    )

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

    # Единый обработчик обычного текста:
    # ввод суммы для экономики или кнопки главного меню.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            economy_text_or_menu,
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