import random


games = {}


def create_game(user_id):

    cells = {}

    diamond = random.randint(0, 8)

    for i in range(9):
        cells[i] = "💣"

    cells[diamond] = "💎"

    games[user_id] = {
        "cells": cells,
        "opened": []
    }


def get_cell(user_id, number):

    game = games.get(user_id)

    if not game:
        return None


    if number in game["opened"]:
        return "opened"


    game["opened"].append(number)

    return game["cells"][number]


def end_game(user_id):

    if user_id in games:
        del games[user_id]