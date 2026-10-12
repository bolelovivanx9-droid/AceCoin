from telegram import InlineKeyboardButton, InlineKeyboardMarkup


FIELD_SIZE = 5


def treasure_field():
    keyboard = []

    for row in range(FIELD_SIZE):
        buttons = []

        for col in range(FIELD_SIZE):
            buttons.append(
                InlineKeyboardButton(
                    "⬜",
                    callback_data=f"treasure_{row}_{col}",
                )
            )

        keyboard.append(buttons)

    # Кнопка забора выигрыша под полем.
    keyboard.append(
        [
            InlineKeyboardButton(
                "💵 Забрать выигрыш",
                callback_data="treasure_cashout",
            )
        ]
    )

    return InlineKeyboardMarkup(keyboard)