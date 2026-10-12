
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.database import (
    get_balance,
    remove_money,
    change_balance,
    record_game,
)

from games.blackjack import (
    start_game,
    get_game,
    hit,
    stand,
    finish_game,
    format_cards,
    is_blackjack,
)


WIN_XP = 5
LOSS_XP = 2
DRAW_XP = 3


def blackjack_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ Ещё карту",
                callback_data="blackjack_hit",
            ),
            InlineKeyboardButton(
                "✋ Хватит",
                callback_data="blackjack_stand",
            ),
        ]
    ])


def render_game(game, reveal_dealer=False, message=None):
    player_cards = format_cards(game["player_cards"])
    player_score = game["player_score"]

    if reveal_dealer:
        dealer_cards = format_cards(game["dealer_cards"])
        dealer_score = game["dealer_score"]
    else:
        dealer_cards = format_cards(game["dealer_cards"][:1]) + " ❓"
        dealer_score = "?"

    text = (
        "🃏 **БЛЭКДЖЕК**\n\n"
        f"💰 Ставка: ${game['bet']}\n\n"
        f"👤 Твои карты: {player_cards}\n"
        f"Сумма: {player_score}\n\n"
        f"🎩 Карты дилера: {dealer_cards}\n"
        f"Сумма: {dealer_score}"
    )

    if message:
        text += f"\n\n{message}"

    return text


async def blackjack_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    if not context.args:
        await message.reply_text(
            "🃏 Чтобы сыграть, укажи ставку:\n"
            "/blackjack 100"
        )
        return

    try:
        bet = int(context.args[0])
    except (ValueError, TypeError):
        await message.reply_text(
            "❌ Ставка должна быть целым числом."
        )
        return

    if bet <= 0:
        await message.reply_text(
            "❌ Ставка должна быть больше нуля."
        )
        return

    if get_game(user.id):
        await message.reply_text(
            "⚠️ У тебя уже идёт партия в блэкджек. "
            "Заверши её перед новой."
        )
        return

    balance = get_balance(user.id)

    if balance < bet:
        await message.reply_text(
            "❌ Недостаточно средств.\n"
            f"💰 Твой баланс: ${balance}"
        )
        return

    if not remove_money(user.id, bet):
        await message.reply_text(
            "❌ Не удалось списать ставку. "
            "Проверь баланс и попробуй ещё раз."
        )
        return

    try:
        game = start_game(user.id, bet)
    except Exception:
        change_balance(user.id, bet)
        raise

    if game is None:
        change_balance(user.id, bet)
        await message.reply_text(
            "⚠️ У тебя уже идёт другая партия. "
            "Ставка возвращена."
        )
        return

    player_natural = is_blackjack(game["player_cards"])
    dealer_natural = is_blackjack(game["dealer_cards"])

    if player_natural or dealer_natural:
        if player_natural and dealer_natural:
            change_balance(user.id, bet)
            record_game(
                user.id,
                won=False,
                winnings=0,
                xp_reward=DRAW_XP,
                draw=True,
            )
            finish_game(user.id)

            await message.reply_text(
                render_game(
                    game,
                    reveal_dealer=True,
                    message=(
                        "🤝 У обоих блэкджек! "
                        f"Ставка возвращена. +{DRAW_XP} XP"
                    ),
                ),
                parse_mode="Markdown",
            )
            return

        if player_natural:
            payout = bet * 5 // 2
            change_balance(user.id, payout)
            record_game(
                user.id,
                won=True,
                winnings=payout,
                xp_reward=WIN_XP,
            )
            finish_game(user.id)

            await message.reply_text(
                render_game(
                    game,
                    reveal_dealer=True,
                    message=(
                        f"🎉 БЛЭКДЖЕК! "
                        f"Тебе выплачено ${payout}.\n"
                        f"✨ Получено: +{WIN_XP} XP"
                    ),
                ),
                parse_mode="Markdown",
            )
            return

        finish_game(user.id)
        record_game(
            user.id,
            won=False,
            winnings=0,
            xp_reward=LOSS_XP,
        )

        await message.reply_text(
            render_game(
                game,
                reveal_dealer=True,
                message=(
                    "😈 У дилера блэкджек. "
                    f"Ты проиграл ставку.\n"
                    f"✨ Получено: +{LOSS_XP} XP"
                ),
            ),
            parse_mode="Markdown",
        )
        return

    await message.reply_text(
        render_game(game),
        reply_markup=blackjack_keyboard(),
        parse_mode="Markdown",
    )


async def blackjack_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if not query:
        return

    await query.answer()

    user_id = query.from_user.id
    action = query.data

    game = get_game(user_id)

    if not game:
        await query.edit_message_text(
            "⚠️ Активная партия не найдена. "
            "Начни новую командой /blackjack."
        )
        return

    if action == "blackjack_hit":
        game = hit(user_id)

        if not game:
            await query.edit_message_text(
                "⚠️ Эта партия уже завершена."
            )
            return

        if game["player_score"] > 21:
            finish_game(user_id)
            record_game(
                user_id,
                won=False,
                winnings=0,
                xp_reward=LOSS_XP,
            )

            await query.edit_message_text(
                render_game(
                    game,
                    reveal_dealer=True,
                    message=(
                        "💥 Перебор! Ты проиграл ставку.\n"
                        f"✨ Получено: +{LOSS_XP} XP"
                    ),
                ),
                parse_mode="Markdown",
            )
            return

        await query.edit_message_text(
            render_game(game),
            reply_markup=blackjack_keyboard(),
            parse_mode="Markdown",
        )
        return

    if action == "blackjack_stand":
        game = stand(user_id)

        if not game:
            await query.edit_message_text(
                "⚠️ Эта партия уже завершена."
            )
            return

        result = game.get("result")

        if result == "win":
            payout = game["bet"] * 2
            change_balance(user_id, payout)
            record_game(
                user_id,
                won=True,
                winnings=payout,
                xp_reward=WIN_XP,
            )
            message = (
                f"🎉 Ты победил! Выплата: ${payout}.\n"
                f"✨ Получено: +{WIN_XP} XP"
            )

        elif result == "draw":
            change_balance(user_id, game["bet"])
            record_game(
                user_id,
                won=False,
                winnings=0,
                xp_reward=DRAW_XP,
                draw=True,
            )
            message = (
                f"🤝 Ничья! Ставка ${game['bet']} возвращена.\n"
                f"✨ Получено: +{DRAW_XP} XP"
            )

        else:
            record_game(
                user_id,
                won=False,
                winnings=0,
                xp_reward=LOSS_XP,
            )
            message = (
                "😈 Дилер победил. Ты проиграл ставку.\n"
                f"✨ Получено: +{LOSS_XP} XP"
            )

        finish_game(user_id)

        await query.edit_message_text(
            render_game(
                game,
                reveal_dealer=True,
                message=message,
            ),
            parse_mode="Markdown",
        )
