
from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu
from core.database import add_user
from handlers.subscription import (
    is_subscribed,
    show_subscription_prompt,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    add_user(
        user.id,
        user.username or "unknown",
    )

    if not await is_subscribed(context.bot, user.id):
        await show_subscription_prompt(message)
        return

    await message.reply_text(
        f"🎰 Добро пожаловать в AceCoin Casino, {user.first_name}!",
        reply_markup=main_menu(),
    )
