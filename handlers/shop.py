
import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from core.shop_database import (
    SHOP_ITEMS,
    CATEGORY_NAMES,
    XP_DAILY_PURCHASE_LIMIT,
    SECRET_CATEGORY,
    get_shop_catalog,
    get_inventory,
    get_equipped,
    get_relic_status,
    get_xp_daily_purchases,
    get_secret_shop_status,
    get_item_unlock_status,
    get_rare_history,
    purchase_item,
    equip_item,
)


logger = logging.getLogger(__name__)

CATEGORIES = [
    "boosters",
    "titles",
    "relics",
    SECRET_CATEGORY,
]

PAGE_SIZE = 6


def money(value):
    return f"{value:,}".replace(",", " ") + " $"


def secret_lock_text(status):
    if status["level"] < 5 and not status["via_achievement"]:
        return (
            "🔒 Секретный магазин закрыт.\n\n"
            "Открой его одним из двух способов:\n"
            "• достигни 5-го уровня;\n"
            "• получи достижение «Игрок» за 10 сыгранных игр."
        )

    return "🔒 Секретный магазин закрыт."


def item_requirement_text(item):
    """Возвращает описание требования к секретному предмету."""
    achievement = item.get("unlock_achievement")
    level = item.get("unlock_level")

    if achievement == "games_100":
        return "🔐 Требование: достижение «Ветеран» за 100 игр."

    if level:
        return f"🔐 Требование: {level}-й уровень."

    return "🔐 Требование: доступ к секретному магазину."


def shop_keyboard(category=None, page=0, user_id=None):
    keyboard = []

    if category is None:
        for key in CATEGORIES:
            if key == SECRET_CATEGORY and user_id is not None:
                status = get_secret_shop_status(user_id)

                if not status["unlocked"]:
                    continue

            keyboard.append([
                InlineKeyboardButton(
                    CATEGORY_NAMES[key],
                    callback_data=f"shop_cat:{key}",
                )
            ])

        keyboard.extend([
            [
                InlineKeyboardButton(
                    "🎒 Мой инвентарь",
                    callback_data="shop_inventory",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏆 Редкие находки",
                    callback_data="shop_rare",
                )
            ],
        ])

        return InlineKeyboardMarkup(keyboard)

    items = get_shop_catalog(category)
    start = page * PAGE_SIZE
    visible = items[start:start + PAGE_SIZE]

    for item in visible:
        keyboard.append([
            InlineKeyboardButton(
                f"{item['name']} — {money(item['price'])}",
                callback_data=f"shop_item:{item['id']}",
            )
        ])

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data=f"shop_page:{category}:{page - 1}",
            )
        )

    if start + PAGE_SIZE < len(items):
        navigation.append(
            InlineKeyboardButton(
                "Вперёд ➡️",
                callback_data=f"shop_page:{category}:{page + 1}",
            )
        )

    if navigation:
        keyboard.append(navigation)

    keyboard.append([
        InlineKeyboardButton(
            "↩️ Категории",
            callback_data="shop_home",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def item_keyboard(item_id, user_id, can_buy=True):
    item = SHOP_ITEMS[item_id]
    keyboard = []

    if can_buy:
        keyboard.append([
            InlineKeyboardButton(
                "🛒 Купить",
                callback_data=f"shop_buy:{item_id}",
            )
        ])

    keyboard.extend([
        [
            InlineKeyboardButton(
                "↩️ В каталог",
                callback_data=f"shop_cat:{item['category']}",
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Главное меню магазина",
                callback_data="shop_home",
            )
        ],
    ])

    return InlineKeyboardMarkup(keyboard)


async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_shop(update, context)


async def show_shop(update, context):
    user = update.effective_user
    user_id = user.id if user else None

    text = (
        "🛒 <b>МАГАЗИН ACECOIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Выбирай предметы для своего профиля.\n\n"
        "⭐ XP-бустеры — мгновенный опыт\n"
        "🏷️ Титулы — престиж и статус\n"
        "🏺 Реликвии — редкие коллекционные предметы\n"
        "🔐 Секретный магазин — особые предметы и условия\n\n"
        f"⭐ Каждый XP-бустер можно купить "
        f"до {XP_DAILY_PURCHASE_LIMIT} раз за сутки.\n\n"
        "⚖️ Предметы магазина не изменяют игровые шансы, "
        "множители и выплаты.\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text,
            reply_markup=shop_keyboard(user_id=user_id),
            parse_mode="HTML",
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text,
            reply_markup=shop_keyboard(user_id=user_id),
            parse_mode="HTML",
        )


async def show_category(query, category, page=0):
    if category not in CATEGORIES:
        await query.answer("Категория не найдена.", show_alert=True)
        return

    user_id = query.from_user.id

    if category == SECRET_CATEGORY:
        status = get_secret_shop_status(user_id)

        if not status["unlocked"]:
            await query.answer(
                secret_lock_text(status),
                show_alert=True,
            )
            return

    items = get_shop_catalog(category)

    if not items:
        await query.answer("В этой категории пока пусто.")
        return

    page = max(0, page)
    page_count = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)

    if page >= page_count:
        page = page_count - 1

    lines = [
        f"🛒 <b>{CATEGORY_NAMES[category]}</b>",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if category == SECRET_CATEGORY:
        status = get_secret_shop_status(user_id)
        lines.extend([
            "🗝️ <b>Секреты открываются не всем.</b>",
            f"Твой уровень: {status['level']}",
            "Условия открытия указаны у каждого предмета.",
            "",
        ])

    for item in items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]:
        lines.append(
            f"<b>{item['name']}</b>\n"
            f"💵 Цена: {money(item['price'])}\n"
            f"✨ Редкость: {item['rarity']}\n"
            f"<i>{item['description']}</i>\n"
        )

        if category == SECRET_CATEGORY:
            unlock = get_item_unlock_status(user_id, item["id"])

            if unlock["unlocked"]:
                lines.append("✅ Предмет доступен для покупки.\n")
            else:
                lines.append(f"{item_requirement_text(item)}\n")

        if item["kind"] == "xp":
            purchased = get_xp_daily_purchases(
                user_id,
                item["id"],
            )
            remaining = max(
                0,
                XP_DAILY_PURCHASE_LIMIT - purchased,
            )

            lines.append(
                f"📅 Покупок сегодня: {purchased}/"
                f"{XP_DAILY_PURCHASE_LIMIT}\n"
                f"🛒 Осталось сегодня: {remaining}\n"
            )

    if category == "relics":
        status = get_relic_status()

        if status and status["sold_out"]:
            lines.extend([
                "━━━━━━━━━━━━━━━━━━",
                "🔒 <b>Сердце AceCoin уже приобретено.</b>",
                f"Первый владелец ID: <code>{status['owner_id']}</code>",
            ])
        else:
            lines.extend([
                "━━━━━━━━━━━━━━━━━━",
                "👑 Реликвия доступна только в одном экземпляре.",
            ])

    await query.answer()
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=shop_keyboard(category, page, user_id),
        parse_mode="HTML",
    )


async def show_item(query, item_id):
    item = SHOP_ITEMS.get(item_id)

    if not item:
        await query.answer("Предмет не найден.", show_alert=True)
        return

    user_id = query.from_user.id
    unlock = get_item_unlock_status(user_id, item_id)
    can_buy = unlock["unlocked"]

    text = (
        f"🛍️ <b>{item['name']}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{item['description']}\n\n"
        f"💵 Цена: <b>{money(item['price'])}</b>\n"
        f"✨ Редкость: {item['rarity']}\n"
    )

    if item["category"] == SECRET_CATEGORY:
        text += f"\n{item_requirement_text(item)}\n"

    if not can_buy:
        text += f"\n{unlock['message']}\n"

    if item["kind"] == "xp":
        purchased = get_xp_daily_purchases(user_id, item_id)
        remaining = max(
            0,
            XP_DAILY_PURCHASE_LIMIT - purchased,
        )

        text += (
            f"\n⭐ Будет начислено: <b>{item['xp']} XP</b>\n"
            f"📅 Покупок сегодня: "
            f"<b>{purchased}/{XP_DAILY_PURCHASE_LIMIT}</b>\n"
            f"🛒 Осталось сегодня: <b>{remaining}</b>\n"
        )

        if remaining == 0:
            text += (
                "\n⏳ Дневной лимит исчерпан. "
                "Попробуй купить этот бустер завтра.\n"
            )

    if item["kind"] == "relic":
        status = get_relic_status()

        if status and status["sold_out"]:
            text += "\n🔒 Эта реликвия уже продана.\n"
            can_buy = False
        else:
            text += "\n👑 Единственный экземпляр на весь бот.\n"

    await query.answer()
    await query.edit_message_text(
        text,
        reply_markup=item_keyboard(item_id, user_id, can_buy),
        parse_mode="HTML",
    )


async def buy_item(query, user_id, item_id):
    item = SHOP_ITEMS.get(item_id)

    if not item:
        await query.answer("Предмет не найден.", show_alert=True)
        return

    success, code, details = purchase_item(user_id, item_id)

    if not success:
        messages = {
            "unknown_item": "Такого товара нет.",
            "user_not_found": "Сначала отправь /acstart.",
            "insufficient_funds": "Недостаточно средств!",
            "already_owned": "У тебя уже есть этот предмет.",
            "relic_sold": "Реликвия уже навсегда продана другому игроку.",
            "secret_locked": (
                "🔒 Секретный магазин закрыт. "
                "Нужен 5-й уровень или достижение «Игрок» за 10 игр."
            ),
            "item_locked": (
                details.get("message", "Сначала выполни условие открытия.")
                if details else "Сначала выполни условие открытия."
            ),
            "xp_daily_limit": (
                f"⏳ Ты уже купил этот XP-бустер "
                f"{XP_DAILY_PURCHASE_LIMIT} раза за сегодня! "
                "Попробуй завтра."
            ),
        }

        await query.answer(
            messages.get(code, "Не удалось совершить покупку."),
            show_alert=True,
        )
        return

    if code == "xp_granted":
        purchased_today = details.get("purchased_today", 0)
        daily_limit = details.get(
            "daily_limit",
            XP_DAILY_PURCHASE_LIMIT,
        )
        remaining_today = details.get(
            "remaining_today",
            max(0, daily_limit - purchased_today),
        )

        text = (
            "⭐ <b>XP-БУСТЕР АКТИВИРОВАН!</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"Предмет: <b>{item['name']}</b>\n"
            f"Начислено: <b>+{details['xp']} XP</b>\n"
            f"Потрачено: {money(item['price'])}\n"
            f"Остаток: {money(details['balance'])}\n\n"
            f"📅 Покупок сегодня: "
            f"<b>{purchased_today}/{daily_limit}</b>\n"
            f"🛒 Осталось сегодня: <b>{remaining_today}</b>"
        )

        if remaining_today == 0:
            text += "\n\n⏳ Лимит этого бустера на сегодня исчерпан."
    else:
        text = (
            "✅ <b>ПОКУПКА УСПЕШНА!</b>\n\n"
            f"Предмет: <b>{item['name']}</b>\n"
            f"Потрачено: {money(item['price'])}\n"
            f"Остаток: {money(details['balance'])}\n\n"
            "Предмет сохранён в твоём инвентаре."
        )

        if item["kind"] == "relic":
            text += (
                "\n\n👑 <b>Ты стал единственным владельцем "
                "Сердца AceCoin!</b>"
            )

    await query.answer("Покупка завершена!")
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎒 Инвентарь",
                    callback_data="shop_inventory",
                )
            ],
            [
                InlineKeyboardButton(
                    "🛒 В магазин",
                    callback_data="shop_home",
                )
            ],
        ]),
        parse_mode="HTML",
    )


async def show_inventory(query, user_id):
    inventory = get_inventory(user_id)
    equipped = get_equipped(user_id)

    lines = [
        "🎒 <b>МОЙ ИНВЕНТАРЬ</b>",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if not inventory:
        lines.append("Пока у тебя нет предметов.")
    else:
        for item in inventory:
            marker = ""

            if item["id"] == equipped["title_id"]:
                marker = " 🟢 <i>Активен</i>"

            lines.append(f"• <b>{item['name']}</b>{marker}")

    keyboard = []

    for item in inventory:
        if item["kind"] in ("title", "relic"):
            keyboard.append([
                InlineKeyboardButton(
                    f"Выбрать: {item['name']}",
                    callback_data=f"shop_equip:{item['id']}",
                )
            ])

    keyboard.append([
        InlineKeyboardButton(
            "🛒 Вернуться в магазин",
            callback_data="shop_home",
        )
    ])

    await query.answer()
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def show_rare_history(query):
    history = get_rare_history(limit=15)

    lines = [
        "🏆 <b>ИСТОРИЯ РЕДКИХ НАХОДОК</b>",
        "━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if not history:
        lines.append("Редких предметов пока никто не приобретал.")
    else:
        for entry in history:
            item = SHOP_ITEMS.get(entry["item_id"])
            name = item["name"] if item else entry["item_id"]

            lines.append(
                f"• <b>{name}</b>\n"
                f"  Игрок ID: <code>{entry['user_id']}</code>\n"
                f"  Событие: {entry['event']}\n"
            )

    status = get_relic_status()

    if status and status["sold_out"]:
        lines.extend([
            "━━━━━━━━━━━━━━━━━━",
            "👑 <b>Сердце AceCoin</b>",
            f"Владелец: <code>{status['owner_id']}</code>",
        ])

    await query.answer()
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "↩️ В магазин",
                callback_data="shop_home",
            )
        ]]),
        parse_mode="HTML",
    )


async def equip_owned_item(query, user_id, item_id):
    success, code = equip_item(user_id, item_id)

    if not success:
        await query.answer(
            "Этот предмет не найден, не принадлежит тебе "
            "или его нельзя экипировать.",
            show_alert=True,
        )
        return

    item = SHOP_ITEMS.get(item_id)

    if not item:
        await query.answer("Предмет не найден.", show_alert=True)
        return

    await query.answer("Предмет выбран!")
    await query.edit_message_text(
        f"✅ Ты выбрал: <b>{item['name']}</b>\n\n"
        "Изменение сохранено.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🎒 В инвентарь",
                    callback_data="shop_inventory",
                )
            ],
            [
                InlineKeyboardButton(
                    "🛒 В магазин",
                    callback_data="shop_home",
                )
            ],
        ]),
        parse_mode="HTML",
    )


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    user_id = query.from_user.id
    data = query.data or ""

    try:
        if data == "shop_home":
            await show_shop(update, context)

        elif data == "shop_inventory":
            await show_inventory(query, user_id)

        elif data == "shop_rare":
            await show_rare_history(query)

        elif data.startswith("shop_cat:"):
            category = data.split(":", 1)[1]
            await show_category(query, category)

        elif data.startswith("shop_page:"):
            _, category, page = data.split(":", 2)
            await show_category(query, category, int(page))

        elif data.startswith("shop_item:"):
            item_id = data.split(":", 1)[1]
            await show_item(query, item_id)

        elif data.startswith("shop_buy:"):
            item_id = data.split(":", 1)[1]
            await buy_item(query, user_id, item_id)

        elif data.startswith("shop_equip:"):
            item_id = data.split(":", 1)[1]
            await equip_owned_item(query, user_id, item_id)

        else:
            await query.answer("Неизвестное действие.")

    except Exception:
        logger.exception("Ошибка обработчика магазина")

        try:
            await query.answer(
                "Произошла ошибка. Попробуй ещё раз.",
                show_alert=True,
            )
        except Exception:
            pass
