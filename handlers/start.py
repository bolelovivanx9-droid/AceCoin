from telegram import Update
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu
from core.database import add_user


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(
        user.id,
        user.username or "unknown"
    )

    await update.message.reply_text(
        f"🎰 Добро пожаловать в AceCoin Casino, {user.first_name}!",
        reply_markup=main_menu()
    )