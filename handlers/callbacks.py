
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from games.treasure import (
    get_cell,
    get_bet,
    get_game,
    get_opened,
    get_stats,
    get_multiplier,
    calculate_win,
    end_game,
    GRID_SIZE,
    TREASURES_COUNT,
    BOMBS_TO_LOSE,
)
from services.casino import give_win
from core.database import record_game


# Сбалансированная награда за завершённую игру.
WIN_BASE_XP = 5
LOSS_BASE_XP = 2
DRAW_BASE_XP = 3
XP_PER_TREASURE = 1
MAX_TREASURE_BONUS_XP = 5


def calculate_game_xp(treasures: int, won: bool = False) -> int:
    """Рассчитывает XP за завершённую игру."""

    treasure_bonus = min(
        max(treasures, 0),
        MAX_TREASURE_BONUS_XP,
    )

    if won:
        return WIN_BASE_XP + treasure_bonus

    return LOSS_BASE_XP + treasure_bonus


def build_treasure_keyboard(user_id: int):
    """Строит поле с открытыми клетками и кнопкой выигрыша."""

    game = get_game(user_id)

    if not game:
        return None

    opened = set(get_opened(user_id))
    keyboard = []

    for row in range(GRID_SIZE):
        buttons = []

        for col in range(GRID_SIZE):
            number = row * GRID_SIZE + col

            if number in opened:
                emoji = game["cells"][number]
                callback_data = "treasure_opened"
            else:
                emoji = "⬜"
                callback_data = f"treasure_{row}_{col}"

            buttons.append(
                InlineKeyboardButton(
                    emoji,
                    callback_data=callback_data,
                )
            )

        keyboard.append(buttons)

    keyboard.append([
        InlineKeyboardButton(
            "💵 Забрать выигрыш",
            callback_data="treasure_cashout",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


def build_revealed_keyboard(user_id: int):
    """Показывает всё поле после завершения игры."""

    game = get_game(user_id)

    if not game:
        return None

    keyboard = []

    for row in range(GRID_SIZE):
        buttons = []

        for col in range(GRID_SIZE):
            number = row * GRID_SIZE + col

            buttons.append(
                InlineKeyboardButton(
                    game["cells"][number],
                    callback_data="treasure_opened",
                )
            )

        keyboard.append(buttons)

    return InlineKeyboardMarkup(keyboard)


def build_cashout_keyboard(user_id: int):
    """Оставляет открытые клетки видимыми после забора выигрыша."""

    game = get_game(user_id)

    if not game:
        return None

    opened = set(get_opened(user_id))
    keyboard = []

    for row in range(GRID_SIZE):
        buttons = []

        for col in range(GRID_SIZE):
            number = row * GRID_SIZE + col

            if number in opened:
                emoji = game["cells"][number]
            else:
                emoji = "⬜"

            buttons.append(
                InlineKeyboardButton(
                    emoji,
                    callback_data="treasure_opened",
                )
            )

        keyboard.append(buttons)

    return InlineKeyboardMarkup(keyboard)


async def treasure_click(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""
    user_id = query.from_user.id

    print(
        f"[TREASURE] Получено нажатие: {data}",
        flush=True,
    )

    if data == "treasure_opened":
        await query.answer()
        return

    game = get_game(user_id)

    # ==========================================
    # ЗАБРАТЬ ВЫИГРЫШ
    # ==========================================

    if data == "treasure_cashout":
        if not game or game["finished"]:
            await query.answer(
                "Активная игра не найдена.",
                show_alert=True,
            )
            return

        treasures = game["treasures"]
        bet = get_bet(user_id)

        if bet <= 0:
            await query.answer(
                "Не удалось определить ставку.",
                show_alert=True,
            )
            return

        if treasures < 1:
            await query.answer(
                "Сначала найди хотя бы один мешочек! 💰",
                show_alert=True,
            )
            return

        multiplier = get_multiplier(treasures)
        win = calculate_win(bet, treasures)
        xp_reward = calculate_game_xp(treasures, won=True)

        # Закрываем игру до выплаты, чтобы повторно
        # забрать выигрыш из этой партии было нельзя.
        end_game(user_id)

        give_win(user_id, win)

        record_game(
            user_id=user_id,
            won=True,
            winnings=win,
            xp_reward=xp_reward,
        )

        await query.answer("Выигрыш забран! 💰")

        await query.edit_message_text(
            "💵 <b>ВЫИГРЫШ ЗАБРАН!</b>\n\n"
            f"💰 Найдено мешочков: {treasures}\n"
            f"💣 Попаданий на бомбы: "
            f"{game['bombs']}/{BOMBS_TO_LOSE}\n"
            f"🎯 Множитель: ×{multiplier:.2f}\n"
            f"💵 Выплата: +${win:,}\n"
            f"⭐ Получено опыта: +{xp_reward} XP\n\n"
            "🏆 Результат сохранён в статистике!",
            reply_markup=build_cashout_keyboard(user_id),
            parse_mode="HTML",
        )

        print(
            f"[TREASURE] Игрок {user_id} забрал "
            f"${win:,}, получил {xp_reward} XP, "
            f"множитель x{multiplier:.2f}",
            flush=True,
        )
        return

    if not data.startswith("treasure_"):
        await query.answer()
        return

    parts = data.split("_")

    if len(parts) != 3:
        await query.answer(
            "Некорректная клетка.",
            show_alert=True,
        )
        return

    try:
        row = int(parts[1])
        col = int(parts[2])
    except ValueError:
        await query.answer(
            "Некорректная клетка.",
            show_alert=True,
        )
        return

    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
        await query.answer(
            "Клетка вне поля.",
            show_alert=True,
        )
        return

    if not game or game["finished"]:
        await query.answer(
            "Игра завершена или не найдена.",
            show_alert=True,
        )
        return

    bet = get_bet(user_id)

    if bet <= 0:
        await query.answer(
            "Ставка не найдена.",
            show_alert=True,
        )
        return

    number = row * GRID_SIZE + col
    result = get_cell(user_id, number)

    if result == "opened":
        await query.answer(
            "Эта клетка уже открыта.",
            show_alert=True,
        )
        return

    if result is None:
        await query.answer(
            "Не удалось открыть клетку.",
            show_alert=True,
        )
        return

    await query.answer()

    stats = get_stats(user_id)
    game = get_game(user_id)

    if not stats or not game:
        await query.edit_message_text(
            "❌ Не удалось получить данные игры."
        )
        return

    print(
        f"[TREASURE] Игрок: {user_id}, "
        f"клетка: {row},{col}, результат: {result}",
        flush=True,
    )

    # ==========================================
    # БОМБА
    # ==========================================

    if result == "💣":
        if game["bombs"] >= BOMBS_TO_LOSE:
            treasures = stats["treasures"]
            xp_reward = calculate_game_xp(treasures, won=False)

            end_game(user_id)

            record_game(
                user_id=user_id,
                won=False,
                winnings=0,
                xp_reward=xp_reward,
            )

            await query.edit_message_text(
                "💥 <b>ТЫ ПОПАЛ НА ПОСЛЕДНЮЮ БОМБУ!</b>\n\n"
                f"💰 Найдено мешочков: {treasures}\n"
                f"💣 Бомб: {stats['bombs']}/{BOMBS_TO_LOSE}\n"
                f"❌ Потеряна ставка: ${bet:,}\n"
                f"⭐ Получено опыта: +{xp_reward} XP\n\n"
                "📊 Результат сохранён в статистике.",
                reply_markup=build_revealed_keyboard(user_id),
                parse_mode="HTML",
            )

            print(
                f"[TREASURE] Игрок {user_id} проиграл "
                f"${bet:,} и получил {xp_reward} XP",
                flush=True,
            )
            return

        multiplier = get_multiplier(stats["treasures"])
        possible_win = calculate_win(bet, stats["treasures"])

        await query.edit_message_text(
            "💣 Ты попал на бомбу, но игра продолжается!\n\n"
            f"💰 Найдено мешочков: {stats['treasures']}\n"
            f"💣 Бомб: {stats['bombs']}/{BOMBS_TO_LOSE}\n"
            f"🎯 Текущий множитель: ×{multiplier:.2f}\n"
            f"💵 Можно забрать: ${possible_win:,}\n\n"
            "Продолжай искать или забери выигрыш кнопкой ниже.",
            reply_markup=build_treasure_keyboard(user_id),
        )
        return

    # ==========================================
    # СОКРОВИЩЕ
    # ==========================================

    if result == "💰":
        treasures = stats["treasures"]
        multiplier = get_multiplier(treasures)
        possible_win = calculate_win(bet, treasures)

        # Найдены все сокровища — автоматическая победа.
        if treasures >= TREASURES_COUNT:
            xp_reward = calculate_game_xp(treasures, won=True)

            end_game(user_id)

            give_win(user_id, possible_win)

            record_game(
                user_id=user_id,
                won=True,
                winnings=possible_win,
                xp_reward=xp_reward,
            )

            await query.edit_message_text(
                "🏆 <b>ТЫ НАШЁЛ ВСЕ СОКРОВИЩА!</b>\n\n"
                f"💰 Найдено: {treasures}/{TREASURES_COUNT}\n"
                f"🎯 Множитель: ×{multiplier:.2f}\n"
                f"💵 Выигрыш: +${possible_win:,}\n"
                f"⭐ Получено опыта: +{xp_reward} XP\n\n"
                "🥇 Победа записана в статистику!",
                reply_markup=build_revealed_keyboard(user_id),
                parse_mode="HTML",
            )

            print(
                f"[TREASURE] Игрок {user_id} нашёл все "
                f"сокровища, выиграл ${possible_win:,} "
                f"и получил {xp_reward} XP",
                flush=True,
            )
            return

        await query.edit_message_text(
            "💰 Ты нашёл мешочек с монетами!\n\n"
            f"💰 Мешочков: {treasures}/{TREASURES_COUNT}\n"
            f"💣 Бомб: {stats['bombs']}/{BOMBS_TO_LOSE}\n"
            f"🎯 Текущий множитель: ×{multiplier:.2f}\n"
            f"💵 Можно забрать: ${possible_win:,}\n\n"
            "🎲 Выбирай следующую клетку или забирай выигрыш!",
            reply_markup=build_treasure_keyboard(user_id),
        )
        return

    await query.edit_message_text(
        "❌ Неизвестный результат клетки. "
        "Попробуй начать новую игру."
    )
