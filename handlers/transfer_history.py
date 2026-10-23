
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from core.database import add_user, get_transfer_history


def format_transfer_date(value):
    """Преобразует дату перевода в читаемый формат."""
    if value is None:
        return "Дата не указана"

    try:
        if isinstance(value, (int, float)):
            date = datetime.fromtimestamp(value)
        else:
            date_text = str(value).strip()

            try:
                date = datetime.fromisoformat(date_text)
            except ValueError:
                date = datetime.fromtimestamp(float(date_text))

        return date.strftime("%d.%m.%Y %H:%M")

    except (ValueError, TypeError, OSError, OverflowError):
        return str(value)


async def transfer_history_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Показывает последние 10 переводов игрока."""
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    add_user(user.id, user.username or "unknown")

    history = get_transfer_history(user.id, limit=10)

    if not history:
        await message.reply_text(
            "📜 <b>ИСТОРИЯ ПЕРЕВОДОВ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "У тебя пока нет переводов.\n\n"
            "💸 Чтобы отправить монеты игроку, используй:\n"
            "<code>/acpay @username 500</code>\n\n"
            "Или ответь на сообщение игрока командой:\n"
            "<code>/acpay 500</code>\n\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
        )
        return

    lines = []

    for transfer in history:
        sender_id = transfer["sender_id"]
        recipient_id = transfer["recipient_id"]
        amount = transfer["amount"]
        created_at = transfer["created_at"]

        if sender_id == user.id:
            direction = "📤 ОТПРАВЛЕНО"
            other_user_id = recipient_id
            amount_text = f"−{amount:,} AC"
        else:
            direction = "📥 ПОЛУЧЕНО"
            other_user_id = sender_id
            amount_text = f"+{amount:,} AC"

        date_text = format_transfer_date(created_at)

        lines.append(
            f"{direction}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🪙 Сумма: <b>{amount_text}</b>\n"
            f"👤 ID игрока: <code>{other_user_id}</code>\n"
            f"🕒 Дата: <b>{date_text}</b>"
        )

    history_text = "\n\n".join(lines)

    await message.reply_text(
        "📜 <b>ИСТОРИЯ ПЕРЕВОДОВ ACECOIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{history_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Показаны последние 10 операций.",
        parse_mode="HTML",
    )
