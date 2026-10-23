import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from core.database import (
    add_user,
    get_balance,
    get_bank_balance,
    deposit_money,
    withdraw_money,
    get_transfer_history,
)
from core.loans import (
    MAX_LOAN_AMOUNT,
    get_active_loan,
    get_loan_history,
    issue_loan,
    repay_loan,
)

logger = logging.getLogger(__name__)


# ============================================================
# КЛАВИАТУРЫ — ВСЕ КНОПКИ НАХОДЯТСЯ ПОД СООБЩЕНИЕМ БОТА
# ============================================================

def bank_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📥 Внести деньги",
                callback_data="econ:deposit",
            ),
            InlineKeyboardButton(
                "📤 Снять деньги",
                callback_data="econ:withdraw",
            ),
        ],
        [
            InlineKeyboardButton(
                "💳 Кредиты",
                callback_data="econ:loans",
            ),
            InlineKeyboardButton(
                "📜 История переводов",
                callback_data="econ:transfer_history",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 Обновить",
                callback_data="econ:bank",
            ),
        ],
    ])


def loan_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💸 Взять кредит",
                callback_data="econ:take_loan",
            ),
            InlineKeyboardButton(
                "💰 Погасить долг",
                callback_data="econ:repay_loan",
            ),
        ],
        [
            InlineKeyboardButton(
                "📜 История кредитов",
                callback_data="econ:loan_history",
            ),
        ],
        [
            InlineKeyboardButton(
                "🏦 Вернуться в банк",
                callback_data="econ:bank",
            ),
        ],
    ])


def cancel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ Отменить",
                callback_data="econ:cancel",
            ),
        ],
    ])


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _format_money(amount):
    return f"${int(amount):,}".replace(",", " ")


def _get_user(update):
    if update.effective_user is None:
        return None

    return update.effective_user


async def _show_bank(message, user_id):
    wallet = get_balance(user_id)
    bank = get_bank_balance(user_id)

    await message.reply_text(
        "🏦 <b>ТВОЙ БАНК</b>\n\n"
        f"👛 Кошелёк: <b>{_format_money(wallet)}</b>\n"
        f"🏦 На счету: <b>{_format_money(bank)}</b>\n\n"
        "Выбери действие:",
        reply_markup=bank_keyboard(),
        parse_mode="HTML",
    )


async def _show_loans(message, user_id):
    loan = get_active_loan(user_id)

    if loan:
        debt = int(loan["remaining_amount"])
        loan_info = (
            "📌 <b>ТВОЙ КРЕДИТ</b>\n\n"
            f"💳 Сумма кредита: "
            f"<b>{_format_money(loan['amount'])}</b>\n"
            f"💰 Осталось погасить: <b>{_format_money(debt)}</b>\n"
            f"✅ Уже погашено: "
            f"<b>{_format_money(loan['repaid_amount'])}</b>\n\n"
        )
    else:
        loan_info = (
            "📌 <b>ТВОИ КРЕДИТЫ</b>\n\n"
            "У тебя нет активного кредита.\n\n"
        )

    await message.reply_text(
        loan_info
        + f"Максимальный кредит: <b>{_format_money(MAX_LOAN_AMOUNT)}</b>\n\n"
        "Выбери действие:",
        reply_markup=loan_keyboard(),
        parse_mode="HTML",
    )


# ============================================================
# КОМАНДЫ
# ============================================================

async def bank_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = _get_user(update)

    if user is None or update.effective_message is None:
        return

    add_user(user.id, user.username or "")
    await _show_bank(update.effective_message, user.id)


async def loan_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = _get_user(update)

    if user is None or update.effective_message is None:
        return

    add_user(user.id, user.username or "")
    await _show_loans(update.effective_message, user.id)


async def take_loan_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.effective_message.reply_text(
            "Использование: /actake_loan 5000"
        )
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text(
            "❌ Укажи сумму целым числом."
        )
        return

    await _process_amount(
        update.effective_message,
        update.effective_user.id,
        "take_loan",
        amount,
    )


async def repay_loan_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.args:
        await update.effective_message.reply_text(
            "Использование: /acrepay_loan 1000"
        )
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text(
            "❌ Укажи сумму целым числом."
        )
        return

    await _process_amount(
        update.effective_message,
        update.effective_user.id,
        "repay_loan",
        amount,
    )


async def transfer_history_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = _get_user(update)

    if user is None or update.effective_message is None:
        return

    add_user(user.id, user.username or "")

    history = get_transfer_history(user.id, limit=10)

    if not history:
        await update.effective_message.reply_text(
            "📜 <b>История переводов</b>\n\n"
            "Переводов пока нет.",
            parse_mode="HTML",
            reply_markup=bank_keyboard(),
        )
        return

    lines = ["📜 <b>ПОСЛЕДНИЕ ПЕРЕВОДЫ</b>\n"]

    for item in history:
        amount = _format_money(item["amount"])
        created_at = item["created_at"]

        if item["sender_id"] == user.id:
            direction = f"📤 Отправлено: <b>{amount}</b>"
        else:
            direction = f"📥 Получено: <b>{amount}</b>"

        lines.append(
            f"{direction}\n"
            f"🕒 {created_at}"
        )

    await update.effective_message.reply_text(
        "\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=bank_keyboard(),
    )


# ============================================================
# ОБРАБОТКА INLINE-КНОПОК
# ============================================================

async def economy_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if query is None or query.data is None:
        return

    await query.answer()

    user = _get_user(update)

    if user is None or query.message is None:
        return

    add_user(user.id, user.username or "")

    action = query.data

    if action == "econ:bank":
        wallet = get_balance(user.id)
        bank = get_bank_balance(user.id)

        await query.edit_message_text(
            "🏦 <b>ТВОЙ БАНК</b>\n\n"
            f"👛 Кошелёк: <b>{_format_money(wallet)}</b>\n"
            f"🏦 На счету: <b>{_format_money(bank)}</b>\n\n"
            "Выбери действие:",
            reply_markup=bank_keyboard(),
            parse_mode="HTML",
        )
        return

    if action == "econ:loans":
        loan = get_active_loan(user.id)

        if loan:
            text = (
                "📌 <b>ТВОЙ КРЕДИТ</b>\n\n"
                f"💳 Сумма кредита: "
                f"<b>{_format_money(loan['amount'])}</b>\n"
                f"💰 Осталось погасить: "
                f"<b>{_format_money(loan['remaining_amount'])}</b>\n"
                f"✅ Уже погашено: "
                f"<b>{_format_money(loan['repaid_amount'])}</b>\n\n"
            )
        else:
            text = (
                "📌 <b>ТВОИ КРЕДИТЫ</b>\n\n"
                "У тебя нет активного кредита.\n\n"
            )

        text += (
            f"Максимальный кредит: <b>{_format_money(MAX_LOAN_AMOUNT)}</b>\n\n"
            "Выбери действие:"
        )

        await query.edit_message_text(
            text,
            reply_markup=loan_keyboard(),
            parse_mode="HTML",
        )
        return

    amount_actions = {
        "econ:deposit": (
            "deposit",
            "📥 ВНЕСЕНИЕ ДЕНЕГ",
            "Введи сумму для внесения с кошелька в банк.",
        ),
        "econ:withdraw": (
            "withdraw",
            "📤 СНЯТИЕ ДЕНЕГ",
            "Введи сумму для снятия из банка в кошелёк.",
        ),
        "econ:take_loan": (
            "take_loan",
            "💸 НОВЫЙ КРЕДИТ",
            f"Введи сумму кредита от $1 до "
            f"{_format_money(MAX_LOAN_AMOUNT)}.",
        ),
        "econ:repay_loan": (
            "repay_loan",
            "💰 ПОГАШЕНИЕ КРЕДИТА",
            "Введи сумму, которую хочешь погасить.",
        ),
    }

    if action in amount_actions:
        state, title, prompt = amount_actions[action]
        context.user_data["economy_action"] = state

        await query.message.reply_text(
            f"<b>{title}</b>\n\n"
            f"{prompt}\n\n"
            "Отправь только число.",
            reply_markup=cancel_keyboard(),
            parse_mode="HTML",
        )
        return

    if action == "econ:cancel":
        context.user_data.pop("economy_action", None)

        await query.edit_message_text(
            "❌ Действие отменено."
        )
        return

    if action == "econ:loan_history":
        history = get_loan_history(user.id, limit=10)

        if not history:
            await query.edit_message_text(
                "📜 <b>ИСТОРИЯ КРЕДИТОВ</b>\n\n"
                "Записей пока нет.",
                reply_markup=loan_keyboard(),
                parse_mode="HTML",
            )
            return

        lines = [
            "📜 <b>ПОСЛЕДНИЕ ОПЕРАЦИИ ПО КРЕДИТАМ</b>\n"
        ]

        for item in history:
            lines.append(
                f"Действие: <b>{item['action']}</b>\n"
                f"Сумма: <b>{_format_money(item['amount'])}</b>\n"
                f"Остаток долга: "
                f"<b>{_format_money(item['remaining_after'])}</b>\n"
                f"Дата: {item['created_at']}"
            )

        await query.edit_message_text(
            "\n\n".join(lines),
            reply_markup=loan_keyboard(),
            parse_mode="HTML",
        )
        return

    if action == "econ:transfer_history":
        history = get_transfer_history(user.id, limit=10)

        if not history:
            await query.edit_message_text(
                "📜 <b>ИСТОРИЯ ПЕРЕВОДОВ</b>\n\n"
                "Переводов пока нет.",
                reply_markup=bank_keyboard(),
                parse_mode="HTML",
            )
            return

        lines = ["📜 <b>ПОСЛЕДНИЕ ПЕРЕВОДЫ</b>\n"]

        for item in history:
            amount = _format_money(item["amount"])

            if item["sender_id"] == user.id:
                direction = f"📤 Отправлено: <b>{amount}</b>"
            else:
                direction = f"📥 Получено: <b>{amount}</b>"

            lines.append(
                f"{direction}\n"
                f"🕒 {item['created_at']}"
            )

        await query.edit_message_text(
            "\n\n".join(lines),
            reply_markup=bank_keyboard(),
            parse_mode="HTML",
        )


# ============================================================
# ОБРАБОТКА ВВЕДЁННОЙ СУММЫ
# ============================================================

async def _process_amount(message, user_id, action, amount):
    if (
        not isinstance(amount, int)
        or isinstance(amount, bool)
        or amount <= 0
    ):
        await message.reply_text(
            "❌ Сумма должна быть положительным целым числом."
        )
        return

    if action == "deposit":
        success = deposit_money(user_id, amount)

        if not success:
            await message.reply_text(
                "❌ Недостаточно денег в кошельке."
            )
            return

        await message.reply_text(
            "✅ Деньги внесены в банк.\n\n"
            f"👛 Кошелёк: {_format_money(get_balance(user_id))}\n"
            f"🏦 Банк: {_format_money(get_bank_balance(user_id))}",
            reply_markup=bank_keyboard(),
        )
        return

    if action == "withdraw":
        success = withdraw_money(user_id, amount)

        if not success:
            await message.reply_text(
                "❌ Недостаточно денег на банковском счету."
            )
            return

        await message.reply_text(
            "✅ Деньги сняты со счёта.\n\n"
            f"👛 Кошелёк: {_format_money(get_balance(user_id))}\n"
            f"🏦 Банк: {_format_money(get_bank_balance(user_id))}",
            reply_markup=bank_keyboard(),
        )
        return

    if action == "take_loan":
        success, result = issue_loan(user_id, amount)

        if not success:
            errors = {
                "invalid_amount": "Укажи корректную сумму кредита.",
                "limit_exceeded": (
                    f"Максимальный кредит — "
                    f"{_format_money(MAX_LOAN_AMOUNT)}."
                ),
                "user_not_found": (
                    "Сначала зарегистрируйся через /acstart."
                ),
                "existing_debt": (
                    "У тебя уже есть непогашенный кредит."
                ),
            }

            await message.reply_text(
                "❌ "
                + errors.get(
                    result,
                    f"Не удалось выдать кредит: {result}",
                )
            )
            return

        await message.reply_text(
            "✅ <b>КРЕДИТ ВЫДАН</b>\n\n"
            f"Сумма: <b>{_format_money(amount)}</b>\n"
            f"Твой баланс: <b>{_format_money(get_balance(user_id))}</b>",
            reply_markup=loan_keyboard(),
            parse_mode="HTML",
        )
        return

    if action == "repay_loan":
        success, result = repay_loan(user_id, amount)

        if not success:
            errors = {
                "invalid_amount": "Укажи корректную сумму погашения.",
                "no_active_loan": "У тебя нет активного кредита.",
                "amount_exceeds_debt": (
                    "Сумма больше оставшегося долга."
                ),
                "insufficient_balance": (
                    "Недостаточно денег в кошельке."
                ),
                "user_not_found": (
                    "Сначала зарегистрируйся через /acstart."
                ),
            }

            await message.reply_text(
                "❌ "
                + errors.get(
                    result,
                    f"Не удалось погасить кредит: {result}",
                )
            )
            return

        loan = get_active_loan(user_id)
        remaining = int(loan["remaining_amount"]) if loan else 0

        await message.reply_text(
            "✅ <b>КРЕДИТ ПОГАШЕН</b>\n\n"
            f"Внесено: <b>{_format_money(amount)}</b>\n"
            f"Остаток долга: <b>{_format_money(remaining)}</b>\n"
            f"Кошелёк: <b>{_format_money(get_balance(user_id))}</b>",
            reply_markup=loan_keyboard(),
            parse_mode="HTML",
        )


async def process_economy_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if (
        update.effective_message is None
        or update.effective_user is None
    ):
        return

    action = context.user_data.get("economy_action")

    if not action:
        return

    text = (update.effective_message.text or "").strip()

    if text.startswith("/"):
        return

    try:
        amount = int(text)
    except ValueError:
        await update.effective_message.reply_text(
            "❌ Введи сумму целым числом или нажми «Отменить»."
        )
        return

    context.user_data.pop("economy_action", None)

    await _process_amount(
        update.effective_message,
        update.effective_user.id,
        action,
        amount,
    )