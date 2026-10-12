
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from core.quests import (
    get_daily_quests,
    claim_daily_quest,
)


def quests_keyboard(quests):
    rows = []

    for quest in quests:
        if quest["claimed"]:
            button = "✅ Награда получена"
        elif quest["completed"]:
            button = f"🎁 Забрать +{quest['reward_money']:,} $"
        else:
            continue

        rows.append(
            [
                InlineKeyboardButton(
                    f"{quest['name']} — {button}",
                    callback_data=f"quest_claim:{quest['id']}",
                )
            ]
        )

    return InlineKeyboardMarkup(rows) if rows else None


async def show_quests(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    quests = get_daily_quests(user.id)
    lines = []

    for quest in quests:
        status = (
            "✅ Награда получена"
            if quest["claimed"]
            else "🎁 Можно забрать награду"
            if quest["completed"]
            else "⏳ Выполняется"
        )

        lines.append(
            f"{quest['name']}\n"
            f"Прогресс: {quest['progress']}/{quest['target']}\n"
            f"Награда: {quest['reward_money']:,} $ "
            f"+ {quest['reward_xp']} XP\n"
            f"{status}"
        )

    await message.reply_text(
        "🏆 <b>ЕЖЕДНЕВНЫЕ КВЕСТЫ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines)
        + "\n\n━━━━━━━━━━━━━━━━━━\n"
        "Выполняй задания и забирай награды!",
        parse_mode="HTML",
        reply_markup=quests_keyboard(quests),
    )


async def quest_claim_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query or not query.from_user:
        return

    quest_id = query.data.partition(":")[2]

    success, result = claim_daily_quest(
        query.from_user.id,
        quest_id,
    )

    await query.answer(
        result,
        show_alert=not success,
    )

    if success and query.message:
        quests = get_daily_quests(query.from_user.id)
        lines = []

        for quest in quests:
            status = (
                "✅ Награда получена"
                if quest["claimed"]
                else "🎁 Можно забрать награду"
                if quest["completed"]
                else "⏳ Выполняется"
            )

            lines.append(
                f"{quest['name']}\n"
                f"Прогресс: {quest['progress']}/{quest['target']}\n"
                f"Награда: {quest['reward_money']:,} $ "
                f"+ {quest['reward_xp']} XP\n"
                f"{status}"
            )

        await query.edit_message_text(
            "🏆 <b>ЕЖЕДНЕВНЫЕ КВЕСТЫ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(lines)
            + "\n\n━━━━━━━━━━━━━━━━━━\n"
            + result,
            parse_mode="HTML",
            reply_markup=quests_keyboard(quests),
        )
