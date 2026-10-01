from telegram import InlineKeyboardButton, InlineKeyboardMarkup


FIELD_SIZE = 3


def treasure_field():

    keyboard = []


    for row in range(FIELD_SIZE):

        buttons = []


        for col in range(FIELD_SIZE):

            buttons.append(
                InlineKeyboardButton(
                    "⬜",
                    callback_data=f"treasure_{row}_{col}"
                )
            )


        keyboard.append(buttons)


    return InlineKeyboardMarkup(keyboard)