from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from core.achievements import get_achievement_summary


async def achievements_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    achievements = get_achievement_summary(user.id)

    if not achievements:
        await message.reply_text(
            "❌ Не удалось загрузить достижения. "
            "Нажми /start и попробуй снова."
        )
        return

    unlocked_count = sum(
        item["unlocked"] for item in achievements
    )

    lines = []

    for item in achievements:
        if item["unlocked"]:
            status = "✅ Получено"
            date_text = ""

            if item["unlocked_at"]:
                try:
                    date_text = datetime.fromtimestamp(
                        item["unlocked_at"]
                    ).strftime("%d.%m.%Y")
                except (ValueError, TypeError, OSError):
                    pass

            if date_text:
                status += f" · {date_text}"
        else:
            status = (
                f"🔒 Прогресс: "
                f"{item['current']}/{item['target']}"
            )

        lines.append(
            f"{item['emoji']} <b>{item['name']}</b>\n"
            f"   {item['description']}\n"
            f"   ⭐ Награда: +{item['reward_xp']} XP\n"
            f"   {status}"
        )

    await message.reply_text(
        "🏅 <b>ТВОИ ДОСТИЖЕНИЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Открыто: "
        f"<b>{unlocked_count}/{len(achievements)}</b>\n\n"
        + "\n\n".join(lines)
        + "\n\n━━━━━━━━━━━━━━━━━━\n"
        "🎮 Играй и получай новые награды!",
        parse_mode="HTML",
    )