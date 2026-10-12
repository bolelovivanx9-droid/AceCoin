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
        "<code>/treasure 100</code> — начать игру со ставкой 100 $\n\n"
        "🎰 <b>Слоты</b>\n"
        "<code>/slots 100</code> — запустить слоты со ставкой 100 $\n\n"
        "🎡 <b>Рулетка</b>\n"
        "<code>/roulette</code> — открыть рулетку\n\n"
        "🃏 <b>Блэкджек</b>\n"
        "<code>/blackjack 100</code> — начать игру со ставкой 100 $\n\n"
        "⚔️ <b>Дуэли</b>\n"
        "<code>/duel</code> — вызвать игрока на дуэль\n"
        "<code>/cancel</code> — отменить ожидающий вызов\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>ЭКОНОМИКА</b>\n\n"
        "🪙 <code>/balance</code> — посмотреть баланс\n"
        "💸 <code>/pay @username 500</code> — перевести 500 $\n"
        "💸 Ответом на сообщение: <code>/pay 500</code>\n"
        "🎁 Ежедневный бонус — через главное меню\n"
        "🏦 Банк и кредиты — раздел «Банк» в меню\n"
        "📜 История переводов — кнопка в главном меню\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🎁 <b>ПРОМОКОДЫ И ДОСТИЖЕНИЯ</b>\n\n"
        "🎟️ <code>/promo КОД</code> — активировать промокод\n"
        "🛠️ <code>/createpromo</code> — создать промокод "
        "(если есть права)\n"
        "🏅 <code>/achievements</code> — посмотреть достижения\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>ПРОФИЛЬ</b>\n\n"
        "👤 <code>/profile</code> — открыть свой профиль\n"
        "🔎 <code>/profile @username</code> — профиль игрока\n"
        "💬 Можно ответить на сообщение игрока командой "
        "<code>/profile</code>, чтобы открыть его профиль\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>СТАТИСТИКА</b>\n\n"
        "<code>/stats</code> — посмотреть свою статистику:\n"
        "⭐ XP и уровень\n"
        "💎 Ранг и опыт до следующего уровня\n"
        "🏆 Победы и 💥 поражения\n"
        "🎮 Количество завершённых игр\n"
        "💰 Общий выигрыш\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🏆 <b>ТОП ИГРОКОВ</b>\n\n"
        "<code>/top</code> — открыть рейтинг лучших игроков по XP\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>ОСНОВНЫЕ КОМАНДЫ</b>\n\n"
        "🚀 <code>/start</code> — запустить бота\n"
        "📖 <code>/help</code> — открыть справочник\n"
        "💰 <code>/addmoney</code> — административная команда\n\n"

        "⚠️ Для использования некоторых команд необходимо "
        "зарегистрироваться в AceCoin Casino.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔥 <i>Удачи в AceCoin Casino!</i>"
    )

    await message.reply_text(
        help_text,
        parse_mode="HTML",
    )