from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def treasure_field():

    keyboard = []

    for row in range(3):
        buttons = []

        for col in range(3):
            buttons.append(
                InlineKeyboardButton(
                    "⬜",
                    callback_data=f"treasure_{row}_{col}"
                )
            )

        keyboard.append(buttons)

    return InlineKeyboardMarkup(keyboard)