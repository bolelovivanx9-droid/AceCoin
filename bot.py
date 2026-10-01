from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config import BOT_TOKEN

from core.database import init_db
from core.logger import setup_logger

from handlers.start import start
from handlers.menu import menu_buttons
from handlers.admin import add_money
from handlers.callbacks import treasure_click


def main():

    logger = setup_logger()

    init_db()

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
    CommandHandler("addmoney", add_money)
    )

    app.add_handler(
        CallbackQueryHandler(treasure_click)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu_buttons
        )
    )

    logger.info("🎰 AceCoin бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()