from telegram import Update
from telegram.ext import ContextTypes

from core.admin import is_admin
from core.database import change_balance


async def add_money(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not update.effective_user or not update.message:
        return

    user_id = update.effective_user.id

    if not is_admin(user_id):
        await update.message.reply_text(
            "❌ Нет доступа."
        )
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование:\n"
            "/acaddmoney ID СУММА\n\n"
            "Пример: /acaddmoney 123456789 1000"
        )
        return

    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ ID и сумма должны быть целыми числами."
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "❌ Сумма должна быть больше нуля."
        )
        return

    change_balance(target_id, amount)

    await update.message.reply_text(
        f"✅ Выдано {amount} AceCoin игроку {target_id}."
    )
