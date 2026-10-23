from telegram import Update
from telegram.ext import ContextTypes


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message

    if not message:
        return

    help_text = (
        "🎰 <b>ACECOIN CASINO — СПРАВОЧНИК</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "🎮 <b>ИГРЫ</b>\n\n"
        "💎 <b>Сокровища</b>\n"
        "<code>/actreasure 100</code> — начать игру со ставкой 100 $\n\n"
        "🎰 <b>Слоты</b>\n"
        "<code>/acslots 100</code> — запустить слоты со ставкой 100 $\n\n"
        "🎡 <b>Рулетка</b>\n"
        "<code>/acroulette</code> — открыть рулетку\n\n"
        "🃏 <b>Блэкджек</b>\n"
        "<code>/acblackjack 100</code> — начать игру со ставкой 100 $\n\n"
        "⚔️ <b>Дуэли</b>\n"
        "<code>/acduel</code> — вызвать игрока на дуэль\n"
        "<code>/accancel</code> — отменить ожидающий вызов\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>ЭКОНОМИКА</b>\n\n"
        "🪙 <code>/acbalance</code> — посмотреть баланс\n"
        "💸 <code>/acpay @username 500</code> — перевести 500 $\n"
        "💸 Ответом на сообщение: <code>/acpay 500</code>\n"
        "🎁 Ежедневный бонус — через главное меню\n"
        "📅 <code>/acdaily</code> — ежедневный бонус\n\n"

        "🕵️ <b>КРАЖА ДЕНЕГ</b>\n"
        "🥷 <code>/acsteal @username</code> — попытаться украсть деньги у игрока\n"
        "💬 Ответь на сообщение игрока командой <code>/acsteal</code>, "
        "чтобы попытаться украсть у него\n"
        "🎲 Шанс успеха — 15%\n"
        "⏳ Одна попытка раз в 24 часа\n"
        "💰 При успехе случайная сумма переводится с баланса цели на твой баланс\n\n"

        "🏦 <b>БАНК И КРЕДИТЫ</b>\n"
        "🏦 <code>/acbank</code> — открыть банк и посмотреть балансы\n"
        "💳 <code>/acloan</code> — посмотреть состояние кредита\n"
        "💸 <code>/actake_loan 5000</code> — взять кредит на 5000 $\n"
        "💰 <code>/acrepay_loan 1000</code> — погасить 1000 $ долга\n"
        "📜 <code>/actransfer_history</code> — последние 10 переводов\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🎁 <b>ПРОМОКОДЫ И ДОСТИЖЕНИЯ</b>\n\n"
        "🎟️ <code>/acpromo КОД</code> — активировать промокод\n"
        "🛠️ <code>/accreatepromo</code> — создать промокод "
        "(если есть права)\n"
        "🏅 <code>/acachievements</code> — посмотреть достижения\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>ПРОФИЛЬ</b>\n\n"
        "👤 <code>/acprofile</code> — открыть свой профиль\n"
        "🔎 <code>/acprofile @username</code> — профиль игрока\n"
        "💬 Можно ответить на сообщение игрока командой "
        "<code>/acprofile</code>, чтобы открыть его профиль\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>СТАТИСТИКА</b>\n\n"
        "<code>/acstats</code> — посмотреть свою статистику:\n"
        "⭐ XP и уровень\n"
        "💎 Ранг и опыт до следующего уровня\n"
        "🏆 Победы и 💥 поражения\n"
        "🎮 Количество завершённых игр\n"
        "💰 Общий выигрыш\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🏆 <b>ТОП ИГРОКОВ</b>\n\n"
        "<code>/actop</code> — открыть рейтинг лучших игроков по XP\n"
        "<code>/acrating</code> — открыть рейтинг игроков\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>ОСНОВНЫЕ КОМАНДЫ</b>\n\n"
        "🚀 <code>/acstart</code> — запустить бота\n"
        "📖 <code>/achelp</code> — открыть справочник\n"
        "📋 <code>/acmenu</code> — открыть главное меню\n"
        "💰 <code>/acaddmoney</code> — административная команда\n\n"

        "⚠️ Для использования некоторых команд необходимо "
        "зарегистрироваться в AceCoin Casino.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔥 <i>Удачи в AceCoin Casino!</i>"
    )

    await message.reply_text(
        help_text,
        parse_mode="HTML",
    )