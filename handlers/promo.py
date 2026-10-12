from telegram import Update
from telegram.ext import ContextTypes

from core.admin import is_admin
from core.promocodes import create_promo, redeem_promo


async def create_promo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Создание промокода администратором."""

    if not update.effective_user or not update.message:
        return

    admin_id = update.effective_user.id

    if not is_admin(admin_id):
        await update.message.reply_text("❌ Нет доступа.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Использование:\n"
            "/createpromo НАЗВАНИЕ СУММА\n\n"
            "Пример:\n"
            "/createpromo GOLD100 500"
        )
        return

    code = context.args[0].strip().upper()

    try:
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            "❌ Сумма должна быть целым числом."
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "❌ Сумма должна быть больше нуля."
        )
        return

    success, status = create_promo(code, amount, admin_id)

    if success:
        await update.message.reply_text(
            "✅ Промокод успешно создан!\n\n"
            f"🎟 Код: {code}\n"
            f"💰 Награда: ${amount}\n"
            "♾️ Активации: без ограничений\n"
            "👤 Каждый игрок может использовать код один раз."
        )
    elif status == "already_exists":
        await update.message.reply_text(
            "❌ Такой промокод уже существует. "
            "Придумай другое название."
        )
    elif status == "invalid_code":
        await update.message.reply_text(
            "❌ Название должно содержать от 3 до 32 символов: "
            "латинские буквы, цифры, дефис или подчёркивание."
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось создать промокод. "
            "Проверь сумму и попробуй ещё раз."
        )


async def promo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Активация промокода игроком."""

    if not update.effective_user or not update.message:
        return

    if len(context.args) != 1:
        await update.message.reply_text(
            "Использование:\n"
            "/promo НАЗВАНИЕ\n\n"
            "Пример:\n"
            "/promo GOLD100"
        )
        return

    code = context.args[0].strip().upper()

    try:
        success, status, amount = redeem_promo(
            update.effective_user.id,
            code,
        )
    except Exception:
        await update.message.reply_text(
            "❌ Не удалось активировать промокод. "
            "Попробуй позже."
        )
        raise

    if success:
        await update.message.reply_text(
            "🎉 Промокод активирован!\n\n"
            f"🎟 Код: {code}\n"
            f"💰 Начислено: ${amount}\n"
            "✅ Награда зачислена на твой баланс."
        )
    elif status == "not_found":
        await update.message.reply_text(
            "❌ Такой промокод не найден."
        )
    elif status == "already_used":
        await update.message.reply_text(
            "❌ Ты уже активировал этот промокод."
        )
    elif status == "user_not_found":
        await update.message.reply_text(
            "Сначала зарегистрируйся командой /start."
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось активировать промокод."
        )