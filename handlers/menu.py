
import html
import logging

from handlers.transfer_history import transfer_history_command
from handlers.achievements import achievements_command
from handlers.quests import show_quests

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from keyboards.main_menu import main_menu
from keyboards.treasure import treasure_field
from games.treasure import create_game, get_game, delete_game

from core.database import (
    add_user,
    get_user,
    get_user_by_username,
    get_balance,
    get_bank_balance,
    deposit_money,
    withdraw_money,
    remove_money,
    change_balance,
    transfer_money,
    claim_daily_bonus,
    DAILY_BONUS_AMOUNT,
    get_daily_bonus_remaining,
    get_user_stats,
    get_top_users,
    get_user_rank,
)

from core.loans import (
    MAX_LOAN_AMOUNT,
    get_active_loan,
    get_loan_history,
    issue_loan,
    repay_loan,
)

from services.profile_card import generate_profile_card
from core.shop_database import get_equipped_details


logger = logging.getLogger(__name__)


# ==================================================
# КЛАВИАТУРЫ
# ==================================================

def bank_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["📥 Внести", "📤 Снять"],
            ["💳 Кредиты"],
            ["↩️ Назад"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def loan_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💸 Взять кредит", "💰 Погасить долг"],
            ["📜 История кредитов"],
            ["↩️ В банк"],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def daily_bonus_keyboard(user_id: int):
    remaining = get_daily_bonus_remaining(user_id)

    if remaining > 0:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        button_text = (
            f"⏳ Бонус через {hours} ч. {minutes} мин."
        )
    else:
        button_text = (
            f"🎁 Забрать бонус (+{DAILY_BONUS_AMOUNT:,} $)"
        )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"daily_bonus_claim:{user_id}",
                )
            ]
        ]
    )


# ==================================================
# INLINE-БОНУС В СООБЩЕНИИ БАЛАНСА
# ==================================================

async def daily_bonus_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query or not query.from_user:
        return

    try:
        owner_id = int(query.data.split(":", 1)[1])
    except (AttributeError, IndexError, TypeError, ValueError):
        await query.answer(
            "❌ Не удалось определить владельца бонуса.",
            show_alert=True,
        )
        return

    # Не позволяем другим игрокам забирать бонус по чужой кнопке.
    if query.from_user.id != owner_id:
        await query.answer(
            "❌ Это кнопка бонуса другого игрока.",
            show_alert=True,
        )
        return

    user = query.from_user
    add_user(user.id, user.username or "unknown")

    claimed, remaining = claim_daily_bonus(user.id)
    money = get_balance(user.id)

    if claimed:
        text = (
            "🪙 <b>ACECOIN CASINO</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Баланс: <b>{money:,} $</b>\n\n"
            "🎁 <b>Ежедневный бонус получен!</b>\n"
            f"🪙 Начислено: <b>+{DAILY_BONUS_AMOUNT:,} $</b>\n\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await query.answer(
            f"🎁 Получено {DAILY_BONUS_AMOUNT:,} $!"
        )

    elif remaining > 0:
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60

        text = (
            "🪙 <b>ACECOIN CASINO</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Баланс: <b>{money:,} $</b>\n\n"
            "⏳ <b>Ты уже получил ежедневный бонус.</b>\n"
            f"До следующего: <b>{hours} ч. {minutes} мин.</b>\n\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await query.answer(
            f"Бонус будет доступен через {hours} ч. {minutes} мин.",
            show_alert=True,
        )

    else:
        text = (
            "🪙 <b>ACECOIN CASINO</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Баланс: <b>{money:,} $</b>\n\n"
            "❌ Не удалось начислить бонус.\n"
            "Попробуй ещё раз позже.\n\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await query.answer(
            "Не удалось получить бонус.",
            show_alert=True,
        )

    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=daily_bonus_keyboard(user.id),
    )


def is_main_menu_button(text):
    return text in {
        "💰 Баланс",
        "🎁 Ежедневный бонус",
        "🎮 Игры",
        "🛒 Магазин",
        "👤 Профиль",
        "📊 Статистика",
        "🏆 Топ",
        "🏆 Квесты",
        "🏅 Достижения",
        "📢 Канал бота",
        "💎 Сокровища",
        "🏦 Банк",
        "📜 История переводов",
    }


# ==================================================
# БАНК
# ==================================================

async def show_bank(message, user_id):
    wallet = get_balance(user_id)
    bank = get_bank_balance(user_id)

    await message.reply_text(
        "🏦 <b>БАНК ACECOIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👛 Кошелёк: <b>{wallet:,} $</b>\n"
        f"🏦 В банке: <b>{bank:,} $</b>\n\n"
        "💡 Храни монеты в банке или снимай их,\n"
        "когда они понадобятся для игры.\n\n"
        "💳 Нужны дополнительные монеты? "
        "Загляни в раздел кредитов.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Выбери нужное действие:",
        parse_mode="HTML",
        reply_markup=bank_keyboard(),
    )


# ==================================================
# КРЕДИТЫ
# ==================================================

async def show_loans(message, user_id):
    wallet = get_balance(user_id)
    loan = get_active_loan(user_id)

    if loan:
        debt = loan["remaining_amount"]
        loan_text = (
            "📌 <b>ТВОЙ АКТИВНЫЙ КРЕДИТ</b>\n"
            f"💳 Первоначальная сумма: "
            f"<b>{loan['amount']:,} $</b>\n"
            f"💸 Осталось выплатить: <b>{debt:,} $</b>\n"
            f"✅ Уже погашено: <b>{loan['repaid_amount']:,} $</b>\n\n"
            "Пока долг не погашен полностью,\n"
            "новый кредит оформить нельзя."
        )
    else:
        loan_text = (
            "✅ <b>У ТЕБЯ НЕТ ДОЛГОВ</b>\n\n"
            "Ты можешь оформить новый кредит."
        )

    await message.reply_text(
        "💳 <b>КРЕДИТНЫЙ ЦЕНТР ACECOIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👛 Твой кошелёк: <b>{wallet:,} $</b>\n"
        f"📈 Максимальный кредит: <b>{MAX_LOAN_AMOUNT:,} $</b>\n"
        "📊 Процентная ставка: <b>0%</b>\n\n"
        f"{loan_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Выбери действие:",
        parse_mode="HTML",
        reply_markup=loan_keyboard(),
    )


async def start_loan_action(message, context, action):
    context.user_data.pop("bank_action", None)
    context.user_data["loan_action"] = action

    if action == "issue":
        loan = get_active_loan(message.from_user.id)

        if loan:
            context.user_data.pop("loan_action", None)
            await show_loans(message, message.from_user.id)
            return

        await message.reply_text(
            "💸 <b>ОФОРМЛЕНИЕ КРЕДИТА</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Можно получить от 1 до {MAX_LOAN_AMOUNT:,} $.\n"
            "📈 Проценты: 0%.\n\n"
            "Напиши сумму кредита одним сообщением.\n"
            "Например: <code>5000</code>\n\n"
            "↩️ Для отмены нажми «В банк».",
            parse_mode="HTML",
            reply_markup=loan_keyboard(),
        )

    elif action == "repay":
        loan = get_active_loan(message.from_user.id)

        if not loan:
            context.user_data.pop("loan_action", None)
            await message.reply_text(
                "✅ У тебя нет непогашенных кредитов!",
                reply_markup=loan_keyboard(),
            )
            return

        await message.reply_text(
            "💰 <b>ПОГАШЕНИЕ КРЕДИТА</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💸 Остаток долга: "
            f"<b>{loan['remaining_amount']:,} $</b>\n"
            f"👛 Твой кошелёк: "
            f"<b>{get_balance(message.from_user.id):,} $</b>\n\n"
            "Напиши сумму, которую хочешь вернуть.\n"
            "Можно погасить долг частично или полностью.\n"
            "Минимальная сумма — 1 $.\n\n"
            "↩️ Для отмены нажми «В банк».",
            parse_mode="HTML",
            reply_markup=loan_keyboard(),
        )


async def show_loan_history(message, user_id):
    history = get_loan_history(user_id, limit=10)

    if not history:
        await message.reply_text(
            "📜 <b>ИСТОРИЯ КРЕДИТОВ</b>\n\n"
            "У тебя пока нет кредитных операций.",
            parse_mode="HTML",
            reply_markup=loan_keyboard(),
        )
        return

    lines = []

    for item in history:
        if item["action"] == "issued":
            title = "💸 Получен кредит"
            amount_text = f"+{item['amount']:,} $"
        elif item["action"] == "repayment":
            title = "💰 Погашение долга"
            amount_text = f"-{item['amount']:,} $"
        else:
            title = "📌 Операция"
            amount_text = f"{item['amount']:,} $"

        date_text = "Дата не указана"

        try:
            from datetime import datetime

            date_text = datetime.fromtimestamp(
                item["created_at"]
            ).strftime("%d.%m.%Y %H:%M")
        except (ValueError, TypeError, OSError):
            pass

        lines.append(
            f"{title}\n"
            f"🪙 Сумма: <b>{amount_text}</b>\n"
            f"📉 Остаток долга: "
            f"<b>{item['remaining_after']:,} $</b>\n"
            f"🕒 {date_text}"
        )

    await message.reply_text(
        "📜 <b>ИСТОРИЯ КРЕДИТОВ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines)
        + "\n\n━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=loan_keyboard(),
    )


async def process_loan_amount(message, context, user_id, text):
    action = context.user_data.get("loan_action")

    try:
        amount = int(text)
    except (ValueError, TypeError):
        await message.reply_text(
            "❌ Введи сумму целым числом.\n"
            "Например: <code>500</code>",
            parse_mode="HTML",
            reply_markup=loan_keyboard(),
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ Сумма должна быть больше нуля.",
            reply_markup=loan_keyboard(),
        )
        return

    if amount > 2_147_483_647:
        await message.reply_text(
            "❌ Сумма слишком большая.",
            reply_markup=loan_keyboard(),
        )
        return

    if action == "issue":
        if amount > MAX_LOAN_AMOUNT:
            await message.reply_text(
                f"❌ Максимальный кредит — "
                f"{MAX_LOAN_AMOUNT:,} $.\n"
                "Введи другую сумму.",
                reply_markup=loan_keyboard(),
            )
            return

        success, result = issue_loan(user_id, amount)

        if not success:
            errors = {
                "invalid_amount": "❌ Укажи корректную сумму кредита.",
                "limit_exceeded": (
                    f"❌ Максимальный кредит — {MAX_LOAN_AMOUNT:,} $."
                ),
                "existing_debt": (
                    "❌ У тебя уже есть непогашенный кредит.\n"
                    "Сначала полностью верни старый долг."
                ),
                "user_not_found": (
                    "❌ Профиль не найден. Нажми /start."
                ),
            }

            await message.reply_text(
                errors.get(
                    result,
                    "❌ Не удалось оформить кредит. Попробуй ещё раз.",
                ),
                reply_markup=loan_keyboard(),
            )
            return

        context.user_data.pop("loan_action", None)

        await message.reply_text(
            "💳 <b>КРЕДИТ ОДОБРЕН!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🪙 Получено: <b>+{amount:,} $</b>\n"
            "📈 Проценты: <b>0%</b>\n"
            f"💸 Твой долг: <b>{amount:,} $</b>\n"
            f"👛 Баланс кошелька: "
            f"<b>{get_balance(user_id):,} $</b>\n\n"
            "💡 Возвращай долг частями или полностью.\n"
            "Новый кредит станет доступен после полного погашения.\n\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
            reply_markup=loan_keyboard(),
        )
        return

    if action == "repay":
        loan = get_active_loan(user_id)

        if not loan:
            context.user_data.pop("loan_action", None)
            await message.reply_text(
                "✅ У тебя нет непогашенных кредитов.",
                reply_markup=loan_keyboard(),
            )
            return

        if amount > loan["remaining_amount"]:
            await message.reply_text(
                "❌ Сумма больше остатка долга.\n"
                f"💸 Осталось вернуть: "
                f"{loan['remaining_amount']:,} $.\n\n"
                "Введи другую сумму.",
                reply_markup=loan_keyboard(),
            )
            return

        success, result = repay_loan(user_id, amount)

        if not success:
            errors = {
                "invalid_amount": "❌ Укажи корректную сумму.",
                "no_active_loan": "❌ У тебя нет активного кредита.",
                "amount_exceeds_debt": (
                    "❌ Сумма превышает остаток долга."
                ),
                "insufficient_balance": (
                    "❌ Недостаточно монет в кошельке.\n"
                    f"👛 Твой баланс: {get_balance(user_id):,} $."
                ),
                "user_not_found": (
                    "❌ Профиль не найден. Нажми /start."
                ),
            }

            await message.reply_text(
                errors.get(
                    result,
                    "❌ Не удалось погасить кредит. Попробуй ещё раз.",
                ),
                reply_markup=loan_keyboard(),
            )
            return

        context.user_data.pop("loan_action", None)
        remaining = result["remaining_amount"]

        if remaining == 0:
            debt_message = (
                "🎉 <b>КРЕДИТ ПОГАШЕН ПОЛНОСТЬЮ!</b>\n"
                "Теперь ты можешь оформить новый кредит."
            )
        else:
            debt_message = (
                "📌 <b>КРЕДИТ ЕЩЁ НЕ ПОГАШЕН</b>\n"
                f"Осталось вернуть: <b>{remaining:,} $</b>."
            )

        await message.reply_text(
            "💰 <b>ПОГАШЕНИЕ КРЕДИТА</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🪙 Возвращено: <b>{amount:,} $</b>\n"
            f"💸 Остаток долга: <b>{remaining:,} $</b>\n"
            f"👛 Баланс кошелька: "
            f"<b>{get_balance(user_id):,} $</b>\n\n"
            f"{debt_message}\n\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
            reply_markup=loan_keyboard(),
        )
        return

    context.user_data.pop("loan_action", None)


# ==================================================
# БАЛАНС
# ==================================================

async def balance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not user or not update.message:
        return

    add_user(user.id, user.username or "unknown")
    money = get_balance(user.id)

    await update.message.reply_text(
        "🪙 <b>ACECOIN CASINO</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Баланс: <b>{money:,} $</b>\n\n"
        "━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=daily_bonus_keyboard(user.id),
    )


# ==================================================
# ПЕРЕВОДЫ
# ==================================================

async def transfer_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    sender = update.effective_user

    if not message or not sender:
        return

    add_user(sender.id, sender.username or "unknown")

    recipient = None
    amount_text = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user

        if not target:
            await message.reply_text(
                "❌ Не удалось определить получателя перевода."
            )
            return

        if target.is_bot:
            await message.reply_text(
                "❌ Нельзя переводить монеты ботам."
            )
            return

        recipient = target

        if len(context.args) == 1:
            amount_text = context.args[0]
        else:
            await message.reply_text(
                "💸 <b>ПЕРЕВОД</b>\n\n"
                "Ответь на сообщение игрока командой:\n"
                "<code>/pay 500</code>",
                parse_mode="HTML",
            )
            return

    else:
        if len(context.args) != 2:
            await message.reply_text(
                "💸 <b>ПЕРЕВОД</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Перевод по username:\n"
                "<code>/pay @username 500</code>\n\n"
                "Или ответом на сообщение:\n"
                "<code>/pay 500</code>\n\n"
                "💰 Комиссия: 0 $\n"
                "━━━━━━━━━━━━━━━━━━",
                parse_mode="HTML",
            )
            return

        username = context.args[0].strip().lstrip("@")
        amount_text = context.args[1]

        if not username or username.lower() == "unknown":
            await message.reply_text(
                "❌ Укажи корректный Telegram username."
            )
            return

        recipient_record = get_user_by_username(username)

        if not recipient_record:
            await message.reply_text(
                "❌ Игрок не найден в базе AceCoin Casino.\n\n"
                "Он должен сначала запустить бота командой /start."
            )
            return

        recipient_id = recipient_record["user_id"]

        if recipient_id == sender.id:
            await message.reply_text(
                "❌ Нельзя переводить монеты самому себе."
            )
            return

        class Recipient:
            id = recipient_id
            username = recipient_record["username"]
            first_name = recipient_record["username"] or "Игрок"
            is_bot = False

        recipient = Recipient()

    if recipient.id == sender.id:
        await message.reply_text(
            "❌ Нельзя переводить монеты самому себе."
        )
        return

    if recipient.is_bot:
        await message.reply_text(
            "❌ Нельзя переводить монеты ботам."
        )
        return

    try:
        amount = int(amount_text)
    except (ValueError, TypeError):
        await message.reply_text(
            "❌ Сумма должна быть целым числом.\n"
            "Пример: <code>/pay 500</code>",
            parse_mode="HTML",
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ Сумма перевода должна быть больше нуля."
        )
        return

    if amount > 2_147_483_647:
        await message.reply_text("❌ Сумма слишком большая.")
        return

    add_user(recipient.id, recipient.username or "unknown")

    success, result = transfer_money(
        sender.id,
        recipient.id,
        amount,
    )

    if not success:
        errors = {
            "invalid_amount": "❌ Некорректная сумма перевода.",
            "same_user": "❌ Нельзя переводить монеты самому себе.",
            "sender_not_found": "❌ Твой профиль не найден. Нажми /start.",
            "recipient_not_found": "❌ Профиль получателя не найден.",
            "insufficient_funds": "❌ Недостаточно средств для перевода.",
        }

        await message.reply_text(
            errors.get(
                result,
                "❌ Не удалось выполнить перевод. Попробуй ещё раз.",
            )
        )
        return

    sender_balance = get_balance(sender.id)
    recipient_balance = get_balance(recipient.id)

    sender_name = html.escape(sender.first_name or "Игрок")
    recipient_name = html.escape(
        getattr(recipient, "first_name", None) or "Игрок"
    )

    await message.reply_text(
        "💸 <b>ПЕРЕВОД УСПЕШНО ВЫПОЛНЕН</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Отправитель: <b>{sender_name}</b>\n"
        f"🎯 Получатель: <b>{recipient_name}</b>\n"
        f"🪙 Переведено: <b>{amount:,} $</b>\n"
        "💳 Комиссия: <b>0 $</b>\n\n"
        f"💰 Твой баланс: <b>{sender_balance:,} $</b>\n"
        "━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )

    try:
        await context.bot.send_message(
            chat_id=recipient.id,
            text=(
                "💰 <b>ТЕБЕ ПЕРЕВЕЛИ МОНЕТЫ!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 Отправитель: <b>{sender_name}</b>\n"
                f"🪙 Получено: <b>+{amount:,} $</b>\n"
                f"💰 Твой баланс: <b>{recipient_balance:,} $</b>\n\n"
                "━━━━━━━━━━━━━━━━━━"
            ),
            parse_mode="HTML",
        )
    except Exception:
        logger.info(
            "Не удалось отправить уведомление о переводе пользователю %s.",
            recipient.id,
        )


# ==================================================
# СОКРОВИЩА
# ==================================================

async def treasure_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    if not user or not update.message:
        return

    user_id = user.id
    add_user(user_id, user.username or "unknown")

    if len(context.args) != 1:
        await update.message.reply_text(
            "💎 <b>СОКРОВИЩА</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Использование: <code>/treasure 100</code>\n"
            "Число — размер твоей ставки.\n\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
        )
        return

    try:
        bet = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ Ставка должна быть целым числом.\n"
            "Пример: <code>/treasure 100</code>",
            parse_mode="HTML",
        )
        return

    if bet <= 0:
        await update.message.reply_text(
            "❌ Ставка должна быть больше нуля."
        )
        return

    current_game = get_game(user_id)

    if current_game and not current_game["finished"]:
        await update.message.reply_text(
            "⚠️ У тебя уже идёт игра «Сокровища»."
        )
        return

    money = get_balance(user_id)

    if money < bet:
        await update.message.reply_text(
            "❌ Недостаточно средств.\n\n"
            f"💰 Баланс: {money:,} $\n"
            f"🎲 Ставка: {bet:,} $"
        )
        return

    if not remove_money(user_id, bet):
        await update.message.reply_text(
            "❌ Не удалось списать ставку. "
            "Проверь баланс и попробуй снова."
        )
        return

    create_game(user_id, bet)

    try:
        await update.message.reply_text(
            "💎 <b>ACECOIN CASINO</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "💰 <b>ИГРА «СОКРОВИЩА»</b>\n\n"
            f"👤 Игрок: {html.escape(user.first_name or 'Игрок')}\n"
            f"🪙 Ставка: <b>{bet:,} $</b>\n"
            "💎 Сокровищ: 20\n"
            "💣 Бомб: 5\n\n"
            "Выбирай клетку и испытывай удачу!\n"
            "━━━━━━━━━━━━━━━━━━",
            reply_markup=treasure_field(),
            parse_mode="HTML",
        )

    except Exception:
        logger.exception(
            "Не удалось отправить игровое поле игроку %s",
            user_id,
        )

        change_balance(user_id, bet)
        delete_game(user_id)

        try:
            await update.message.reply_text(
                "❌ Не удалось запустить игру.\n"
                f"Ставка {bet:,} $ возвращена на баланс."
            )
        except Exception:
            logger.exception(
                "Не удалось сообщить об ошибке игроку %s",
                user_id,
            )


# ==================================================
# ОБРАБОТЧИК КНОПОК
# ==================================================

async def menu_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.message
    user = update.effective_user

    if not message or not message.text or not user:
        return

    text = message.text.strip()
    add_user(user.id, user.username or "unknown")

    # Ввод суммы кредита.
    loan_action = context.user_data.get("loan_action")

    if loan_action:
        if text == "↩️ В банк":
            context.user_data.pop("loan_action", None)
            await show_bank(message, user.id)
            return

        if text == "💸 Взять кредит":
            await start_loan_action(message, context, "issue")
            return

        if text == "💰 Погасить долг":
            await start_loan_action(message, context, "repay")
            return

        if text == "📜 История кредитов":
            context.user_data.pop("loan_action", None)
            await show_loan_history(message, user.id)
            return

        if text == "💳 Кредиты":
            context.user_data.pop("loan_action", None)
            await show_loans(message, user.id)
            return

        if is_main_menu_button(text):
            context.user_data.pop("loan_action", None)
        else:
            await process_loan_amount(
                message,
                context,
                user.id,
                text,
            )
            return

    # Ввод суммы банковской операции.
    bank_action = context.user_data.get("bank_action")

    if bank_action:
        if text == "↩️ Назад":
            context.user_data.pop("bank_action", None)
            await message.reply_text(
                "↩️ Возвращаемся в главное меню.",
                reply_markup=main_menu(),
            )
            return

        if text == "🏦 Банк":
            context.user_data.pop("bank_action", None)
            await show_bank(message, user.id)
            return

        if text == "💳 Кредиты":
            context.user_data.pop("bank_action", None)
            await show_loans(message, user.id)
            return

        if text == "📥 Внести":
            context.user_data["bank_action"] = "deposit"
            await message.reply_text(
                "📥 <b>ВНЕСЕНИЕ В БАНК</b>\n\n"
                "Отправь сумму для внесения.\n"
                "Например: <code>500</code>\n\n"
                "↩️ Для отмены нажми «Назад».",
                parse_mode="HTML",
                reply_markup=bank_keyboard(),
            )
            return

        if text == "📤 Снять":
            context.user_data["bank_action"] = "withdraw"
            await message.reply_text(
                "📤 <b>СНЯТИЕ ИЗ БАНКА</b>\n\n"
                "Отправь сумму для снятия.\n"
                "Например: <code>500</code>\n\n"
                "↩️ Для отмены нажми «Назад».",
                parse_mode="HTML",
                reply_markup=bank_keyboard(),
            )
            return

        if is_main_menu_button(text):
            context.user_data.pop("bank_action", None)
        else:
            try:
                amount = int(text)
            except (ValueError, TypeError):
                await message.reply_text(
                    "❌ Введи сумму целым числом.\n"
                    "Например: <code>500</code>",
                    parse_mode="HTML",
                    reply_markup=bank_keyboard(),
                )
                return

            if amount <= 0:
                await message.reply_text(
                    "❌ Сумма должна быть больше нуля.",
                    reply_markup=bank_keyboard(),
                )
                return

            if amount > 2_147_483_647:
                await message.reply_text(
                    "❌ Сумма слишком большая.",
                    reply_markup=bank_keyboard(),
                )
                return

            if bank_action == "deposit":
                success = deposit_money(user.id, amount)

                if not success:
                    await message.reply_text(
                        "❌ <b>НЕ УДАЛОСЬ ВНЕСТИ МОНЕТЫ</b>\n\n"
                        "Возможно, в кошельке недостаточно средств.\n\n"
                        f"👛 Кошелёк: "
                        f"<b>{get_balance(user.id):,} $</b>\n"
                        f"🏦 В банке: "
                        f"<b>{get_bank_balance(user.id):,} $</b>\n\n"
                        "Попробуй другую сумму.",
                        parse_mode="HTML",
                        reply_markup=bank_keyboard(),
                    )
                    return

                context.user_data.pop("bank_action", None)
                await message.reply_text(
                    "📥 <b>ПОПОЛНЕНИЕ БАНКА УСПЕШНО</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"🪙 Внесено: <b>{amount:,} $</b>\n\n"
                    f"👛 Кошелёк: "
                    f"<b>{get_balance(user.id):,} $</b>\n"
                    f"🏦 В банке: "
                    f"<b>{get_bank_balance(user.id):,} $</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML",
                    reply_markup=bank_keyboard(),
                )
                return

            if bank_action == "withdraw":
                success = withdraw_money(user.id, amount)

                if not success:
                    await message.reply_text(
                        "❌ <b>НЕ УДАЛОСЬ СНЯТЬ МОНЕТЫ</b>\n\n"
                        "Возможно, в банке недостаточно средств.\n\n"
                        f"🏦 В банке: "
                        f"<b>{get_bank_balance(user.id):,} $</b>\n"
                        f"👛 Кошелёк: "
                        f"<b>{get_balance(user.id):,} $</b>\n\n"
                        "Попробуй другую сумму.",
                        parse_mode="HTML",
                        reply_markup=bank_keyboard(),
                    )
                    return

                context.user_data.pop("bank_action", None)
                await message.reply_text(
                    "📤 <b>СНЯТИЕ ИЗ БАНКА УСПЕШНО</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"🪙 Снято: <b>{amount:,} $</b>\n\n"
                    f"👛 Кошелёк: "
                    f"<b>{get_balance(user.id):,} $</b>\n"
                    f"🏦 В банке: "
                    f"<b>{get_bank_balance(user.id):,} $</b>\n\n"
                    "━━━━━━━━━━━━━━━━━━",
                    parse_mode="HTML",
                    reply_markup=bank_keyboard(),
                )
                return

            context.user_data.pop("bank_action", None)

    # Главное меню.
    if text == "📜 История переводов":
        context.user_data.pop("bank_action", None)
        context.user_data.pop("loan_action", None)
        await transfer_history_command(update, context)
        return

    if text == "🏅 Достижения":
        context.user_data.pop("bank_action", None)
        context.user_data.pop("loan_action", None)
        await achievements_command(update, context)
        return

    if text == "🏦 Банк":
        context.user_data.pop("loan_action", None)
        await show_bank(message, user.id)

    elif text == "💳 Кредиты":
        context.user_data.pop("bank_action", None)
        await show_loans(message, user.id)

    elif text == "💸 Взять кредит":
        await start_loan_action(message, context, "issue")

    elif text == "💰 Погасить долг":
        await start_loan_action(message, context, "repay")

    elif text == "📜 История кредитов":
        await show_loan_history(message, user.id)

    elif text == "↩️ В банк":
        context.user_data.pop("loan_action", None)
        await show_bank(message, user.id)

    elif text == "📥 Внести":
        context.user_data["bank_action"] = "deposit"
        await message.reply_text(
            "📥 <b>ВНЕСЕНИЕ В БАНК</b>\n\n"
            "Отправь сумму для внесения.\n"
            "Например: <code>500</code>\n\n"
            "↩️ Для отмены нажми «Назад».",
            parse_mode="HTML",
            reply_markup=bank_keyboard(),
        )

    elif text == "📤 Снять":
        context.user_data["bank_action"] = "withdraw"
        await message.reply_text(
            "📤 <b>СНЯТИЕ ИЗ БАНКА</b>\n\n"
            "Отправь сумму для снятия.\n"
            "Например: <code>500</code>\n\n"
            "↩️ Для отмены нажми «Назад».",
            parse_mode="HTML",
            reply_markup=bank_keyboard(),
        )

    elif text == "↩️ Назад":
        context.user_data.pop("bank_action", None)
        context.user_data.pop("loan_action", None)
        await message.reply_text(
            "↩️ Возвращаемся в главное меню.",
            reply_markup=main_menu(),
        )

    elif text == "💰 Баланс":
        await balance(update, context)

    elif text == "🎁 Ежедневный бонус":
        claimed, remaining = claim_daily_bonus(user.id)

        if claimed:
            money = get_balance(user.id)
            await message.reply_text(
                "🎁 <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"🪙 Начислено: "
                f"<b>+{DAILY_BONUS_AMOUNT:,} $</b>\n"
                f"💰 Твой баланс: <b>{money:,} $</b>\n\n"
                "Возвращайся через 24 часа за новым бонусом!\n"
                "━━━━━━━━━━━━━━━━━━",
                parse_mode="HTML",
            )

        elif remaining > 0:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await message.reply_text(
                "⏳ <b>ЕЖЕДНЕВНЫЙ БОНУС</b>\n\n"
                "Ты уже забирал сегодняшний бонус.\n"
                f"🕒 До следующего: "
                f"<b>{hours} ч. {minutes} мин.</b>",
                parse_mode="HTML",
            )

        else:
            await message.reply_text(
                "❌ Не удалось получить бонус. "
                "Проверь регистрацию профиля и попробуй снова."
            )

    elif text == "💎 Сокровища":
        await message.reply_text(
            "💎 <b>СОКРОВИЩА</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Чтобы начать игру, используй команду:\n"
            "<code>/treasure 100</code>\n\n"
            "Замени 100 на размер своей ставки.\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
        )

    elif text == "🎮 Игры":
        await message.reply_text(
            "🎰 <b>ACECOIN CASINO</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🎮 <b>ИГРОВОЙ ЗАЛ</b>\n\n"
            "Добро пожаловать за игровой стол!\n"
            "Выбирай игру, делай ставку и испытывай удачу.\n\n"
            "💎 <b>СОКРОВИЩА</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔹 Открывай клетки и ищи сокровища.\n"
            "🔹 Остерегайся бомб.\n"
            "🔹 Начни игру командой:\n"
            "<code>/treasure 100</code>\n\n"
            "💡 Число в команде — размер ставки.\n"
            "Например, для ставки 500 используй:\n"
            "<code>/treasure 500</code>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🛠️ <b>НОВЫЕ ИГРЫ</b>\n"
            "Другие игровые режимы появятся по мере "
            "развития казино.\n\n"
            "🪙 Баланс: <code>/balance</code>\n"
            "💸 Перевод: <code>/pay @username 500</code>\n"
            "📖 Помощь: <code>/help</code>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🔥 <i>Твоя ставка. Твой риск. Твой путь к вершине.</i>",
            parse_mode="HTML",
        )

    elif text == "🛒 Магазин":
        from handlers.shop import show_shop
        await show_shop(update, context)
        return

    elif text == "📊 Статистика":
        await stats_command(update, context)

        if not stats:
            await message.reply_text(
                "❌ Профиль не найден. Нажми /start и попробуй снова."
            )
            return

        await message.reply_text(
            "📊 <b>СТАТИСТИКА ACECOIN</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 Игрок: <b>{html.escape(user.first_name or 'Игрок')}</b>\n"
            f"⭐ Опыт: <b>{stats['xp']} XP</b>\n"
            f"🎚️ Уровень: <b>{stats['level']}</b>\n"
            f"💎 Ранг: <b>{stats['rank_emoji']} {stats['rank']}</b>\n"
            f"📈 До следующего уровня: "
            f"<b>{stats['xp_to_next_level']} XP</b>\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🏆 Победы: <b>{stats['wins']}</b>\n"
            f"💥 Поражения: <b>{stats['losses']}</b>\n"
            f"🎮 Игр завершено: <b>{stats['games_played']}</b>\n"
            f"💰 Общий выигрыш: "
            f"<b>{stats['total_winnings']:,} $</b>\n\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
        )

    elif text == "🏆 Квесты":
        await show_quests(update, context)

    elif text == "👤 Профиль":
        money = get_balance(user.id)
        stats = get_user_stats(user.id)

        if not stats:
            await message.reply_text(
                "❌ Профиль не найден. Нажми /start и попробуй снова."
            )
            return

        try:
            avatar_bytes = None

            photos = await context.bot.get_user_profile_photos(
                user_id=user.id,
                limit=1,
            )

            if photos.total_count > 0 and photos.photos:
                photo = photos.photos[0][-1]
                telegram_file = await context.bot.get_file(photo.file_id)
                avatar_bytes = bytes(
                    await telegram_file.download_as_bytearray()
                )

            cosmetics = get_equipped_details(user.id)
            equipped_frame = cosmetics.get("frame_id")
            equipped_title = cosmetics.get("title")

            title_text = (
                equipped_title.get("name")
                if equipped_title
                else None
            )

            profile_image = generate_profile_card(
                first_name=user.first_name or "Игрок",
                username=user.username or "",
                user_id=user.id,
                balance=money,
                avatar_bytes=avatar_bytes,
                level=stats["level"],
                rank=stats["rank"],
                rank_emoji=stats["rank_emoji"],
                xp=stats["xp"],
                xp_in_level=stats["xp_in_level"],
                xp_per_level=stats["xp_per_level"],
                frame_id=equipped_frame,
                title=title_text,
            )

            await message.reply_photo(
                photo=profile_image,
                caption=(
                    "🖤 <b>ACECOIN CASINO</b>\n"
                    f"{stats['rank_emoji']} Ранг: "
                    f"<b>{html.escape(stats['rank'])}</b>\n"
                    f"🎚️ Уровень: <b>{stats['level']}</b> · "
                    f"⭐ XP: <b>{stats['xp']}</b>\n"
                    "🎰 Твоя игра. Твои правила."
                ),
                parse_mode="HTML",
            )

        except Exception:
            logger.exception(
                "Не удалось создать карточку профиля пользователя %s",
                user.id,
            )
            await message.reply_text(
                "❌ Не удалось создать карточку профиля.\n"
                "Подробности ошибки находятся в терминале."
            )

    elif text == "📢 Канал бота":
        await message.reply_text(
            "📢 <b>КАНАЛ ACECOIN CASINO</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Новости, обновления и новые возможности казино.\n\n"
            "👇 Подписывайся на канал!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📢 Открыть канал",
                            url="https://t.me/QxlRu9bXe51lZjAy",
                        )
                    ]
                ]
            ),
        )

    elif text == "🏆 Топ":
        top_users = get_top_users(10)
        my_position = get_user_rank(user.id)

        if not top_users:
            await message.reply_text(
                "🏆 <b>ТОП ИГРОКОВ ACECOIN</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Пока рейтинг пуст. Стань первым игроком!\n\n"
                "━━━━━━━━━━━━━━━━━━",
                parse_mode="HTML",
            )
            return

        medals = ["🥇", "🥈", "🥉"]
        lines = []

        for player in top_users:
            position = player["position"]

            if position <= 3:
                medal = medals[position - 1]
            else:
                medal = f"<b>{position}.</b>"

            username = player.get("username") or ""
            safe_username = html.escape(username)

            if safe_username and safe_username != "unknown":
                player_name = f"@{safe_username}"
            else:
                player_name = f"Игрок {player['user_id']}"

            lines.append(
                f"{medal} {player.get('rank_emoji', '⭐')} "
                f"<b>{player.get('level', 1)} ур.</b> — "
                f"{player_name}\n"
                f"   ⭐ XP: <b>{player.get('xp', 0):,}</b>"
            )

        rating_text = "\n\n".join(lines)

        if my_position:
            rating_text += (
                "\n\n━━━━━━━━━━━━━━━━━━\n"
                f"👤 Твоё место: <b>#{my_position}</b>"
            )

        await message.reply_text(
            "🏆 <b>ТОП ИГРОКОВ ACECOIN</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"{rating_text}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🎮 Играй, получай XP и поднимайся в рейтинге!",
            parse_mode="HTML",
        )

# ==================================================
# КОМАНДА /STATS И КНОПКА «СТАТИСТИКА»
# ==================================================

async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    add_user(user.id, user.username or "unknown")
    stats = get_user_stats(user.id)

    if not stats:
        await message.reply_text(
            "❌ Профиль не найден. Нажми /start и попробуй снова."
        )
        return

    await message.reply_text(
        "📊 <b>СТАТИСТИКА ACECOIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Игрок: <b>{html.escape(user.first_name or 'Игрок')}</b>\n"
        f"⭐ Опыт: <b>{stats['xp']} XP</b>\n"
        f"🎚️ Уровень: <b>{stats['level']}</b>\n"
        f"💎 Ранг: <b>{stats['rank_emoji']} {stats['rank']}</b>\n"
        f"📈 До следующего уровня: "
        f"<b>{stats['xp_to_next_level']} XP</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🏆 Победы: <b>{stats['wins']}</b>\n"
        f"💥 Поражения: <b>{stats['losses']}</b>\n"
        f"🎮 Игр завершено: <b>{stats['games_played']}</b>\n"
        f"💰 Общий выигрыш: "
        f"<b>{stats['total_winnings']:,} $</b>\n\n"
        "━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
    )

# ==================================================
# КОМАНДА /RATING
# ==================================================

async def rating_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    # Используем тот же рейтинг, что и кнопка «🏆 Топ».
    await menu_buttons_rating(update, context)


async def menu_buttons_rating(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    add_user(user.id, user.username or "unknown")
    top_users = get_top_users(10)
    my_position = get_user_rank(user.id)

    if not top_users:
        await message.reply_text(
            "🏆 <b>ТОП ИГРОКОВ ACECOIN</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Пока рейтинг пуст. Стань первым игроком!\n\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []

    for player in top_users:
        position = player["position"]
        medal = (
            medals[position - 1]
            if position <= 3
            else f"<b>{position}.</b>"
        )

        username = html.escape(player.get("username") or "")

        if username and username.lower() != "unknown":
            player_name = f"@{username}"
        else:
            player_name = f"Игрок {player['user_id']}"

        lines.append(
            f"{medal} {player.get('rank_emoji', '⭐')} "
            f"<b>{player.get('level', 1)} ур.</b> — "
            f"{player_name}\n"
            f"   ⭐ XP: <b>{player.get('xp', 0):,}</b>"
        )

    rating_text = "\n\n".join(lines)

    if my_position:
        rating_text += (
            "\n\n━━━━━━━━━━━━━━━━━━\n"
            f"👤 Твоё место: <b>#{my_position}</b>"
        )

    await message.reply_text(
        "🏆 <b>ТОП ИГРОКОВ ACECOIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{rating_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🎮 Играй, получай XP и поднимайся в рейтинге!",
        parse_mode="HTML",
    )
