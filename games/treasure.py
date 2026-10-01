import random


games = {}


def create_game(user_id, bet):

    cells = {}

    diamond = random.randint(0, 8)


    for i in range(9):

        cells[i] = "💣"


    cells[diamond] = "💎"


    games[user_id] = {

        "cells": cells,

        "opened": [],

        "bet": bet,

        "active": True

    }



def get_cell(user_id, number):

    game = games.get(user_id)


    if not game:

        return None


    if number not in game["cells"]:

        return None



    if number in game["opened"]:

        return "opened"



    game["opened"].append(number)


    return game["cells"][number]



def get_bet(user_id):

    game = games.get(user_id)


    if game:

        return game["bet"]


    return 0



def end_game(user_id):

    if user_id in games:

        games[user_id]["active"] = False

        del games[user_id]