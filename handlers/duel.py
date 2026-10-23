import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from core.database import (
    get_balance,
    get_user_by_username,
    remove_money,
    change_balance,
    record_game,
)

from games.duel import (
    DUEL_TIMEOUT,
    STARTING_HP,
    create_duel,
    get_duel,
    get_player_duel,
    accept_duel,
    start_battle,
    submit_action,
    finish_battle,
    cancel_duel,
    expire_duel,
    remove_duel,
)

from games.treasure import (
    get_game as get_treasure_game,
    get_bet as get_treasure_bet,
    end_game as end_treasure_game,
    delete_game as delete_treasure_game,
)

from games.blackjack import (
    get_game as get_blackjack_game,
    finish_game as finish_blackjack_game,
)


WIN_XP = 5
LOSS_XP = 2
DRAW_XP = 3


def _safe_name(name):
    name = str(name or "").strip()
    return name[:40] if name else "Игрок"


def _get_display_name(user):
    if user.username:
        return f"@{user.username}"
    return _safe_name(user.full_name)


def _name(duel, user_id):
    names = duel.get("player_names", {})
    return names.get(user_id, f"Игрок {user_id}")


def challenge_keyboard(duel_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚔️ Принять",
                callback_data=f"duel_accept_{duel_id}",
            ),
            InlineKeyboardButton(
                "❌ Отклонить",
                callback_data=f"duel_decline_{duel_id}",
            ),
        ]
    ])


def battle_keyboard(duel_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔫 Выстрелить",
                callback_data=f"duel_action_{duel_id}_shoot",
            ),
            InlineKeyboardButton(
                "🎯 Прицелиться",
                callback_data=f"duel_action_{duel_id}_aim",
            ),
        ],
        [
            InlineKeyboardButton(
                "💨 Сбить прицел",
                callback_data=f"duel_action_{duel_id}_disrupt",
            ),
        ],
    ])


def _hearts(hp):
    hp = max(0, min(STARTING_HP, hp))
    return "❤️" * hp + "🖤" * (STARTING_HP - hp)


def _battle_text(duel, events=None, waiting_text=None):
    challenger_id = duel["challenger_id"]
    opponent_id = duel["opponent_id"]
    hp = duel.get("hp", {})

    challenger_name = _name(duel, challenger_id)
    opponent_name = _name(duel, opponent_id)

    lines = [
        "⚔️ ПЕРЕСТРЕЛКА ACECOIN",
        "",
        f"🔵 {challenger_name}: {_hearts(hp.get(challenger_id, STARTING_HP))}",
        f"🔴 {opponent_name}: {_hearts(hp.get(opponent_id, STARTING_HP))}",
        "",
        f"🎲 Раунд: {duel.get('round', 1)}",
    ]

    if events:
        lines.extend(["", *events])

    if waiting_text:
        lines.extend(["", waiting_text])
    elif duel.get("status") == "active":
        lines.extend([
            "",
            "Выбери действие. Выборы игроков скрыты "
            "до завершения раунда.",
        ])

    return "\n".join(lines)


async def cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Отменяет активные игры и ожидающий вызов на дуэль."""

    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    # 1. Отмена игры «Сокровища»

    treasure_game = get_treasure_game(user.id)

    if treasure_game and not treasure_game.get("finished", False):
        bet = get_treasure_bet(user.id)

        if bet <= 0:
            await message.reply_text(
                "❌ Не удалось определить ставку. "
                "Игра не отменена."
            )
            return

        end_treasure_game(user.id)
        delete_treasure_game(user.id)
        change_balance(user.id, bet)

        await message.reply_text(
            "❌ <b>ИГРА «СОКРОВИЩА» ОТМЕНЕНА</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Возвращённая ставка: <b>${bet:,}</b>\n"
            f"👛 Текущий баланс: <b>${get_balance(user.id):,}</b>\n\n"
            "Выигрыш и опыт за отменённую игру не начисляются.\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
        )
        return

    # 2. Отмена незавершённого блэкджека

    blackjack_game = get_blackjack_game(user.id)

    if blackjack_game and not blackjack_game.get("finished", False):
        bet = blackjack_game.get("bet", 0)

        if bet <= 0:
            await message.reply_text(
                "❌ Не удалось определить ставку блэкджека. "
                "Игра не отменена."
            )
            return

        if not finish_blackjack_game(user.id):
            await message.reply_text(
                "❌ Не удалось отменить партию. "
                "Попробуй ещё раз."
            )
            return

        change_balance(user.id, bet)

        await message.reply_text(
            "❌ <b>БЛЭКДЖЕК ОТМЕНЁН</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Возвращённая ставка: <b>${bet:,}</b>\n"
            f"👛 Текущий баланс: <b>${get_balance(user.id):,}</b>\n\n"
            "Партия отменена. Выигрыш и опыт не начисляются.\n"
            "━━━━━━━━━━━━━━━━━━",
            parse_mode="HTML",
        )
        return

    # 3. Отмена ожидающего вызова на дуэль

    duel = get_player_duel(user.id)

    if not duel:
        if treasure_game and treasure_game.get("finished", False):
            await message.reply_text(
                "ℹ️ Игра «Сокровища» уже завершена.\n"
                "Ставка повторно не возвращается."
            )
        else:
            await message.reply_text(
                "ℹ️ У тебя нет активной игры, "
                "которую можно отменить, или ожидающего вызова на дуэль.\n\n"
                "Слоты и рулетка рассчитываются сразу после запуска."
            )
        return

    status = duel.get("status")

    if status == "pending":
        if user.id != duel["challenger_id"]:
            await message.reply_text(
                "❌ Ты не создавал этот вызов.\n"
                "Если не хочешь участвовать, нажми кнопку "
                "«❌ Отклонить» под сообщением с вызовом."
            )
            return

        cancelled, result_status = cancel_duel(
            duel["id"],
            user.id,
        )

        if result_status != "success" or not cancelled:
            await message.reply_text(
                "❌ Не удалось отменить вызов. "
                "Возможно, соперник уже его принял."
            )
            return

        await message.reply_text(
            "❌ Вызов на перестрелку отменён.\n"
            "💰 Ставки не списывались, баланс не изменён."
        )
        return

    if status in ("accepted", "active"):
        await message.reply_text(
            "❌ Эту дуэль уже приняли.\n"
            "Отменить её командой /accancel нельзя, "
            "возврат ставки не выполнен."
        )
        return

    await message.reply_text(
        "ℹ️ Эта дуэль уже завершена или недоступна."
    )


async def duel_timeout(bot, duel_id, chat_id, message_id):
    await asyncio.sleep(DUEL_TIMEOUT)

    expired = expire_duel(duel_id)
    if not expired:
        return

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=(
                "⌛ Время вышло. Дуэль отменена, "
                "ставки не списывались."
            ),
        )
    except Exception:
        pass


async def duel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if not message or not user:
        return

    reply = message.reply_to_message

    if reply and len(context.args) == 1:
        target = reply.from_user

        if not target or target.is_bot:
            await message.reply_text(
                "❌ Не удалось определить соперника."
            )
            return

        opponent_id = target.id
        opponent_display_name = _get_display_name(target)

    elif len(context.args) == 2:
        username = context.args[0].lstrip("@").strip()

        if not username:
            await message.reply_text(
                "❌ Укажи юзернейм соперника."
            )
            return

        if user.username and username.lower() == user.username.lower():
            await message.reply_text(
                "❌ Нельзя вызвать самого себя."
            )
            return

        opponent = get_user_by_username(username)

        if not opponent:
            await message.reply_text(
                "❌ Игрок не найден. Он должен запустить бота "
                "командой /acstart."
            )
            return

        opponent_id = opponent["user_id"]
        opponent_username = opponent["username"]

        if opponent_username and opponent_username.lower() != "unknown":
            opponent_display_name = f"@{opponent_username}"
        else:
            opponent_display_name = f"Игрок {opponent_id}"

    else:
        await message.reply_text(
            "⚔️ Дуэль по юзернейму:\n"
            "/acduel @username 500\n\n"
            "⚔️ Дуэль ответом на сообщение:\n"
            "Ответь на сообщение игрока командой /acduel 500"
        )
        return

    if opponent_id == user.id:
        await message.reply_text(
            "❌ Нельзя вызвать самого себя."
        )
        return

    try:
        bet = int(context.args[-1])
    except (ValueError, IndexError):
        await message.reply_text(
            "❌ Ставка должна быть целым числом."
        )
        return

    if bet <= 0:
        await message.reply_text(
            "❌ Ставка должна быть больше нуля."
        )
        return

    if get_balance(user.id) < bet:
        await message.reply_text(
            "❌ У тебя недостаточно денег."
        )
        return

    if get_balance(opponent_id) < bet:
        await message.reply_text(
            "❌ У соперника недостаточно денег."
        )
        return

    challenger_name = _get_display_name(user)

    duel, status = create_duel(
        user.id,
        opponent_id,
        bet,
        challenger_name=challenger_name,
        opponent_name=opponent_display_name,
    )

    if status != "success" or not duel:
        errors = {
            "challenger_busy": "❌ У тебя уже есть активная дуэль.",
            "opponent_busy": "❌ У соперника уже есть активная дуэль.",
            "same_player": "❌ Нельзя вызвать самого себя.",
            "invalid_bet": "❌ Некорректная ставка.",
        }

        await message.reply_text(
            errors.get(status, "❌ Не удалось создать дуэль.")
        )
        return

    duel_id = duel["id"]

    text = (
        "⚔️ ВЫЗОВ НА ПЕРЕСТРЕЛКУ!\n\n"
        f"👤 Инициатор: {challenger_name}\n"
        f"🎯 Соперник: {opponent_display_name}\n"
        f"💰 Ставка каждого: ${bet:,}\n"
        f"🏆 Приз победителю: ${bet * 2:,}\n\n"
        f"⏳ На принятие: {DUEL_TIMEOUT} секунд.\n"
        "Ставки спишутся только после принятия.\n\n"
        "Чтобы отменить свой вызов, используй /accancel."
    )

    try:
        sent = await message.reply_text(
            text,
            reply_markup=challenge_keyboard(duel_id),
        )
    except Exception:
        remove_duel(duel_id)
        raise

    asyncio.create_task(
        duel_timeout(
            context.bot,
            duel_id,
            sent.chat_id,
            sent.message_id,
        )
    )


async def duel_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""
    parts = data.split("_", 3)

    if len(parts) < 3:
        await query.answer(
            "Некорректная кнопка.",
            show_alert=True,
        )
        return

    action = parts[1]
    duel_id = parts[2]
    user_id = query.from_user.id

    duel = get_duel(duel_id)

    if not duel:
        await query.answer(
            "Дуэль уже завершена или отменена.",
            show_alert=True,
        )
        return

    if user_id not in (
        duel["challenger_id"],
        duel["opponent_id"],
    ):
        await query.answer(
            "Ты не участник этой дуэли.",
            show_alert=True,
        )
        return

    if action == "decline":
        if user_id != duel["opponent_id"]:
            await query.answer(
                "Отклонить вызов может вызванный игрок.",
                show_alert=True,
            )
            return

        _, status = cancel_duel(
            duel_id,
            duel["challenger_id"],
        )

        if status != "success":
            await query.answer(
                "Дуэль уже нельзя отменить.",
                show_alert=True,
            )
            return

        await query.answer("Дуэль отклонена.")
        await query.edit_message_text(
            "❌ Дуэль отклонена. Деньги не списывались."
        )
        return

    if action == "accept":
        if user_id != duel["opponent_id"]:
            await query.answer(
                "Принять вызов может только соперник.",
                show_alert=True,
            )
            return

        bet = duel["bet"]
        challenger_id = duel["challenger_id"]
        opponent_id = duel["opponent_id"]

        if get_balance(challenger_id) < bet:
            remove_duel(duel_id)
            await query.answer(
                "У инициатора недостаточно денег.",
                show_alert=True,
            )
            await query.edit_message_text(
                "❌ Дуэль отменена: у инициатора "
                "недостаточно денег."
            )
            return

        if get_balance(opponent_id) < bet:
            remove_duel(duel_id)
            await query.answer(
                "У тебя недостаточно денег.",
                show_alert=True,
            )
            await query.edit_message_text(
                "❌ Дуэль отменена: у соперника "
                "недостаточно денег."
            )
            return

        accepted, status = accept_duel(
            duel_id,
            opponent_id,
        )

        if not accepted:
            await query.answer(
                "Дуэль уже недоступна или время истекло.",
                show_alert=True,
            )
            return

        if not remove_money(challenger_id, bet):
            remove_duel(duel_id)
            await query.answer(
                "Не удалось списать ставку инициатора.",
                show_alert=True,
            )
            await query.edit_message_text(
                "❌ Дуэль отменена. Ставки не списаны."
            )
            return

        if not remove_money(opponent_id, bet):
            change_balance(challenger_id, bet)
            remove_duel(duel_id)
            await query.answer(
                "Не удалось списать твою ставку.",
                show_alert=True,
            )
            await query.edit_message_text(
                "❌ Дуэль отменена. Деньги возвращены."
            )
            return

        battle = start_battle(duel_id)

        if not battle:
            change_balance(challenger_id, bet)
            change_balance(opponent_id, bet)
            remove_duel(duel_id)
            await query.answer(
                "Не удалось запустить бой. Ставки возвращены.",
                show_alert=True,
            )
            await query.edit_message_text(
                "❌ Бой не запустился. Обе ставки возвращены."
            )
            return

        await query.answer("Перестрелка началась!")
        await query.edit_message_text(
            _battle_text(battle),
            reply_markup=battle_keyboard(duel_id),
        )
        return

    if action != "action" or len(parts) != 4:
        await query.answer(
            "Неизвестное действие.",
            show_alert=True,
        )
        return

    chosen_action = parts[3]

    labels = {
        "shoot": "🔫 Выстрел",
        "aim": "🎯 Прицеливание",
        "disrupt": "💨 Сбивание прицела",
    }

    if chosen_action not in labels:
        await query.answer(
            "Неизвестное действие.",
            show_alert=True,
        )
        return

    snapshot, status, events = submit_action(
        duel_id,
        user_id,
        chosen_action,
    )

    if status == "not_found":
        await query.answer(
            "Дуэль не найдена.",
            show_alert=True,
        )
        return

    if status == "not_active":
        await query.answer(
            "Перестрелка не активна.",
            show_alert=True,
        )
        return

    if status == "not_participant":
        await query.answer(
            "Ты не участник этой дуэли.",
            show_alert=True,
        )
        return

    if status == "already_moved":
        await query.answer(
            "Ты уже выбрал действие в этом раунде.",
            show_alert=True,
        )
        return

    if status == "invalid_action":
        await query.answer(
            "Недопустимое действие.",
            show_alert=True,
        )
        return

    if status == "waiting":
        await query.answer(
            f"{labels[chosen_action]} выбран."
        )
        await query.edit_message_text(
            _battle_text(
                snapshot,
                waiting_text=(
                    "✅ Ход принят скрытно. "
                    "Ожидаем действие второго игрока..."
                ),
            ),
            reply_markup=battle_keyboard(duel_id),
        )
        return

    if status == "round_resolved":
        await query.answer("Раунд завершён!")
        await query.edit_message_text(
            _battle_text(snapshot, events=events),
            reply_markup=battle_keyboard(duel_id),
        )
        return

    if status == "finished":
        result = finish_battle(duel_id)

        if not result:
            await query.answer(
                "Не удалось получить результат боя.",
                show_alert=True,
            )
            return

        winner_id = result["winner_id"]
        challenger_id = result["challenger_id"]
        opponent_id = result["opponent_id"]
        bet = result["bet"]

        challenger_name = _name(result, challenger_id)
        opponent_name = _name(result, opponent_id)

        if winner_id is None:
            change_balance(challenger_id, bet)
            change_balance(opponent_id, bet)

            record_game(
                challenger_id,
                won=False,
                winnings=0,
                xp_reward=DRAW_XP,
                draw=True,
            )
            record_game(
                opponent_id,
                won=False,
                winnings=0,
                xp_reward=DRAW_XP,
                draw=True,
            )

            ending = (
                "🤝 НИЧЬЯ!\n\n"
                f"Обе ставки по ${bet:,} возвращены.\n"
                f"✨ Каждому начислено: +{DRAW_XP} XP"
            )
        else:
            prize = bet * 2
            change_balance(winner_id, prize)

            loser_id = (
                opponent_id
                if winner_id == challenger_id
                else challenger_id
            )

            record_game(
                winner_id,
                won=True,
                winnings=prize,
                xp_reward=WIN_XP,
            )
            record_game(
                loser_id,
                won=False,
                winnings=0,
                xp_reward=LOSS_XP,
            )

            winner_name = (
                challenger_name
                if winner_id == challenger_id
                else opponent_name
            )

            ending = (
                f"🏆 ПОБЕДИТЕЛЬ: {winner_name}!\n\n"
                f"💰 Выигрыш: ${prize:,}\n"
                f"✨ Победителю: +{WIN_XP} XP\n"
                f"✨ Проигравшему: +{LOSS_XP} XP"
            )

        final_text = _battle_text(result, events=events)
        final_text += "\n\n" + ending

        await query.answer("Перестрелка завершена!")
        await query.edit_message_text(final_text)
        return

    await query.answer(
        "Не удалось обработать действие.",
        show_alert=True,
    )