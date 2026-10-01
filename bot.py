import asyncio

from telegram.ext import Application
from config import BOT_TOKEN


async def main():

    app = (
        Application
        .builder()
        .token(BOT_TOKEN)
        .build()
    )

    print("🎰 AceCoin Casino запущен")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())