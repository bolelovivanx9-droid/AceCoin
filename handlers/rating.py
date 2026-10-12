
import html

from telegram import Update
from telegram.ext import ContextTypes

from core.database import add_user, get_top_users, get_user_rank


async def rating_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    add_user(user.id, user.username or "unknown")

    players = get_top_users(10)

    if not players:
        await message.reply_text(
            "🏆 <b>РЕЙТИНГ ACECOIN</b>\n\n"
            "Пока в рейтинге нет игроков.",
            parse_mode="HTML",
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = []

    for player in players:
        position = player["position"]
        medal = (
            medals[position - 1]
            if position <= 3
            else f"{position}."
        )

        username = player.get("username")
        if username and username.lower() != "unknown":
            name = f"@{html.escape(username.lstrip('@'))}"
        else:
            name = f"Игрок {player['user_id']}"

        lines.append(
            f"{medal} {player.get('rank_emoji', '⭐')} "
            f"<b>{player.get('level', 1)} ур.</b> — {name}\n"
            f"   ✨ Опыт: <b>{player.get('xp', 0):,} XP</b>"
            .replace(",", " ")
        )

    position = get_user_rank(user.id)

    own_position = (
        f"\n\n━━━━━━━━━━━━━━━━━━\n"
        f"👤 Твоё место: <b>#{position}</b>"
        if position is not None
        else ""
    )

    await message.reply_text(
        "🏆 <b>РЕЙТИНГ ИГРОКОВ ACECOIN</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines)
        + own_position
        + "\n\n━━━━━━━━━━━━━━━━━━\n"
        "🎮 Получай XP и поднимайся в рейтинге!",
        parse_mode="HTML",
    )
